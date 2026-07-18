# ==========================================
# AI Fake News Detection System
# Prediction Module
# ==========================================

from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
from config import Config


# ==========================================
# Clean Text
# ==========================================

def clean_text(text: str) -> str:
    text = str(text).lower()

    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"www\S+", " ", text)

    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ==========================================
# NLP Preprocessing
# ==========================================

def preprocess(text: str, stop_words: set[str], lemmatizer) -> str:
    text = clean_text(text)

    words = text.split()
    words = [
        lemmatizer.lemmatize(word)
        for word in words
        if word not in stop_words
    ]

    return " ".join(words)


# ==========================================
# Predictor Class
# ==========================================


_PREDICTOR_SINGLETON: "Predictor | None" = None


class Predictor:

    """Loads ML artifacts and performs predictions.

    Notes:
    - NLTK resources are expected to be present (train_model.py downloads them once).
    - No downloads happen at request-time for performance.
    """

    def __init__(self):
        # Lazy import so app can start even if NLTK is partially unavailable.
        import nltk
        from nltk.corpus import stopwords
        from nltk.stem import WordNetLemmatizer

        self.models_dir = Path(Config.MODELS_FOLDER)

        model_path = self.models_dir / "model.pkl"
        vectorizer_path = self.models_dir / "vectorizer.pkl"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found:\n{model_path}\n\nRun train_model.py first."
            )

        if not vectorizer_path.exists():
            raise FileNotFoundError(
                f"Vectorizer file not found:\n{vectorizer_path}\n\nRun train_model.py first."
            )

        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)

        # Ensure stopwords/lemmatizer resources are available.
        # On Render/production, automatically download missing NLTK data (first startup)
        # instead of crashing.
        try:
            # Store NLTK data under project-local directory so it can persist in Render.
            # (If directory isn't writable on a given platform, nltk will fallback.)
            try:
                nltk.data.path.append(str(Path("nltk_data")))
            except Exception:
                pass

            required_resources = [
                "stopwords",
                "punkt",
                "wordnet",
                "omw-1.4",
            ]

            for res in required_resources:
                try:
                    nltk.data.find(f"corpora/{res}")
                except LookupError:
                    nltk.download(res, quiet=True)

            self.stop_words = set(stopwords.words("english"))
            self.lemmatizer = WordNetLemmatizer()

        except Exception as e:
            # Never crash the whole app due to NLTK.
            # Fall back to no stopword filtering.
            self.stop_words = set()
            self.lemmatizer = WordNetLemmatizer()
            import logging

            logging.getLogger(__name__).warning(
                "NLTK initialization failed; continuing with fallback. Error: %s",
                e,
            )


        metadata_file = self.models_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

    def predict(self, text: str) -> dict:

        processed = preprocess(text, self.stop_words, self.lemmatizer)
        vector = self.vectorizer.transform([processed])

        prediction = self.model.predict(vector)[0]
        probability = self.model.predict_proba(vector)[0]

        confidence = float(max(probability))

        # Training labels: fake=0, real=1 => prediction==1 => REAL
        label = "REAL" if int(prediction) == 1 else "FAKE"

        return {
            "prediction": int(prediction),
            "prediction_label": label,
            "confidence": round(confidence * 100, 2),
            "fake_probability": round(float(probability[0]) * 100, 2),
            "real_probability": round(float(probability[1]) * 100, 2),
            "metadata": self.metadata,
        }


def get_predictor() -> Predictor:
    global _PREDICTOR_SINGLETON
    if _PREDICTOR_SINGLETON is None:
        _PREDICTOR_SINGLETON = Predictor()
    return _PREDICTOR_SINGLETON


