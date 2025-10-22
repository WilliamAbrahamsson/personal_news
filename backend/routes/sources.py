from flask import Blueprint, jsonify, request, g, current_app
import os
import glob
import re
import shutil
import requests

from backend.auth_utils import auth_required
from backend.extensions import db
from backend.models.source import Source
from backend.models.video import Video
from backend.youtube_captions import extract_video_id

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
            try:
                u = value
                chan_id = handle = None
                # Parse possible URL or handle
                if u.startswith("@"):
                    handle = u[1:]
                m = re.search(r"/channel/([A-Za-z0-9_-]+)", u)
                if m:
                    chan_id = m.group(1)
                mh = re.search(r"/@([A-Za-z0-9._-]+)", u)
                if mh:
                    handle = mh.group(1)

                # Lookup channel info
                if chan_id:
                    r = requests.get(
                        "https://www.googleapis.com/youtube/v3/channels",
                        params={"part": "snippet", "id": chan_id, "key": api_key},
                        timeout=12,
                    )
                    if r.ok:
                        items = (r.json() or {}).get("items") or []
                        if items:
                            label = items[0].get("snippet", {}).get("title")
                elif handle:
                    r = requests.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part": "snippet",
                            "type": "channel",
                            "q": handle,
                            "maxResults": 1,
                            "key": api_key,
                        },
                        timeout=12,
                    )
                    if r.ok:
                        items = (r.json() or {}).get("items") or []
                        if items:
                            it = items[0]
                            label = it.get("snippet", {}).get("channelTitle")
                            ch_id = it.get("snippet", {}).get("channelId")
                            if ch_id:
                                value = f"https://www.youtube.com/channel/{ch_id}"
            except Exception:
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
    """Add a new video under a source and run AI pipeline."""
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

    # Fetch YouTube metadata
    vid_id = extract_video_id(url)
    api_key = os.environ.get("YOUTUBE_API_KEY")

    title = description = channel_title = published_at = None
    views = likes = dislikes = comments = None

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
                    dislikes = to_int(st.get("dislikeCount"))
                    comments = to_int(st.get("commentCount"))
        except Exception:
            pass

    # Create video record
    video = Video(
        source_id=src.id,
        url=url,
        title=title or url,
        description=description,
        channel_title=channel_title,
        view_count=views,
        like_count=likes,
        dislike_count=dislikes,
        comment_count=comments,
        published_at=published_at,
    )
    db.session.add(video)
    db.session.commit()

    # ✅ Trigger the AI pipeline asynchronously (new ai.py system)
    try:
        from backend.routes.ai import _run_async
        current_app.logger.info("Starting full AI pipeline for video_id=%s", video.id)
        _run_async(current_app._get_current_object(), video.id, video.url)
    except Exception as e:
        current_app.logger.exception("Pipeline start failed for video_id=%s: %s", video.id, e)

    return jsonify(video.to_dict()), 201


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
# VIDEO DETAILS / UPDATE / DELETE
# ---------------------------------
@bp.get("/<int:source_id>/videos/<int:video_id>")
@auth_required
def get_video(source_id: int, video_id: int):
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404
    return jsonify(vid.to_dict())


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
        text = (data.get("transcribe") or "").strip()
        vid.transcribe = text
        vid.transcribe_status = "ready" if text else ""

    db.session.commit()
    return jsonify(vid.to_dict())


@bp.delete("/<int:source_id>/videos/<int:video_id>")
@auth_required
def delete_video(source_id: int, video_id: int):
    """Delete a video and its local audio if present."""
    src, vid = _get_owned_source_and_video(source_id, video_id)
    if not src:
        return jsonify(error="Source not found"), 404
    if not vid:
        return jsonify(error="Video not found"), 404

    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if getattr(vid, "audio_path", None):
            path = os.path.join(project_root, vid.audio_path.lstrip("/"))
            if os.path.isfile(path):
                os.remove(path)
    except Exception:
        pass

    db.session.delete(vid)
    db.session.commit()
    return jsonify(message="Video deleted"), 200


# ---------------------------------
# FETCH LATEST VIDEOS
# ---------------------------------
# ---------------------------------
# FETCH LATEST VIDEOS (range-based)
# ---------------------------------
@bp.get("/<int:source_id>/fetch_latest")
@auth_required
def fetch_latest_videos(source_id: int):
    """Fetch YouTube videos from index 'from' to 'to' (range-based pagination)."""
    src = Source.query.get(source_id)
    if not src or src.user_id != g.current_user.id:
        return jsonify(error="Source not found"), 404

    if src.type != "youtube_channel":
        return jsonify(error="Unsupported source type"), 400

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return jsonify(error="Missing YOUTUBE_API_KEY"), 500

    # Extract channel ID
    m = re.search(r"/channel/([A-Za-z0-9_-]+)", src.value)
    chan_id = m.group(1) if m else None
    if not chan_id:
        return jsonify(error="Unable to extract channel ID from source"), 400

    # Range parameters
    from_idx = request.args.get("from", 0, type=int)
    to_idx = request.args.get("to", 10, type=int)
    if to_idx <= from_idx:
        return jsonify(error="'to' must be greater than 'from'"), 400

    # Clamp and calculate
    max_total = 200  # safety limit
    from_idx = max(0, min(from_idx, max_total))
    to_idx = max(from_idx + 1, min(to_idx, max_total))
    batch_size = to_idx - from_idx
    max_batch = 50  # YouTube API max per call

    # Compute which "page" of YouTube results to fetch
    # YouTube API supports 'pageToken', but we can emulate by repeatedly calling until reaching the requested range.
    all_videos = []
    next_page = None
    fetched = 0

    try:
        while len(all_videos) < to_idx and (fetched < 5):  # avoid too many API calls
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": chan_id,
                    "order": "date",
                    "maxResults": min(max_batch, to_idx - len(all_videos)),
                    "type": "video",
                    "key": api_key,
                    **({"pageToken": next_page} if next_page else {}),
                },
                timeout=15,
            )
            if not r.ok:
                return jsonify(error=f"YouTube API error: {r.status_code}"), 502

            j = r.json() or {}
            items = j.get("items", [])
            next_page = j.get("nextPageToken")
            fetched += 1

            for it in items:
                sn = it.get("snippet", {})
                vid_id = it.get("id", {}).get("videoId")
                if not vid_id:
                    continue
                all_videos.append({
                    "video_id": vid_id,
                    "title": sn.get("title"),
                    "description": sn.get("description"),
                    "published_at": sn.get("publishedAt"),
                    "thumbnail": (
                        sn.get("thumbnails", {}).get("medium", {}).get("url")
                        or sn.get("thumbnails", {}).get("default", {}).get("url")
                    ),
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "channel_title": sn.get("channelTitle"),
                })

            if not next_page or len(all_videos) >= to_idx:
                break

        # Slice requested window
        videos = all_videos[from_idx:to_idx]
        return jsonify({
            "items": videos,
            "range": {"from": from_idx, "to": to_idx},
            "total_fetched": len(videos),
            "has_more": bool(next_page),
        })

    except Exception as e:
        current_app.logger.exception("Failed to fetch latest videos: %s", e)
        return jsonify(error="Failed to fetch latest videos"), 500
