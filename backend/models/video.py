from datetime import datetime

from sqlalchemy import UniqueConstraint

from backend.extensions import db


class Video(db.Model):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("source_id", "url", name="uq_source_url"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sources.id"), nullable=False, index=True)
    url = db.Column(db.String(1000), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    transcribe = db.Column(db.Text, nullable=False, default="")
    summary = db.Column(db.Text, nullable=False, default="")
    audio_path = db.Column(db.String(1000), nullable=False, default="")
    audio_status = db.Column(db.String(50), nullable=False, default="")  # '', 'pending', 'ready', 'failed'
    transcribe_status = db.Column(db.String(50), nullable=False, default="")  # '', 'pending', 'ready', 'failed'
    # YouTube metadata
    channel_title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    view_count = db.Column(db.Integer, nullable=True)
    like_count = db.Column(db.Integer, nullable=True)
    dislike_count = db.Column(db.Integer, nullable=True)
    comment_count = db.Column(db.Integer, nullable=True)
    published_at = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "transcribe": self.transcribe,
            "summary": self.summary,
            "audio_path": self.audio_path,
            "audio_status": self.audio_status,
            "transcribe_status": self.transcribe_status,
            "channel_title": self.channel_title,
            "description": self.description,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "dislike_count": self.dislike_count,
            "comment_count": self.comment_count,
            "published_at": self.published_at,
            "created_at": self.created_at.isoformat() + "Z",
        }
