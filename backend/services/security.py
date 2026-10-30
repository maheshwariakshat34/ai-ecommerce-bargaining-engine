import hmac
import os
import secrets
from datetime import timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import g, jsonify, request, session

from backend.models.product import db
from backend.models.user import User

load_dotenv()


REQUIRE_LOGIN_TO_BARGAIN = True


def init_auth(app):
    """Cookie settings and the secret key that signs the login cookie."""
    key = os.getenv("SECRET_KEY")

    if not key:

        os.makedirs(app.instance_path, exist_ok=True)
        path = os.path.join(app.instance_path, "secret_key.txt")

        if os.path.exists(path):
            with open(path) as f:
                key = f.read().strip()
        else:
            key = secrets.token_hex(32)
            with open(path, "w") as f:
                f.write(key)

    app.config["SECRET_KEY"] = key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # BUG 7 FIX: require HTTPS for session cookies in production
    app.config["SESSION_COOKIE_SECURE"] = not app.debug
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)


def current_user():
    """The logged in User, or None. Looked up once per request."""
    if "_user" not in g:
        user_id = session.get("user_id")
        g._user = db.session.get(User, user_id) if user_id else None
    return g._user


def has_admin_key():
    """The old way: X-Admin-Key header (kept for scripts and API tools)."""
    expected = os.getenv("ADMIN_KEY") or ""
    provided = request.headers.get("X-Admin-Key", "")

    if not expected:
        return False

    return hmac.compare_digest(provided.encode(), expected.encode())


def is_admin():
    user = current_user()
    return has_admin_key() or (user is not None and user.role == "admin")


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if is_admin():
            return view(*args, **kwargs)

        if current_user() is None and not request.headers.get("X-Admin-Key"):
            return jsonify({
                "error": "Please log in as the seller.",
                "login_required": True
            }), 401

        return jsonify({"error": "Admin access required."}), 403
    return wrapper


def bargaining_login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if (REQUIRE_LOGIN_TO_BARGAIN
                and current_user() is None and not has_admin_key()):
            return jsonify({
                "error": "Please log in to bargain.",
                "login_required": True
            }), 401
        return view(*args, **kwargs)
    return wrapper
