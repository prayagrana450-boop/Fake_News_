# Fake News Detection System (Flask + ML + MySQL)

Production-ready Flask + ML + MySQL project.

BlackboxAI-generated UI templates and static assets are included.


## Features
- Login authentication (session-based)
- Admin and user dashboards
- File upload for prediction
- Prediction APIs and UI
- Prediction history
- CRUD operations for users and datasets
- MySQL schema creation on startup
- Logistic Regression model with TF-IDF + NLTK preprocessing
- Charts and reports (Chart.js)

## Run (exact commands)
1. Install dependencies:
   - `pip install -r requirements.txt`
2. Train model (creates bootstrap dataset on first run if missing):
   - `python train_model.py`
3. Start server:
   - `python app.py`

## MySQL configuration
- App uses these env vars (defaults shown):
  - `DB_HOST` (127.0.0.1)
  - `DB_PORT` (3306)
  - `DB_USER` (root)
  - `DB_PASSWORD` (empty by default)
  - `DB_NAME` (fake_news_db)

## First admin user
- On startup, if no admin exists, a default admin is created:
  - username: `admin`
  - password: `admin123`


## Notes
- Model artifacts are saved under `model/`.
- Uploaded files are stored under `uploads/`.

