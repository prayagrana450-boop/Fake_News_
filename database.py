from __future__ import annotations

import os

import mysql.connector
from flask import current_app, g
from mysql.connector import pooling


def get_db_pool(app) -> pooling.MySQLConnectionPool:
    cfg = app.config
    return pooling.MySQLConnectionPool(
        pool_name="fake_news_pool",
        pool_size=10,
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        autocommit=True,
    )


def get_db():
    """Get a per-request connection using a small pool.

    Note: we rebuild the pool lazily in current_app context to avoid importing
    config at import-time.
    """

    if "db" not in g:
        app = current_app
        pool = get_db_pool(app)
        g.db = pool.get_connection()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def init_db(app):
    """Create tables if they don't exist.

    Fails gracefully if MySQL is unreachable (e.g. local dev without creds).
    """

    with app.app_context():
        try:
            db = get_db()
        except Exception as e:
            app.logger.warning("[WARN] Database init skipped: %s", e)
            return

        cur = db.cursor(dictionary=True)

        # Users
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) NOT NULL UNIQUE,
                email VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin','user') NOT NULL DEFAULT 'user',
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Prediction history
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                input_text LONGTEXT NOT NULL,
                input_filename VARCHAR(255) NULL,
                prediction_label VARCHAR(50) NOT NULL,
                confidence DECIMAL(10,6) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_created (user_id, created_at),
                CONSTRAINT fk_pred_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Optional columns for PDF predictions (added via ALTER, no new tables)
        # - input_type: 'TEXT' or 'PDF'
        # - extracted_text: extracted plain text for PDF inputs
        cur.execute("SHOW COLUMNS FROM prediction_history LIKE 'input_type'")
        has_input_type = bool(cur.fetchone())
        if not has_input_type:
            cur.execute(
                "ALTER TABLE prediction_history ADD COLUMN input_type VARCHAR(10) NULL"
            )

        cur.execute("SHOW COLUMNS FROM prediction_history LIKE 'extracted_text'")
        has_extracted_text = bool(cur.fetchone())
        if not has_extracted_text:
            cur.execute(
                "ALTER TABLE prediction_history ADD COLUMN extracted_text LONGTEXT NULL"
            )

        # Backfill input_type for older rows (best-effort)
        try:
            cur.execute(
                "UPDATE prediction_history SET input_type='TEXT' WHERE input_type IS NULL"
            )
        except Exception:
            pass


        # Safe migrations for legacy DBs: ensure confidence column exists and is NOT NULL
        # (Some student DBs may have been created without it or with a different nullability.)
        cur.execute("SHOW COLUMNS FROM prediction_history LIKE 'confidence'")
        has_conf_col = bool(cur.fetchone())
        if not has_conf_col:
            cur.execute(
                "ALTER TABLE prediction_history ADD COLUMN confidence DECIMAL(10,6) NOT NULL DEFAULT 0"
            )

        # If column exists but is nullable (or type mismatch), make it NOT NULL (best-effort)
        # MySQL will throw if incompatible; we keep it safe.
        try:
            cur.execute(
                "ALTER TABLE prediction_history MODIFY confidence DECIMAL(10,6) NOT NULL"
            )
        except Exception:
            pass


        # Datasets
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                text LONGTEXT NOT NULL,
                label VARCHAR(50) NOT NULL,
                created_by INT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_label_created (label, created_at),
                CONSTRAINT fk_dataset_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Reports
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                report_type VARCHAR(80) NOT NULL,
                payload JSON NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_report_type_created (report_type, created_at),
                CONSTRAINT fk_reports_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Admins (separate from users)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fullname VARCHAR(120) NOT NULL,
                email VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )


        # Optional default admin for dev is intentionally disabled here to enforce separation.
        # Admins must authenticate ONLY via the admins table (see routes/admin_login_routes.py).
        cur.close()



