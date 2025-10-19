from flask import Blueprint, jsonify, g

from backend.auth_utils import auth_required
from backend.extensions import db
from backend.models.video import Video
from backend.models.source import Source


bp = Blueprint("videos", __name__, url_prefix="/videos")


@bp.get("")
@auth_required
def list_videos():
    q = (
        db.session.query(Video)
        .join(Source, Source.id == Video.source_id)
        .filter(Source.user_id == g.current_user.id)
        .order_by(Video.id.desc())
    )
    items = q.all()
    return jsonify([v.to_dict() for v in items])

