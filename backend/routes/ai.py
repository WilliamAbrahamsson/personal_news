import os
import glob
from typing import List, Union, Optional

import requests
from flask import Blueprint, current_app, jsonify, request, g

from backend.extensions import db
from backend.models.video import Video
from backend.models.source import Source
from backend.youtube_captions import extract_video_id
from backend.ai_ops import summarize_markdown as ops_summarize_markdown
from backend.ai_ops import openai_transcribe as ops_openai_transcribe
from backend.auth_utils import auth_required


bp = Blueprint("ai", __name__, url_prefix="/ai")


def _normalize_transcript(t: Union[str, List[str]]) -> str:
    if isinstance(t, list):
        return "\n\n---\n\n".join([str(x) for x in t])
    return str(t or "")


def _summarize_markdown_helper(transcript: str, *, instructions: str = "", model: Optional[str] = None) -> str:
    return ops_summarize_markdown(transcript, instructions=instructions, model=model)


@bp.post("/videos/<int:video_id>/summarize")
@auth_required
def summarize_video(video_id: int):
    # Ensure the current user owns this video via its source
    vid = Video.query.get(video_id)
    if not vid:
        return jsonify(error="Video not found"), 404
    src = Source.query.get(vid.source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Not authorized for this video"), 403
    if not (vid.transcribe or "").strip():
        return jsonify(error="Transcript is empty; cannot summarize"), 400

    data = request.get_json() or {}
    instructions = (data.get("instructions") or "").strip()
    md = _summarize_markdown_helper(vid.transcribe, instructions=instructions)
    if not md:
        return jsonify(error="Failed to generate summary"), 502
    vid.summary = md
    db.session.commit()
    return jsonify(video=vid.to_dict())


def _openai_transcribe_helper(file_path: str, *, model: Optional[str] = None, language: Optional[str] = None) -> str:
    return ops_openai_transcribe(file_path, model=model, language=language)


@bp.post("/videos/<int:video_id>/transcribe")
@auth_required
def transcribe_video(video_id: int):
    vid = Video.query.get(video_id)
    if not vid:
        return jsonify(error="Video not found"), 404
    src = Source.query.get(vid.source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Not authorized for this video"), 403

    # Resolve audio path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_path = None
    if getattr(vid, "audio_path", None):
        p = os.path.join(project_root, vid.audio_path.lstrip("/"))
        if os.path.isfile(p):
            abs_path = p
    if not abs_path:
        out_dir = current_app.config.get("VIDEO_DIR")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            pass
        yt_id = extract_video_id(vid.url) or str(video_id)
        for ext in (".m4a", ".mp4", ".aac", ".mp3", ".webm", ".wav"):
            cand = os.path.join(out_dir, f"{yt_id}{ext}")
            if os.path.isfile(cand):
                abs_path = cand
                try:
                    rel = f"/{os.path.relpath(abs_path, project_root)}"
                    vid.audio_path = rel
                    vid.audio_status = "ready"
                    db.session.commit()
                except Exception:
                    pass
                break
    if not abs_path:
        return jsonify(error="Audio file not found on disk"), 404

    # mark pending
    vid.transcribe_status = "pending"
    db.session.commit()

    text = _openai_transcribe_helper(abs_path)
    if not text:
        vid.transcribe_status = "failed"
        db.session.commit()
        return jsonify(error="Transcription failed or empty"), 502

    vid.transcribe = text
    vid.transcribe_status = "ready"
    vid.summary = _summarize_markdown_helper(text)
    db.session.commit()
    return jsonify(video=vid.to_dict()), 200
