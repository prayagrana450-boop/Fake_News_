from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import joblib
import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import PassiveAggressiveClassifier


DATASET_FOLDER = Path("dataset")


def ensure_nltk():
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)


def fix_encoding(text):
    if isinstance(text, str):
        try:
            return text.encode("latin1").decode("utf-8")
        except Exception:
            return text
    return text


def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"www\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def preprocess(text: str, stop_words: set[str], lemmatizer) -> str:
    text = clean_text(text)
    words = re.findall(r"\b\w+\b", text)
    words = [
        lemmatizer.lemmatize(word)
        for word in words
        if word not in stop_words and len(word) > 2
    ]
    return " ".join(words)


def _load_train_dataset() -> tuple[pd.Series, pd.Series]:
    """Loads the same dataset structure used by train_model.py.

    train_model.py expects:
      - dataset/Fake.csv  (label 0)
      - dataset/True.csv  (label 1)

    If those files are missing, fall back to dataset/WELFake_Dataset.csv.
    """
    ensure_nltk()

    fake_path = DATASET_FOLDER / "Fake.csv"
    true_path = DATASET_FOLDER / "True.csv"

    if fake_path.exists() and true_path.exists():
        fake = pd.read_csv(fake_path, encoding="utf-8-sig", low_memory=False)
        true = pd.read_csv(true_path, encoding="utf-8-sig", low_memory=False)

        # Remove BOM artifacts
        fake.columns = fake.columns.str.replace("\ufeff", "", regex=False)
        true.columns = true.columns.str.replace("\ufeff", "", regex=False)

        fake = fake.loc[:, ~fake.columns.str.contains("^Unnamed")]
        true = true.loc[:, ~true.columns.str.contains("^Unnamed")]

        fake["title"] = fake["title"].apply(fix_encoding)
        true["title"] = true["title"].apply(fix_encoding)
        fake["text"] = fake["text"].apply(fix_encoding)
        true["text"] = true["text"].apply(fix_encoding)

        fake["label"] = 0
        true["label"] = 1

        data = pd.concat([fake, true], ignore_index=True)
        data = data[["title", "text", "label"]].copy()
        data["content"] = data["title"].fillna("").astype(str) + " " + data["text"].fillna("").astype(str)
        data.dropna(inplace=True)

        stop_words = set(stopwords.words("english"))
        lemmatizer = WordNetLemmatizer()
        data["content"] = data["content"].astype(str).apply(lambda x: preprocess(x, stop_words, lemmatizer))

        X = data["content"]
        y = data["label"]
        return X, y

    # Fallback: WELFake_Dataset.csv
    wel_path = DATASET_FOLDER / "WELFake_Dataset.csv"
    if not wel_path.exists():
        raise FileNotFoundError(
            "No dataset found for evaluation. Expected dataset/Fake.csv + dataset/True.csv or dataset/WELFake_Dataset.csv"
        )

    df = pd.read_csv(wel_path, encoding="utf-8-sig", low_memory=False)
    df.columns = df.columns.str.replace("\ufeff", "", regex=False)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    # Try common column names
    text_col = "text" if "text" in df.columns else ("content" if "content" in df.columns else df.columns[0])
    label_col = None
    for c in ["label", "class", "target"]:
        if c in df.columns:
            label_col = c
            break

    if label_col is None:
        # last resort: assume binary label is named 'label' or similar
        raise ValueError("Unable to detect label column in WELFake_Dataset.csv")

    # Normalize labels to 0/1
    y_raw = df[label_col]
    if y_raw.dtype == object:
        y = y_raw.astype(str).str.lower().map(lambda v: 1 if v in ["real", "true", "1"] else 0)
    else:
        y = y_raw.astype(int)

    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()
    X = df[text_col].astype(str).apply(lambda x: preprocess(x, stop_words, lemmatizer))

    return X, y


def _compute_metrics(y_true, y_pred) -> dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    report_dict = classification_report(y_true, y_pred, output_dict=True, zero_division=0)

    # Use weighted averages when available
    weighted = report_dict.get("weighted avg") or report_dict.get("macro avg") or {}
    precision = float(weighted.get("precision", 0.0))
    recall = float(weighted.get("recall", 0.0))
    f1 = float(weighted.get("f1-score", 0.0))

    report_text = classification_report(y_true, y_pred, zero_division=0)

    return {
        "accuracy": float(acc),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "classification_report": report_text,
    }


def evaluate_models(random_state: int = 42) -> dict[str, Any]:
    X, y = _load_train_dataset()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=random_state, stratify=y
    )

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=50000,
        ngram_range=(1, 2),
    )

    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=2000, random_state=random_state),
        "PassiveAggressiveClassifier": PassiveAggressiveClassifier(random_state=random_state, max_iter=1000, tol=1e-3),
    }

    results: dict[str, Any] = {}

    for name, model in models.items():
        model.fit(X_train_vec, y_train)
        y_pred = model.predict(X_test_vec)

        metrics = _compute_metrics(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred)
        labels = ["FAKE", "REAL"]  # based on existing train_model mapping fake=0 real=1

        results[name] = {
            "metrics": {
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
            },
            "classification_report": metrics["classification_report"],
            "confusion_matrix": cm.tolist(),
            "confusion_labels": labels,
        }

    return results


def evaluate_models_safely() -> dict[str, Any]:
    """Wrapper for Flask routes."""
    try:
        return {"results": evaluate_models(), "error": None}
    except Exception as e:
        return {"results": {}, "error": str(e)}

