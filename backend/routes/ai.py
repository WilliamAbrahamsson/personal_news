import os
import shutil
import threading
import subprocess
import glob
from typing import List, Optional, Union

from flask import Blueprint, current_app, jsonify, request, g
from backend.extensions import db
from backend.models.video import Video
from backend.models.source import Source
from backend.youtube_captions import extract_video_id
from backend.ai_ops import summarize_markdown, openai_transcribe
from backend.auth_utils import auth_required

bp = Blueprint("ai", __name__, url_prefix="/ai")


# ---------------------------------------------------------------------
# 🔧 Utility Helpers
# ---------------------------------------------------------------------

def _normalize_transcript(t: Union[str, List[str]]) -> str:
    """Ensure transcripts are normalized to a single string with separators."""
    if isinstance(t, list):
        return "\n\n---\n\n".join(map(str, t))
    return str(t or "")


def _summarize(text: str, instructions: str = "", model: Optional[str] = None) -> str:
    """Summarize transcript using AI."""
    return summarize_markdown(text, instructions=instructions, model=model)


def _transcribe(path: str, model: Optional[str] = None, language: Optional[str] = None) -> str:
    """Transcribe an audio file using AI."""
    return openai_transcribe(path, model=model, language=language)


def _resolve_audio_path(vid: Video) -> Optional[str]:
    """Try to locate an audio file for the video."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_path = None

    # Case 1: already has an audio path
    if getattr(vid, "audio_path", None):
        p = os.path.join(project_root, vid.audio_path.lstrip("/"))
        if os.path.isfile(p):
            return p

    # Case 2: search in VIDEO_DIR
    out_dir = current_app.config.get("VIDEO_DIR")
    yt_id = extract_video_id(vid.url) or str(vid.id)
    for ext in (".m4a", ".mp4", ".aac", ".mp3", ".webm", ".wav"):
        cand = os.path.join(out_dir, f"{yt_id}{ext}")
        if os.path.isfile(cand):
            rel = f"/{os.path.relpath(cand, project_root)}"
            vid.audio_path = rel
            vid.audio_status = "ready"
            db.session.commit()
            return cand

    return None


# ---------------------------------------------------------------------
# 🧠 Background Processing
# ---------------------------------------------------------------------

def _prepare_audio_segments(path: str) -> list[str]:
    """Ensure audio is under OpenAI limits. Downsample + segment if needed."""
    limit = 24 * 1024 * 1024  # 24MB
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0

    small_path = path
    try:
        base, _ = os.path.splitext(path)
        small_path = base + ".small.m4a"
        subprocess.run([
            "ffmpeg", "-y", "-i", path,
            "-ac", "1", "-ar", "16000",
            "-c:a", "aac", "-b:a", "48k", small_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        size = os.path.getsize(small_path)
    except Exception:
        pass

    if size and size <= limit:
        return [small_path]

    # Split into ~10min chunks
    out_dir = os.path.dirname(small_path)
    base = os.path.splitext(os.path.basename(small_path))[0]
    pattern = os.path.join(out_dir, f"{base}.part-%03d.m4a")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", small_path,
            "-f", "segment", "-segment_time", "600",
            "-c", "copy", pattern
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return sorted(glob.glob(os.path.join(out_dir, f"{base}.part-*.m4a")))
    except Exception:
        return [small_path]


def _run_full_pipeline(app, video_id: int, url: str):
    """Main background pipeline: download, transcribe, summarize."""
    from yt_dlp import YoutubeDL

    with app.app_context():
        v = Video.query.get(video_id)
        if not v:
            current_app.logger.warning("Video %s not found", video_id)
            return

        out_dir = app.config.get("VIDEO_DIR")
        os.makedirs(out_dir, exist_ok=True)

        # ---------------- Step 1: Download ----------------
        try:
            current_app.logger.info("Downloading audio for video_id=%s", video_id)
            vid_key = extract_video_id(url)
            canon_url = f"https://www.youtube.com/watch?v={vid_key}" if vid_key else url
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
                "quiet": True,
                "noplaylist": True,
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"},
                    {"key": "FFmpegMetadata"},
                ],
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(canon_url, download=True)
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                audio_path = next((base + ext for ext in [".m4a", ".mp3", ".aac", ".wav", ".webm"] if os.path.exists(base + ext)), None)
                if not audio_path:
                    raise RuntimeError("No audio file found")

            rel = f"/{os.path.relpath(audio_path, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))}"
            v.audio_path, v.audio_status = rel, "ready"
            db.session.commit()
        except Exception as e:
            current_app.logger.exception("Audio download failed: %s", e)
            v.audio_status = "failed"
            db.session.commit()
            return

        # ---------------- Step 2: Transcribe ----------------
        try:
            current_app.logger.info("Transcribing video_id=%s", video_id)
            v.transcribe_status = "pending"
            db.session.commit()

            chunks = _prepare_audio_segments(audio_path)
            parts = [openai_transcribe(p) for p in chunks if p]
            transcript = "\n\n".join(filter(None, parts))

            if not transcript.strip():
                raise RuntimeError("Empty transcript")

            v.transcribe = transcript
            v.transcribe_status = "ready"
            db.session.commit()
        except Exception as e:
            current_app.logger.exception("Transcription failed: %s", e)
            v.transcribe_status = "failed"
            db.session.commit()
            return

        # ---------------- Step 3: Summarize ----------------
        try:
            current_app.logger.info("Summarizing video_id=%s", video_id)
            v.summary = summarize_markdown(v.description + v.transcribe)
            db.session.commit()
        except Exception as e:
            current_app.logger.exception("Summarization failed: %s", e)

        # ---------------- Step 4: Cleanup ----------------
        try:
            current_app.logger.info("Cleaning up video_id=%s", video_id)
            for fp in glob.glob(audio_path.replace(".m4a", "*.m4a")):
                try:
                    os.remove(fp)
                except Exception:
                    pass
            v.audio_path = ""
            v.audio_status = ""
            db.session.commit()
        except Exception as e:
            current_app.logger.warning("Cleanup failed: %s", e)


def _run_async(app, video_id: int, url: str):
    """Run pipeline in a background thread."""
    threading.Thread(
        target=_run_full_pipeline,
        args=(app, video_id, url),
        daemon=True,
        name=f"pipeline-{video_id}"
    ).start()


# ---------------------------------------------------------------------
# 🧩 Flask Routes
# ---------------------------------------------------------------------

@bp.post("/videos/<int:video_id>/transcribe")
@auth_required
def transcribe_video(video_id: int):
    vid = Video.query.get(video_id)
    if not vid:
        return jsonify(error="Video not found"), 404

    src = Source.query.get(vid.source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Not authorized"), 403

    abs_path = _resolve_audio_path(vid)
    if not abs_path:
        return jsonify(error="Audio file not found"), 404

    vid.transcribe_status = "pending"
    db.session.commit()

    text = _transcribe(abs_path)
    if not text:
        vid.transcribe_status = "failed"
        db.session.commit()
        return jsonify(error="Transcription failed"), 502

    vid.transcribe, vid.transcribe_status = text, "ready"
    vid.summary = _summarize(text)
    db.session.commit()
    return jsonify(video=vid.to_dict()), 200


@bp.post("/videos/<int:video_id>/summarize")
@auth_required
def summarize_video(video_id: int):
    vid = Video.query.get(video_id)
    if not vid:
        return jsonify(error="Video not found"), 404

    src = Source.query.get(vid.source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Not authorized"), 403

    if not (vid.transcribe or "").strip():
        return jsonify(error="Transcript is empty; cannot summarize"), 400

    data = request.get_json() or {}
    instructions = (data.get("instructions") or "").strip()

    md = _summarize(vid.transcribe, instructions=instructions)
    if not md:
        return jsonify(error="Summary generation failed"), 502

    vid.summary = md
    db.session.commit()
    return jsonify(video=vid.to_dict())


@bp.post("/videos/<int:video_id>/pipeline")
@auth_required
def queue_pipeline(video_id: int):
    """Trigger full pipeline asynchronously (download, transcribe, summarize)."""
    vid = Video.query.get(video_id)
    if not vid:
        return jsonify(error="Video not found"), 404

    src = Source.query.get(vid.source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Not authorized"), 403

    _run_async(current_app._get_current_object(), video_id, vid.url)
    return jsonify(message="Pipeline started", video_id=video_id)
