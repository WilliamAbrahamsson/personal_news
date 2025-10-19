from functools import wraps
from flask import request, jsonify, g, current_app

from backend.models.user import User
from backend.security import decode_jwt, JWTError


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            return jsonify(error="Missing bearer token"), 401

        secret = current_app.config.get("JWT_SECRET_KEY", "dev-secret-change-me")
        try:
            payload = decode_jwt(token, secret)
        except JWTError as e:
            return jsonify(error=str(e)), 401

        user = User.query.get(payload.get("sub"))
        if not user:
            return jsonify(error="User not found"), 404
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper

