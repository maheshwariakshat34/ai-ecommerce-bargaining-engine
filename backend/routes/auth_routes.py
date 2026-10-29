"""Sign up, log in, log out. Two roles: "user" (customer) and "admin" (seller)."""

import re
import time

from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.models.product import db
from backend.models.user import User
from backend.services.security import REQUIRE_LOGIN_TO_BARGAIN, current_user


auth_bp = Blueprint("auth", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAX_FAILS = 5          # wrong passwords allowed ...
LOCK_SECONDS = 300     # ... within this many seconds, then wait

_fails = {}            # (ip, email) -> times of wrong passwords (resets on restart)

# used when the email is unknown, so the reply takes the same time
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _recent_fails(key):
    now = time.time()
    fresh = [t for t in _fails.get(key, []) if now - t < LOCK_SECONDS]

    if fresh:
        _fails[key] = fresh
    else:
        _fails.pop(key, None)

    return fresh


def _log_in(user):
    session.clear()                      # a new session for every login
    session["user_id"] = user.id
    session.permanent = True


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not 2 <= len(name) <= 60:
        return jsonify({"error": "Please enter your name (2 to 60 letters)."}), 400

    if len(email) > 120 or not EMAIL_PATTERN.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    if not 8 <= len(password) <= 128:
        return jsonify({"error": "Password must be 8 to 128 characters."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    # role is always "user" here. Seller accounts cannot be created from the website.
    user = User(name=name, email=email, role="user")
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An account with this email already exists."}), 409

    _log_in(user)
    return jsonify({"user": user.to_dict()}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    wanted_role = data.get("role")       # optional: "user" or "admin"

    key = (request.remote_addr, email)

    if len(_recent_fails(key)) >= MAX_FAILS:
        return jsonify({
            "error": "Too many wrong attempts. Please wait a few minutes and try again."
        }), 429

    user = User.query.filter_by(email=email).first()
    password_ok = check_password_hash(
        user.password_hash if user else _DUMMY_HASH, password
    )

    if user is None or not password_ok:
        _fails.setdefault(key, []).append(time.time())
        return jsonify({"error": "Wrong email or password."}), 401

    if wanted_role in ("user", "admin") and wanted_role != user.role:
        message = (
            "This is a seller account. Please use the Seller tab."
            if user.role == "admin"
            else "This is not a seller account."
        )
        return jsonify({"error": message}), 403

    _fails.pop(key, None)
    _log_in(user)
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    user = current_user()

    return jsonify({
        "user": user.to_dict() if user else None,
        "login_required_to_bargain": REQUIRE_LOGIN_TO_BARGAIN
    }), 200
