import os
import shutil
import threading
from typing import Any, Dict


_lock = threading.Lock()
_state: Dict[int, Dict[str, Any]] = {}


def get_status(video_id: int) -> Dict[str, Any]:
    """Return a copy of the current download state for a video id."""
    with _lock:
        return dict(_state.get(video_id, {"status": "idle", "progress": 0}))


def _set_status(video_id: int, **kwargs):
    with _lock:
        st = _state.setdefault(video_id, {"status": "idle", "progress": 0})
        st.update(kwargs)


def _progress_hook_factory(video_id: int):
    def hook(d: Dict[str, Any]):
        status = d.get("status")
        if status == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            idx = d.get("fragment_index")
            cnt = d.get("fragment_count")
            percent = 0
            if total:
                try:
                    percent = int(min(100, max(0, round(downloaded * 100 / total))))
                except Exception:
                    percent = 0
            elif idx and cnt:
                try:
                    percent = int(min(100, max(0, round(int(idx) * 100 / int(cnt)))))
                except Exception:
                    percent = 0
            else:
                # No total and no fragments; provide a monotonic visual hint up to 95%
                with _lock:
                    cur = _state.get(video_id) or {}
                    cur_prog = int(cur.get("progress") or 0)
                if downloaded > 0:
                    percent = min(95, cur_prog + 1)
            _set_status(
                video_id,
                status="downloading",
                progress=percent,
                fragment_index=idx,
                fragment_count=cnt,
                tmpfilename=d.get("tmpfilename"),
            )
        elif status == "finished":
            _set_status(video_id, status="processing", progress=100)
    return hook


def queue_download(app, video_id: int, url: str) -> None:
    """Queue a background download once per video id (idempotent)."""
    with _lock:
        cur = _state.get(video_id)
        if cur and cur.get("status") in {"queued", "starting", "downloading", "processing"}:
            return
        _state[video_id] = {"status": "queued", "progress": 0}

    def worker():
        from flask import current_app as _ca
        with app.app_context():
            try:
                from yt_dlp import YoutubeDL
            except Exception:
                _set_status(video_id, status="error", error="yt-dlp not installed")
                return

            out_dir = app.config.get("VIDEO_DIR")
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception:
                pass

            has_ffmpeg = bool(shutil.which("ffmpeg") or shutil.which("avconv"))
            if not has_ffmpeg:
                _set_status(video_id, status="error", error="ffmpeg required to extract audio-only mp4")
                return

            # Audio-only download with postprocessing to m4a (MP4 audio)
            fmt = "bestaudio/best"

            ydl_opts: Dict[str, Any] = {
                "format": fmt,
                "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
                "quiet": True,
                "noprogress": False,
                "nocheckcertificate": True,
                "restrictfilenames": True,
                "retries": 3,
                "fragment_retries": 3,
                "extractor_retries": 3,
                "noplaylist": True,
                "ignoreerrors": False,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                        "preferredquality": "0",
                    },
                    {"key": "FFmpegMetadata"},
                ],
                "progress_hooks": [_progress_hook_factory(video_id)],
            }

            _set_status(video_id, status="starting", progress=0)
            # Reflect pending state in DB
            try:
                from backend.extensions import db
                from backend.models.video import Video
                v = Video.query.get(video_id)
                if v:
                    v.audio_status = "pending"
                    db.session.commit()
            except Exception:
                pass
            try:
                # Normalize to a canonical watch URL to avoid playlists/mixes/etc.
                canonical_url = url
                try:
                    from backend.youtube_captions import extract_video_id as _extract
                    vid_key = _extract(url)
                    if vid_key:
                        canonical_url = f"https://www.youtube.com/watch?v={vid_key}"
                except Exception:
                    pass

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(canonical_url, download=True)
                    # Expected output from FFmpegExtractAudio is .m4a
                    base = ydl.prepare_filename(info)
                    base_no_ext, _ = os.path.splitext(base)
                    produced_m4a = base_no_ext + ".m4a"
                    candidate = produced_m4a if os.path.exists(produced_m4a) else None
                    if not candidate:
                        # Fallback: search for any common audio extension with same base
                        for ext in (".m4a", ".mp4", ".aac", ".mp3", ".webm", ".wav"):
                            p = base_no_ext + ext
                            if os.path.exists(p):
                                candidate = p
                                break
                    if not candidate:
                        raise RuntimeError("Audio file not produced")
                    abs_path = os.path.abspath(candidate)
                _set_status(video_id, status="finished", progress=100, file_path=abs_path)
                # Persist audio_path to DB (project-relative), mark ready
                try:
                    from backend.extensions import db
                    from backend.models.video import Video
                    v = Video.query.get(video_id)
                    if v and abs_path:
                        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                        rel_path = f"/{os.path.relpath(abs_path, project_root)}"
                        v.audio_path = rel_path
                        v.audio_status = "ready"
                        db.session.commit()
                except Exception:
                    pass
            except Exception as e:
                _set_status(video_id, status="error", error=str(e))
                # Reflect error in DB
                try:
                    from backend.extensions import db
                    from backend.models.video import Video
                    v = Video.query.get(video_id)
                    if v:
                        v.audio_status = "failed"
                        db.session.commit()
                except Exception:
                    pass

    t = threading.Thread(target=worker, name=f"dl-{video_id}", daemon=True)
    t.start()
