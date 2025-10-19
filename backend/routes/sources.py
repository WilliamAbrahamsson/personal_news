from flask import Blueprint, jsonify, request, g, current_app
import os
import glob
import shutil

from backend.auth_utils import auth_required
from backend.extensions import db
from backend.models.source import Source
from backend.models.video import Video
from backend.youtube_captions import extract_video_id
import re
import requests

bp = Blueprint("sources", __name__, url_prefix="/sources")


# ---------------------------------
# SOURCES
# ---------------------------------
@bp.get("")
@auth_required
def list_sources():
    """List all sources belonging to the authenticated user."""
    items = (
        Source.query.filter_by(user_id=g.current_user.id)
        .order_by(Source.id.desc())
        .all()
    )
    return jsonify([s.to_dict() for s in items])


@bp.post("")
@auth_required
def add_source():
    """Add a new YouTube channel source."""
    data = request.get_json() or {}
    type_ = (data.get("type") or "").strip().lower()
    value = (data.get("value") or "").strip()
    label = (data.get("label") or "").strip() or None

    if not type_ or not value:
        return jsonify(error="'type' and 'value' are required"), 400
    if type_ != "youtube_channel":
        return jsonify(error="Unsupported source type"), 400

    # Auto-resolve channel label via YouTube Data API if not provided
    if not label:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            chan_id = None
            handle = None
            try:
                u = value
                # Accept raw handle
                if u.startswith("@"):
                    handle = u[1:]
                # Extract from URL patterns
                m = re.search(r"/channel/([A-Za-z0-9_-]+)", u)
                if m:
                    chan_id = m.group(1)
                mh = re.search(r"/@([A-Za-z0-9._-]+)", u)
                if mh:
                    handle = mh.group(1)
                # Resolve channel title
                if chan_id:
                    r = requests.get(
                        "https://www.googleapis.com/youtube/v3/channels",
                        params={"part": "snippet", "id": chan_id, "key": api_key},
                        timeout=12,
                    )
                    if r.ok:
                        items = (r.json() or {}).get("items") or []
                        if items:
                            label = items[0].get("snippet", {}).get("title") or None
                elif handle:
                    r = requests.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={"part": "snippet", "type": "channel", "q": handle, "maxResults": 1, "key": api_key},
                        timeout=12,
                    )
                    if r.ok:
                        items = (r.json() or {}).get("items") or []
                        if items:
                            it = items[0]
                            label = it.get("snippet", {}).get("channelTitle") or it.get("snippet", {}).get("title") or None
                            # Update value to canonical channel URL when possible
                            ch_id = it.get("snippet", {}).get("channelId") or None
                            if ch_id:
                                value = f"https://www.youtube.com/channel/{ch_id}"
            except Exception:
                # Best-effort only; leave label as None if API fails
                pass

    src = Source(user_id=g.current_user.id, type=type_, value=value, label=label)
    db.session.add(src)
    db.session.commit()
    return jsonify(src.to_dict()), 201


