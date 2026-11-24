"""
Tests for Phase 1: Session Expiry + Rate Limiting.

Run from project root:
    pytest backend/tests/test_phase1.py -v
"""

import pytest
from datetime import datetime, timedelta

from backend.app import create_app
from backend.models.product import db as _db
from backend.models.bargaining_session import BargainingSession
from backend.models.bargaining_rate_limit import BargainingRateLimit
from backend.services.bargaining_service import (
    is_session_expired,
    refresh_session_activity,
    expire_session,
    check_rate_limit,
    record_session_start,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Create a Flask app wired to an in-memory SQLite DB for the test run."""
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "BARGAINING_SESSION_TIMEOUT_MINUTES": 15,
        "RATE_LIMIT_SESSIONS_PER_DAY": 3,
        "COOLING_OFF_MINUTES": 10,
    })
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture(autouse=True)
def clean_tables(app):
    """Wipe rate-limit and session rows before every test."""
    with app.app_context():
        BargainingRateLimit.query.delete()
        BargainingSession.query.delete()
        _db.session.commit()
        yield


@pytest.fixture
def ctx(app):
    """Push an app context so service helpers can call current_app.config."""
    with app.app_context():
        yield


# ---------------------------------------------------------------------------
# Helper: minimal BargainingSession object (not persisted)
# ---------------------------------------------------------------------------

def _make_session(status="ACTIVE", expires_at=None):
    """Return an unsaved BargainingSession with the minimum required fields."""
    return BargainingSession(
        product_id=1,
        quantity=1,
        current_round=1,
        max_rounds=3,
        status=status,
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIsSessionExpired:

    def test_session_expires_after_timeout(self, app):
        """is_session_expired() → True when expires_at is in the past."""
        with app.app_context():
            past = datetime.utcnow() - timedelta(minutes=1)
            session = _make_session(expires_at=past)
            assert is_session_expired(session) is True

    def test_session_is_active_if_not_expired(self, app):
        """is_session_expired() → False when expires_at is in the future."""
        with app.app_context():
            future = datetime.utcnow() + timedelta(minutes=10)
            session = _make_session(expires_at=future)
            assert is_session_expired(session) is False

    def test_session_no_expiry_is_not_expired(self, app):
        """is_session_expired() → False when expires_at is None (no timeout set)."""
        with app.app_context():
            session = _make_session(expires_at=None)
            assert is_session_expired(session) is False

    def test_inactive_session_is_always_expired(self, app):
        """is_session_expired() → True immediately if status != ACTIVE."""
        with app.app_context():
            future = datetime.utcnow() + timedelta(hours=1)
            session = _make_session(status="CLOSED", expires_at=future)
            assert is_session_expired(session) is True


class TestRefreshSessionActivity:

    def test_refresh_extends_expiry(self, app):
        """refresh_session_activity() must push expires_at ~15 min into the future."""
        with app.app_context():
            old_expiry = datetime.utcnow() - timedelta(minutes=5)
            session = _make_session(expires_at=old_expiry)

            before = datetime.utcnow()
            refresh_session_activity(session)
            after = datetime.utcnow()

            assert session.expires_at is not None
            # expires_at should be roughly (now + 15 min)
            expected_min = before + timedelta(minutes=14, seconds=59)
            expected_max = after + timedelta(minutes=15, seconds=1)
            assert expected_min <= session.expires_at <= expected_max

    def test_refresh_updates_last_activity_at(self, app):
        """refresh_session_activity() must also update last_activity_at."""
        with app.app_context():
            session = _make_session()
            session.last_activity_at = datetime.utcnow() - timedelta(hours=1)

            before = datetime.utcnow()
            refresh_session_activity(session)
            after = datetime.utcnow()

            assert before <= session.last_activity_at <= after


class TestExpireSession:

    def test_expire_session_sets_status(self, app):
        """expire_session() must set status to EXPIRED (uppercase)."""
        with app.app_context():
            session = _make_session()
            expire_session(session)
            assert session.status == "EXPIRED"

    def test_expire_session_updates_last_activity(self, app):
        """expire_session() must update last_activity_at to now."""
        with app.app_context():
            session = _make_session()
            before = datetime.utcnow()
            expire_session(session)
            after = datetime.utcnow()
            assert before <= session.last_activity_at <= after


class TestCheckRateLimit:

    def test_guest_skips_rate_limit(self, app):
        """check_rate_limit(None, ...) → (True, '') — guests are never blocked."""
        with app.app_context():
            allowed, msg = check_rate_limit(None, 1)
            assert allowed is True
            assert msg == ""

    def test_rate_limit_allows_first_session(self, app):
        """No rate-limit record yet → first session is always allowed."""
        with app.app_context():
            allowed, msg = check_rate_limit(user_id=99, product_id=1)
            assert allowed is True
            assert msg == ""

    def test_rate_limit_blocks_after_3_sessions(self, app):
        """session_count == 3 (== RATE_LIMIT_SESSIONS_PER_DAY) → blocked."""
        with app.app_context():
            record = BargainingRateLimit(
                user_id=1,
                product_id=1,
                date=datetime.utcnow().date(),
                session_count=3,
                last_session_at=datetime.utcnow() - timedelta(hours=1),
            )
            _db.session.add(record)
            _db.session.commit()

            allowed, msg = check_rate_limit(user_id=1, product_id=1)
            assert allowed is False
            assert msg != ""
            assert "3" in msg  # message must mention the limit number

    def test_cooling_off_blocks_immediate_restart(self, app):
        """last_session_at = now with count < max → blocked by cooling-off."""
        with app.app_context():
            record = BargainingRateLimit(
                user_id=2,
                product_id=1,
                date=datetime.utcnow().date(),
                session_count=1,
                last_session_at=datetime.utcnow(),   # just now
            )
            _db.session.add(record)
            _db.session.commit()

            allowed, msg = check_rate_limit(user_id=2, product_id=1)
            assert allowed is False
            assert msg != ""

    def test_cooling_off_allows_after_wait(self, app):
        """last_session_at > 10 min ago with count < max → allowed."""
        with app.app_context():
            record = BargainingRateLimit(
                user_id=3,
                product_id=1,
                date=datetime.utcnow().date(),
                session_count=1,
                last_session_at=datetime.utcnow() - timedelta(minutes=11),
            )
            _db.session.add(record)
            _db.session.commit()

            allowed, msg = check_rate_limit(user_id=3, product_id=1)
            assert allowed is True
            assert msg == ""


class TestRecordSessionStart:

    def test_creates_new_record_for_first_session(self, app):
        """record_session_start() must insert a row with session_count = 1."""
        with app.app_context():
            record_session_start(user_id=10, product_id=5)
            row = BargainingRateLimit.query.filter_by(
                user_id=10, product_id=5
            ).first()
            assert row is not None
            assert row.session_count == 1

    def test_increments_existing_record(self, app):
        """record_session_start() called twice → session_count == 2."""
        with app.app_context():
            record_session_start(user_id=11, product_id=5)
            record_session_start(user_id=11, product_id=5)
            row = BargainingRateLimit.query.filter_by(
                user_id=11, product_id=5
            ).first()
            assert row is not None
            assert row.session_count == 2

    def test_guest_does_not_create_record(self, app):
        """record_session_start(None, ...) must not write anything to the DB."""
        with app.app_context():
            record_session_start(user_id=None, product_id=5)
            count = BargainingRateLimit.query.count()
            assert count == 0
