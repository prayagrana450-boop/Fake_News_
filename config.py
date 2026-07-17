import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _load_secret_key() -> str:
    """Load SECRET_KEY securely.

    - In production, SECRET_KEY must come from environment.
    - In development, a random fallback is generated if missing.
    """

    secret = os.environ.get("SECRET_KEY")
    if secret:
        return secret

    # Dev-only fallback: generate a random value and warn.
    # Werkzeug/Flask sessions rely on this being consistent across restarts,
    # but for local dev it's acceptable.
    try:
        debug_env = os.environ.get("DEBUG", "true").lower() in ("1", "true", "yes")
    except Exception:
        debug_env = True

    if debug_env:
        import secrets

        fallback = secrets.token_urlsafe(32)
        print("[WARN] SECRET_KEY not set. Using a dev-only random fallback.")
        return fallback

    raise RuntimeError(
        "SECRET_KEY environment variable is required in non-debug environments."
    )


class Config:
    # Flask
    SECRET_KEY = _load_secret_key()
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")



    # Cookie hardening


    # ---------------- MySQL ----------------
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "pra@1122")
    DB_NAME = os.getenv("DB_NAME", "ai_fake_news")

    # ---------------- Uploads ----------------
    ALLOWED_EXTENSIONS = (
        "txt",
        "csv",
        "json",
    )


    MAX_PDF_UPLOAD_MB = 10


    # ---------------- Folders ----------------


    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DATASET_FOLDER = os.path.join(BASE_DIR, "dataset")

    MODEL_FOLDER = os.path.join(BASE_DIR, "models")
    MODELS_FOLDER = MODEL_FOLDER

    IMAGES_FOLDER = os.path.join(BASE_DIR, "images")

    MODEL_PATH = os.path.join(MODEL_FOLDER, "model.pkl")
    VECTORIZER_PATH = os.path.join(MODEL_FOLDER, "vectorizer.pkl")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"