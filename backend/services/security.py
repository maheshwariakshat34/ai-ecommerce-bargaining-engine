"""Simple admin protection."""

import hmac
import os
from functools import wraps

from dotenv import load_dotenv
from flask import request, jsonify

load_dotenv()


def is_admin():
    expected = os.getenv("ADMIN_KEY") or ""
    provided = request.headers.get("X-Admin-Key", "")

    if not expected:
        return False

    return hmac.compare_digest(provided.encode(), expected.encode())


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return jsonify({"error": "Admin access required."}), 403
        return view(*args, **kwargs)
    return wrapper