@bp.get("/<int:source_id>")
@auth_required
def get_source(source_id: int):
    """Retrieve a specific source."""
    src = Source.query.get(source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Source not found"), 404
    return jsonify(src.to_dict())


# ---------------------------------
# VIDEOS
# ---------------------------------
@bp.get("/<int:source_id>/videos")
@auth_required
def list_videos(source_id: int):
    """List all videos under a source."""
    src = Source.query.get(source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Source not found"), 404
    return jsonify([v.to_dict() for v in src.videos])


@bp.post("/<int:source_id>/videos")
@auth_required
def add_video(source_id: int):
    """Add a new video under a source."""
    src = Source.query.get(source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Source not found"), 404

    data = request.get_json() or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify(error="'url' is required"), 400

    existing = Video.query.filter_by(source_id=src.id, url=url).first()
    if existing:
        return jsonify(error="Video already added"), 409

    vid_id = extract_video_id(url)
    # Fetch YouTube metadata
    title = None
    channel_title = None
    description = None
    views = likes = dislikes = comments = None
    published_at = None
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if vid_id and api_key:
        try:
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics",
                    "id": vid_id,
                    "key": api_key,
                },
                timeout=15,
            )
            if r.ok:
                j = r.json() or {}
                items = j.get("items") or []
                if items:
                    it = items[0]
                    sn = it.get("snippet", {})
                    st = it.get("statistics", {})
                    title = (sn.get("title") or "").strip() or None
                    description = sn.get("description")
                    channel_title = sn.get("channelTitle")
                    published_at = sn.get("publishedAt")
                    def to_int(x):
                        try:
                            return int(x)
                        except Exception:
                            return None
                    views = to_int(st.get("viewCount"))
                    likes = to_int(st.get("likeCount"))
                    dislikes = to_int(st.get("dislikeCount"))  # may be unavailable
                    comments = to_int(st.get("commentCount"))
        except Exception:
            pass

    video = Video(
        source_id=src.id,
        url=url,
        title=title or url,
        channel_title=channel_title,
        description=description,
        view_count=views,
        like_count=likes,
        dislike_count=dislikes,
        comment_count=comments,
        published_at=published_at,
    )

    db.session.add(video)
    db.session.commit()
    # Run full pipeline synchronously; respond only when finished
    try:
        from backend.pipeline_manager import run_full_pipeline
        current_app.logger.info("Pipeline run (sync) video_id=%s", video.id)
        run_full_pipeline(current_app._get_current_object(), video.id, video.url)
    except Exception as e:
        current_app.logger.exception("Pipeline run failed for video_id=%s: %s", video.id, e)
        return jsonify(error="Pipeline failed"), 500
    # Fetch fresh row and return
    fresh = Video.query.get(video.id)
    return jsonify(fresh.to_dict()), 201


# ---------------------------------
# HELPERS
# ---------------------------------
def _get_owned_source_and_video(source_id: int, video_id: int):
    """Ensure source and video belong to current user."""
    src = Source.query.get(source_id)
    if not src or src.user_id != g.current_user.id:
        return None, None
    vid = Video.query.get(video_id)
    if not vid or vid.source_id != src.id:
        return src, None
    return src, vid


# ---------------------------------
# VIDEO OPERATIONS
# ---------------------------------
@bp.get("/<int:source_id>/videos/<int:video_id>")
@auth_required
def get_video(source_id: int, video_id: int):
    """Retrieve details for a specific video."""
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404
    return jsonify(vid.to_dict())


# ---------------------------------
# DOWNLOAD MANAGEMENT
# ---------------------------------

@bp.post("/<int:source_id>/videos/<int:video_id>/transcribe")
@auth_required
def start_video_download(source_id: int, video_id: int):
    """Start downloading the YouTube video (async). Returns 202 or 200 if already downloaded/in progress."""
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404

    # If already in progress, short-circuit
    try:
        from backend.download_manager import get_status, queue_download
        st = get_status(vid.id)
        if st.get("status") in ("queued", "starting", "downloading", "processing"):
            fp = st.get("file_path")
            if fp:
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                try:
                    st["file_path"] = f"/{os.path.relpath(fp, project_root)}"
                except Exception:
                    pass
            return jsonify(message="Download already in progress", **st), 202
    except Exception:
        pass

    # If file exists on disk, return finished
    out_dir = current_app.config.get("VIDEO_DIR")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception:
        pass
    vid_key = extract_video_id(vid.url) or str(video_id)
    existing = sorted(glob.glob(os.path.join(out_dir, f"{vid_key}.*")))
    if existing:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        rel_path = f"/{os.path.relpath(existing[0], project_root)}"
        return jsonify(message="Already downloaded", status="finished", progress=100, file_path=rel_path), 200

    # Queue download
    try:
        from backend.download_manager import queue_download
        queue_download(current_app._get_current_object(), vid.id, vid.url)
    except Exception as e:
        current_app.logger.exception("Failed to queue download: %s", e)
        return jsonify(error="Failed to queue download"), 500

    return jsonify(message="Download started", status="starting", progress=0), 202


@bp.get("/<int:source_id>/videos/<int:video_id>/download_status")
@auth_required
def video_download_status(source_id: int, video_id: int):
    """Return current download status and progress for the video."""
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404

    try:
        from backend.download_manager import get_status
        st = get_status(vid.id)
    except Exception:
        st = {"status": "idle", "progress": 0}

    # Map absolute file path to project-relative for clients
    fp = st.get("file_path")
    if fp:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        try:
            st["file_path"] = f"/{os.path.relpath(fp, project_root)}"
        except Exception:
            pass

    # If idle/error but file exists, report finished
    if st.get("status") in (None, "idle") or (st.get("status") == "error" and not st.get("file_path")):
        out_dir = current_app.config.get("VIDEO_DIR")
        vid_key = extract_video_id(vid.url) or str(video_id)
        existing = sorted(glob.glob(os.path.join(out_dir, f"{vid_key}.*")))
        if existing:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            rel_path = f"/{os.path.relpath(existing[0], project_root)}"
            st = {"status": "finished", "progress": 100, "file_path": rel_path}
    return jsonify(st)


## AI endpoints have been moved to /ai blueprint


@bp.patch("/<int:source_id>/videos/<int:video_id>")
@auth_required
def update_video(source_id: int, video_id: int):
    """Update video title or transcript."""
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404

    data = request.get_json() or {}
    if "title" in data:
        vid.title = (data.get("title") or "").strip() or None
    if "transcribe" in data:
        transcribe = (data.get("transcribe") or "").strip()
        vid.transcribe = transcribe
        # Do not call AI here; summaries are handled via /ai endpoints
        vid.transcribe_status = "ready" if transcribe else ""

    db.session.commit()
    return jsonify(vid.to_dict())


@bp.delete("/<int:source_id>/videos/<int:video_id>")
@auth_required
def delete_video(source_id: int, video_id: int):
    """Delete a video owned by the current user. Best‑effort cleanup of leftover files."""
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404

    # Attempt to remove any stored audio artifacts if present
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if getattr(vid, "audio_path", None):
            p = os.path.join(project_root, vid.audio_path.lstrip("/"))
            if os.path.isfile(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
    except Exception:
        pass

    db.session.delete(vid)
    db.session.commit()
    return jsonify(message="Video deleted"), 200
