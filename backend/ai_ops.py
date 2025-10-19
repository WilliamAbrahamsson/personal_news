import os
import logging
from typing import Optional

import requests


def summarize_markdown(transcript: str, *, instructions: str = "", model: Optional[str] = None) -> str:
    transcript = (transcript or "").strip()
    if not transcript:
        return ""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""
    model = (model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
    system = (
        "You are an expert summarizer. Respond in clean Markdown. "
        "Write a short intro paragraph followed by a bulleted list of 3–7 key points. "
        "Use headings when helpful (e.g., '# Summary', '## Key Points') and **bold** for emphasis."
    )
    if instructions:
        system += f" Additional instructions: {instructions}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
        "temperature": 0.2,
        "max_tokens": 512,
    }
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=45,
        )
        logging.getLogger(__name__).info(
            "OpenAI summarize status=%s", resp.status_code
        )
        if not resp.ok:
            return ""
        data = resp.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    except requests.RequestException:
        return ""


def openai_transcribe(file_path: str, *, model: Optional[str] = None, language: Optional[str] = None) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""
    model = (model or os.environ.get("OPENAI_TRANSCRIBE_MODEL") or "whisper-1").strip()
    try:
        logging.getLogger(__name__).info(
            "OpenAI transcribe request: model=%s, file=%s", model, os.path.basename(file_path)
        )
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = {"model": model}
            if language:
                data["language"] = language
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=files,
                timeout=120,
            )
        logging.getLogger(__name__).info(
            "OpenAI transcribe response: status=%s", resp.status_code
        )
        if not resp.ok:
            return ""
        j = resp.json()
        return (j.get("text") or "").strip()
    except Exception:
        return ""

