from flask import Blueprint, jsonify

from backend.models.user import User


bp = Blueprint("users", __name__, url_prefix="/users")


@bp.get("")
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])


@bp.post("")
def add_user():
    return jsonify(error="Use /auth/register to create users"), 405
