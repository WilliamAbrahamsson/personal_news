import os
from flask import Flask, jsonify
from dotenv import load_dotenv

from backend.extensions import db


def create_app() -> Flask:
    # Force instance folder to live under backend/instance to match repo
    instance_path = os.path.join(os.path.dirname(__file__), "instance")
    app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

    # Load environment from backend/.env for local dev
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

    # Ensure instance folder exists (for SQLite DB, etc.)
    os.makedirs(app.instance_path, exist_ok=True)

    # Configure SQLite database stored in the instance folder
    db_path = os.path.join(app.instance_path, "database.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Allow use from background threads (SQLite)
    try:
        engine_opts = app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
        conn_args = engine_opts.setdefault("connect_args", {})
        conn_args.setdefault("check_same_thread", False)
    except Exception:
        pass

    # Initialize extensions
    db.init_app(app)

    # Defaults for JWT config
    app.config.setdefault("JWT_SECRET_KEY", os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me"))
    app.config.setdefault("JWT_EXPIRES_SECONDS", int(os.environ.get("JWT_EXPIRES_SECONDS", 60 * 60 * 24)))
    # Captions and media storage (paths under backend/ by default)
    default_captions_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "captions"))
    app.config.setdefault("CAPTIONS_DIR", os.environ.get("CAPTIONS_DIR", default_captions_dir))
    # Legacy audio dir (kept for backwards compatibility)
    default_audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "video-audio"))
    app.config.setdefault("AUDIO_DIR", os.environ.get("AUDIO_DIR", default_audio_dir))
    # Video downloads directory
    default_video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "videos"))
    app.config.setdefault("VIDEO_DIR", os.environ.get("VIDEO_DIR", default_video_dir))

    # Register blueprints
    from backend.routes.user import bp as user_bp
    from backend.routes.auth import bp as auth_bp
    from backend.routes.sources import bp as sources_bp
    from backend.routes.videos import bp as videos_bp
    from backend.routes.ai import bp as ai_bp
    app.register_blueprint(user_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sources_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(ai_bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Lightweight SQLite migration: add 'transcribe' column to 'videos' if missing
        try:
            from sqlalchemy import text
            from sqlalchemy.engine import Connection
            conn: Connection = db.engine.connect()
            cols = conn.exec_driver_sql("PRAGMA table_info(videos)").fetchall()
            col_names = {row[1] for row in cols} if cols else set()
            if "transcribe" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN transcribe TEXT DEFAULT ''")
                conn.exec_driver_sql("UPDATE videos SET transcribe='' WHERE transcribe IS NULL")
            if "summary" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN summary TEXT DEFAULT ''")
                conn.exec_driver_sql("UPDATE videos SET summary='' WHERE summary IS NULL")
            if "audio_path" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN audio_path TEXT DEFAULT ''")
                conn.exec_driver_sql("UPDATE videos SET audio_path='' WHERE audio_path IS NULL")
            if "audio_status" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN audio_status TEXT DEFAULT ''")
                conn.exec_driver_sql("UPDATE videos SET audio_status='' WHERE audio_status IS NULL")
            if "transcribe_status" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN transcribe_status TEXT DEFAULT ''")
                conn.exec_driver_sql("UPDATE videos SET transcribe_status='' WHERE transcribe_status IS NULL")
            # YouTube metadata columns
            if "channel_title" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN channel_title TEXT")
            if "description" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN description TEXT")
            if "view_count" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN view_count INTEGER")
            if "like_count" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN like_count INTEGER")
            if "dislike_count" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN dislike_count INTEGER")
            if "comment_count" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN comment_count INTEGER")
            if "published_at" not in col_names:
                conn.exec_driver_sql("ALTER TABLE videos ADD COLUMN published_at TEXT")
            conn.close()
        except Exception:
            # Best-effort; skip if not SQLite or table not present yet
            pass

    @app.after_request
    def add_cors_headers(resp):
        # Simple CORS for local dev (Vite default port)
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        resp.headers.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
        resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        return resp

    @app.route("/")
    def index():
        return jsonify(message="Flask + SQLite running successfully!")

    return app
