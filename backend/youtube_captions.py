import os
import re
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import requests
import logging

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript,
)


YOUTUBE_ID_RE = re.compile(
    r"(?:youtu\.be/|v=|/v/|/embed/|/shorts/)([\w-]{11})",
    re.IGNORECASE,
)


def extract_video_id(url: str) -> Optional[str]:
    if not url:
        return None
    # Handle plain ID
    if re.fullmatch(r"[\w-]{11}", url):
        return url
    try:
        u = urlparse(url)
        # watch?v=ID
        qs = parse_qs(u.query)
        if "v" in qs and qs["v"]:
            vid = qs["v"][0]
            if re.fullmatch(r"[\w-]{11}", vid):
                return vid
        # youtu.be/ID
        parts = [p for p in u.path.split("/") if p]
        if parts:
            # /shorts/ID, /embed/ID, /v/ID, /live/ID, or /ID
            for marker in ("shorts", "embed", "v", "live"):
                if len(parts) >= 2 and parts[0] == marker and re.fullmatch(r"[\w-]{11}", parts[1]):
                    return parts[1]
            if re.fullmatch(r"[\w-]{11}", parts[-1]):
                return parts[-1]
    except Exception:
        pass
    # Regex fallback
    m = YOUTUBE_ID_RE.search(url)
    if m:
        return m.group(1)
    return None


def _langs_from_env() -> List[str]:
    raw = os.environ.get("YOUTUBE_CAPTIONS_LANGS", "en,en-US,en-GB").strip()
    return [p.strip() for p in raw.split(",") if p.strip()]


def _strip_vtt_to_text(vtt: str) -> str:
    lines = []
    for line in (vtt or "").splitlines():
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> ", line):
            continue
        if re.match(r"^\d{2}:\d{2}\.\d{3} --> ", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _download_timedtext(video_id: str, lang: str, asr: bool, name: Optional[str] = None) -> str:
    """Download timedtext (VTT) and return plain text. If name is provided, try with name first.

    For manually created tracks with a custom name, timedtext often requires the exact `name` param.
    """
    def attempt(include_name: bool) -> str:
        params = {
            "v": video_id,
            "lang": lang,
            "fmt": "vtt",
        }
        if asr:
            params["kind"] = "asr"
        if include_name and name:
            params["name"] = name
        try:
            resp = requests.get("https://www.youtube.com/api/timedtext", params=params, timeout=15)
            logging.getLogger(__name__).info(
                "YouTube timedtext response (lang=%s, asr=%s, name=%s, status=%s):\n%s",
                lang,
                asr,
                name if include_name else "",
                resp.status_code,
                resp.text,
            )
            if not resp.ok:
                return ""
            text = _strip_vtt_to_text(resp.text)
            return text
        except requests.RequestException:
            return ""

    # Try with name first for manual tracks
    if name:
        txt = attempt(include_name=True)
        if txt.strip():
            return txt
    # Fallback without name
    return attempt(include_name=False)


def _fetch_via_data_api(video_id: str, prefer_generated: bool) -> str:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return ""
    langs = _langs_from_env()
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/captions",
            params={"part": "snippet", "videoId": video_id, "key": api_key, "maxResults": 50},
            timeout=15,
        )
        logging.getLogger(__name__).info(
            "YouTube Data API captions list response (video_id=%s, status=%s):\n%s",
            video_id,
            resp.status_code,
            resp.text,
        )
    except requests.RequestException:
        return ""
    if not resp.ok:
        return ""
    j = resp.json() or {}
    items = j.get("items") or []
    if not items:
        return ""
    # Pick track by language + manual/generated preference
    def pick(tracks, want_asr: bool):
        # Prefer requested languages order
        for lang in langs:
            for t in tracks:
                sn = t.get("snippet", {})
                if sn.get("language") == lang and bool(sn.get("trackKind") == "ASR") == want_asr:
                    return t
        # Fallback to any language
        for t in tracks:
            sn = t.get("snippet", {})
            if bool(sn.get("trackKind") == "ASR") == want_asr:
                return t
        return None

    manual = [it for it in items if (it.get("snippet", {}).get("trackKind") or "").upper() != "ASR"]
    auto = [it for it in items if (it.get("snippet", {}).get("trackKind") or "").upper() == "ASR"]
    chosen = None
    if prefer_generated:
        chosen = pick(auto, True) or pick(manual, False)
    else:
        chosen = pick(manual, False) or pick(auto, True)
    if not chosen:
        return ""
    sn = chosen.get("snippet", {})
    lang = sn.get("language") or "en"
    asr = (sn.get("trackKind") or "").upper() == "ASR"
    name = sn.get("name") or None
    # Download text via timedtext (does not require OAuth), matching chosen language/kind/name
    text = _download_timedtext(video_id, lang, asr, name=name)
    if not text and name:
        # Final fallback: try without name if named track didn't return content
        text = _download_timedtext(video_id, lang, asr, name=None)
    return text


def fetch_captions_text(video_id: str, prefer_generated: bool = False) -> str:
    langs = _langs_from_env()
    # First try Data API (track selection using API key), then fall back to transcript API
    data_api_text = _fetch_via_data_api(video_id, prefer_generated=prefer_generated)
    if data_api_text:
        return data_api_text
    try:
        lst = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        if prefer_generated:
            try:
                transcript = lst.find_generated_transcript(langs)
            except Exception:
                pass
        if transcript is None:
            try:
                transcript = lst.find_manually_created_transcript(langs)
            except Exception:
                try:
                    transcript = lst.find_generated_transcript(langs)
                except Exception:
                    pass
        if transcript is None:
            # Fall back to direct get_transcript
            segments = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
        else:
            segments = transcript.fetch()
        # Join text lines, skipping empty ones
        parts = [seg.get("text", "").strip() for seg in segments]
        return "\n".join([p for p in parts if p])
    except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript):
        return ""
    except Exception:
        return ""
