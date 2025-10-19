# InsightFeed
Site where people can create their own personal news feed


# sqlite web

sqlite_web instance/database.db

## Backend

Flask backend structured with separate `models` and `routes` packages.

- App factory: `backend/__init__.py` (`create_app()`)
- Entrypoint: `backend/app.py`
- Models: `backend/models/user.py`
- Routes: `backend/routes/user.py` (Blueprint at `/users`)
 - Auth: `backend/routes/auth.py` (Blueprint at `/auth`)

Run backend:

```
python -m pip install -r backend/requirements.txt
python backend/app.py
```

The SQLite database lives in `backend/instance/database.db`.

### Auth endpoints
- `POST /auth/register` body: `{ "name": "Jane", "email": "jane@example.com", "password": "secret" }`
  - Returns `{ token, user }` (JWT HS256)
- `POST /auth/login` body: `{ "email": "jane@example.com", "password": "secret" }`
  - Returns `{ token, user }`
- `GET /auth/me` with header `Authorization: Bearer <token>`
  - Returns `{ user }`

JWT config (dev defaults):
- `JWT_SECRET_KEY` env var or default `dev-secret-change-me`
- `JWT_EXPIRES_SECONDS` default `86400`

### AI endpoints
- `POST /ai/videos/:videoId/transcribe` — transcribe downloaded audio (requires `OPENAI_API_KEY`)
- `POST /ai/videos/:videoId/summarize` — generate Markdown summary from saved transcription

Env setup (backend/.env):
```
OPENAI_API_KEY=sk-...
# Optional overrides
# OPENAI_MODEL=gpt-4o-mini
# JWT_SECRET_KEY=your-secret
# YOUTUBE_CAPTIONS_LANGS=en,en-US,en-GB
# YOUTUBE_API_KEY=your-youtube-data-api-key
```

### YouTube captions
- When you add a video with a YouTube URL, the backend fetches public captions (if available) using the YouTube Transcript API and stores the transcript directly in the video row.
- Install dependencies: `python -m pip install -r backend/requirements.txt`
- Config (optional): `YOUTUBE_CAPTIONS_LANGS` (comma separated, default: `en,en-US,en-GB`).
- Responses include `transcribe_status` (`ready` or `failed`) and `summary` generated from the transcript.


# colors

Dark gray 1: #1C1C1C
Dark gray 2: #272725
White: #E3E3E3
Blue: #0B8CE9
Red: #F14E1E
Green: #0BD185
