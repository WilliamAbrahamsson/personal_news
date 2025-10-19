from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models.user import User
from backend.security import JWTError, create_jwt, decode_jwt
import os
import requests


bp = Blueprint("auth", __name__, url_prefix="/auth")


def _issue_token(user: User) -> str:
    secret = current_app.config.get("JWT_SECRET_KEY", "dev-secret-change-me")
    expires_in = int(current_app.config.get("JWT_EXPIRES_SECONDS", 60 * 60 * 24))
    return create_jwt({"sub": user.id, "email": user.email, "name": user.name}, secret, expires_in)


@bp.post("/register")
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify(error="Name, email and password are required"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(error="Email already registered"), 409

    user = User(name=name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    token = _issue_token(user)
    return jsonify(token=token, user=user.to_dict()), 201


@bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error="Invalid email or password"), 401

    token = _issue_token(user)
    return jsonify(token=token, user=user.to_dict())


@bp.get("/me")
def me():
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
    return jsonify(user=user.to_dict())


@bp.post("/google")
def google_login():
    data = request.get_json() or {}
    id_token = (data.get("id_token") or data.get("credential") or "").strip()
    if not id_token:
        return jsonify(error="Missing id_token"), 400

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return jsonify(error="Server missing GOOGLE_CLIENT_ID"), 500

    try:
        resp = requests.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}, timeout=15)
    except requests.RequestException as e:
        return jsonify(error=f"Google verify failed: {e}"), 502

    if not resp.ok:
        return jsonify(error="Invalid Google token"), 401

    info = resp.json() or {}
    aud = info.get("aud")
    email = (info.get("email") or "").lower()
    name = info.get("name") or info.get("given_name") or "Google User"
    email_verified = str(info.get("email_verified", "true")).lower() == "true"

    if aud != client_id or not email or not email_verified:
        return jsonify(error="Google token not valid for this app"), 401

    user = User.query.filter_by(email=email).first()
    if not user:
        # Create a placeholder password for OAuth users
        user = User(name=name, email=email, password_hash=generate_password_hash(os.urandom(16).hex()))
        db.session.add(user)
        db.session.commit()
    else:
        if not user.name and name:
            user.name = name
            db.session.commit()

    token = _issue_token(user)
    return jsonify(token=token, user=user.to_dict())
