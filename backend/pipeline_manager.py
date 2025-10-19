import os
import shutil
import threading

from backend.youtube_captions import extract_video_id
from backend.ai_ops import openai_transcribe, summarize_markdown
import subprocess
import math


def _run_pipeline(app, video_id: int, url: str) -> None:
    """Download audio-only, transcribe via OpenAI, and summarize.

    Prints clear start/finish logs for each step.
    """

    def worker():
        from flask import current_app
        from backend.extensions import db
        from backend.models.video import Video
        from yt_dlp import YoutubeDL

        with app.app_context():
            current_app.logger.info("Pipeline start video_id=%s", video_id)
            v = Video.query.get(video_id)
            if not v:
                current_app.logger.warning("Pipeline abort: video missing id=%s", video_id)
                return
            # STEP 1: Download audio-only
            try:
                current_app.logger.info("Download start video_id=%s", video_id)
                out_dir = app.config.get("VIDEO_DIR")
                os.makedirs(out_dir, exist_ok=True)
                has_ffmpeg = bool(shutil.which("ffmpeg") or shutil.which("avconv"))
                if not has_ffmpeg:
                    raise RuntimeError("ffmpeg required to extract audio")
                fmt = "bestaudio/best"
                # Canonical URL
                vid_key = extract_video_id(url)
                canon = f"https://www.youtube.com/watch?v={vid_key}" if vid_key else url
                ydl_opts = {
                    "format": fmt,
                    "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
                    "quiet": True,
                    "noprogress": False,
                    "noplaylist": True,
                    "postprocessors": [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"},
                        {"key": "FFmpegMetadata"},
                    ],
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(canon, download=True)
                    base = ydl.prepare_filename(info)
                    base_no_ext, _ = os.path.splitext(base)
                    audio_path = None
                    for ext in (".m4a", ".mp3", ".aac", ".webm", ".wav"):
                        cand = base_no_ext + ext
                        if os.path.exists(cand):
                            audio_path = os.path.abspath(cand)
                            break
                    if not audio_path:
                        raise RuntimeError("Audio file not produced")
                # Persist audio path + status
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                rel = f"/{os.path.relpath(audio_path, project_root)}"
                v.audio_path = rel
                v.audio_status = "ready"
                db.session.commit()
                current_app.logger.info("Download finished video_id=%s path=%s", video_id, audio_path)
            except Exception as e:
                current_app.logger.exception("Download failed video_id=%s: %s", video_id, e)
                v.audio_status = "failed"
                db.session.commit()
                return

            # Helper: ensure audio is within OpenAI limits; downsample + segment if needed
            def prepare_segments(path: str) -> list[str]:
                segs: list[str] = []
                try:
                    size = os.path.getsize(path)
                except Exception:
                    size = 0
                limit = 24 * 1024 * 1024  # ~24MB safety under API limit
                small_path = path
                try:
                    # Always re-encode to mono 16kHz AAC 48k to reduce size
                    base, _ = os.path.splitext(path)
                    small_path = base + ".small.m4a"
                    cmd = [
                        "ffmpeg", "-y", "-i", path,
                        "-ac", "1", "-ar", "16000",
                        "-c:a", "aac", "-b:a", "48k",
                        small_path,
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                except Exception:
                    small_path = path  # fallback to original

                try:
                    size = os.path.getsize(small_path)
                except Exception:
                    size = 0

                if size and size <= limit:
                    return [small_path]

                # Segment into ~10-minute chunks (600s)
                try:
                    out_dir = os.path.dirname(small_path)
                    base = os.path.splitext(os.path.basename(small_path))[0]
                    pattern = os.path.join(out_dir, f"{base}.part-%03d.m4a")
                    cmd = [
                        "ffmpeg", "-y", "-i", small_path,
                        "-f", "segment", "-segment_time", "600",
                        "-c", "copy", pattern,
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    # Collect produced segments
                    try:
                        import glob as _glob
                        segs = sorted(_glob.glob(os.path.join(out_dir, f"{base}.part-*.m4a")))
                    except Exception:
                        segs = []
                    if segs:
                        return segs
                except Exception:
                    pass
                # As a last resort, return the (possibly large) small_path
                return [small_path]

            # STEP 2: Transcribe
            try:
                current_app.logger.info("Transcribe start video_id=%s", video_id)
                v.transcribe_status = "pending"
                db.session.commit()
                # Prepare segments and transcribe each
                parts = prepare_segments(audio_path)
                full_text_chunks: list[str] = []
                for i, p in enumerate(parts, start=1):
                    current_app.logger.info("Transcribe chunk %s/%s video_id=%s", i, len(parts), video_id)
                    t = openai_transcribe(p)
                    if not t:
                        current_app.logger.warning("Empty chunk transcription %s/%s video_id=%s", i, len(parts), video_id)
                    else:
                        full_text_chunks.append(t)
                text = "\n\n".join(full_text_chunks).strip()
                if not text:
                    raise RuntimeError("Transcription empty")
                v.transcribe = text
                v.transcribe_status = "ready"
                db.session.commit()
                current_app.logger.info("Transcribe finished video_id=%s (chars=%s)", video_id, len(text))
            except Exception as e:
                current_app.logger.exception("Transcribe failed video_id=%s: %s", video_id, e)
                v.transcribe_status = "failed"
                db.session.commit()
                return

            # STEP 3: Summarize
            try:
                current_app.logger.info("Summarize start video_id=%s", video_id)
                md = summarize_markdown(v.transcribe)
                v.summary = md
                db.session.commit()
                current_app.logger.info("Summarize finished video_id=%s", video_id)
            except Exception as e:
                current_app.logger.exception("Summarize failed video_id=%s: %s", video_id, e)

            # Cleanup: remove audio files; keep DB references minimal
            try:
                current_app.logger.info("Cleanup start video_id=%s", video_id)
                try:
                    import glob as _glob
                    base_dir = os.path.dirname(audio_path)
                    base_name = os.path.splitext(os.path.basename(audio_path))[0]
                    patterns = [
                        audio_path,
                        os.path.join(base_dir, f"{base_name}.small.m4a"),
                        os.path.join(base_dir, f"{base_name}.part-" + "*.m4a"),
                    ]
                    for pat in patterns:
                        for fp in _glob.glob(pat):
                            try:
                                os.remove(fp)
                            except Exception:
                                pass
                except Exception:
                    pass
                # Clear stored audio path/status since files are removed
                v.audio_path = ""
                v.audio_status = ""
                db.session.commit()
                current_app.logger.info("Cleanup finished video_id=%s", video_id)
            except Exception as e:
                current_app.logger.exception("Cleanup failed video_id=%s: %s", video_id, e)

            current_app.logger.info("Pipeline finished video_id=%s", video_id)

    worker()


def queue_full_pipeline(app, video_id: int, url: str) -> None:
    def bg():
        _run_pipeline(app, video_id, url)
    threading.Thread(target=bg, name=f"pipeline-{video_id}", daemon=True).start()


def run_full_pipeline(app, video_id: int, url: str) -> None:
    """Synchronous version: run in the request thread."""
    _run_pipeline(app, video_id, url)
