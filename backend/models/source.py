from datetime import datetime

from backend.extensions import db
from backend.models.video import Video


class Source(db.Model):
    __tablename__ = "sources"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # e.g., 'youtube_channel'
    value = db.Column(db.String(500), nullable=False)  # channel url/id/etc.
    label = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    videos = db.relationship(
        Video,
        backref="source",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="desc(Video.id)",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "value": self.value,
            "label": self.label,
            "created_at": self.created_at.isoformat() + "Z",
        }
