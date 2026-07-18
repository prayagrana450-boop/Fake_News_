from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, session


from config import Config
from database import init_db, close_db
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.prediction_routes import prediction_bp
from routes.admin_routes import admin_bp
from routes.admin_login_routes import admin_login_bp






def create_app() -> Flask: 
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load config
    app.config.from_object(Config)

    # Ensure directories exist
    for d in [
        app.config["UPLOAD_FOLDER"],
        app.config["DATASET_FOLDER"],
        app.config["MODELS_FOLDER"],
        app.config["IMAGES_FOLDER"],
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Initialize MySQL tables
    init_db(app)

    # Register blueprints (each exactly once)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_login_bp)


    # Guard against accidental admin session leakage.
    @app.before_request
    def _admin_session_sanity_check():
        # If is_admin is set but admin_id is missing, clear.
        if session.get("is_admin") and not session.get("admin_id"):
            session.pop("is_admin", None)

    # Close DB on teardown

    app.teardown_appcontext(close_db)

    # Set secret key
    app.secret_key = app.config["SECRET_KEY"]

    # Security defaults
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    return app


app = create_app()


if __name__ == "__main__":

    model_files = [
        Path(Config.MODELS_FOLDER) / "model.pkl",
        Path(Config.MODELS_FOLDER) / "vectorizer.pkl",
        Path(Config.MODELS_FOLDER) / "metadata.json",
    ]

    missing = [str(p) for p in model_files if not p.exists()]

    if missing:
        print("[WARN] ML artifacts missing:")
        for file in missing:
            print(file)

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )

