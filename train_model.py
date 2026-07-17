from __future__ import annotations

import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import nltk

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split


# ==========================================
# Fake News Detection System
# Advanced Training Script
# Author : Prayag Rana
# ==========================================

# Dataset Folder (Same as your project)
DATASET_FOLDER = Path("dataset")

# Models Folder (Same as your project)
MODELS_FOLDER = Path("models")




# ==========================================
# Download NLTK Data
# ==========================================

def ensure_nltk():
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)


# ==========================================
# Fix Encoding
# ==========================================

def fix_encoding(text):
    if isinstance(text, str):
        try:
            return text.encode("latin1").decode("utf-8")
        except:
            return text
    return text


# ==========================================
# Clean Text
# ==========================================

def clean_text(text: str) -> str:
    text = str(text).lower()

    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"www\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==========================================
# Preprocess Text
# ==========================================

def preprocess(text, stop_words, lemmatizer):

    text = clean_text(text)

    words = re.findall(r"\b\w+\b", text)

    words = [
        lemmatizer.lemmatize(word)
        for word in words
        if word not in stop_words and len(word) > 2
    ]

    return " ".join(words)


# ==========================================
# Main
# ==========================================

def main():

    ensure_nltk()

    fake_path = DATASET_FOLDER / "Fake.csv"
    true_path = DATASET_FOLDER / "True.csv"

    print("Loading Dataset...")

    fake = pd.read_csv(fake_path,
                       encoding="utf-8-sig",
                       low_memory=False)

    true = pd.read_csv(true_path,
                       encoding="utf-8-sig",
                       low_memory=False)

    # Remove BOM
    fake.columns = fake.columns.str.replace("\ufeff", "", regex=False)
    true.columns = true.columns.str.replace("\ufeff", "", regex=False)

    # Remove unnamed columns
    fake = fake.loc[:, ~fake.columns.str.contains("^Unnamed")]
    true = true.loc[:, ~true.columns.str.contains("^Unnamed")]

    # Fix Encoding
    fake["title"] = fake["title"].apply(fix_encoding)
    true["title"] = true["title"].apply(fix_encoding)

    fake["text"] = fake["text"].apply(fix_encoding)
    true["text"] = true["text"].apply(fix_encoding)

    # Labels
    fake["label"] = 0
    true["label"] = 1

    # Merge
    data = pd.concat([fake, true], ignore_index=True)


    # Keep required columns
    data = data[["title", "text", "label"]]
    # Combine title and text
    data["content"] = (
    data["title"].fillna("").astype(str) + " " +
    data["text"].fillna("").astype(str)
    )

    # Remove Missing Values
    data.dropna(inplace=True)

    # Shuffle Dataset
    data = data.sample(frac=1,
                       random_state=42).reset_index(drop=True)

    print("Total Samples :", len(data))

    stop_words = set(stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()

    # Text Cleaning
    data["content"] = data["content"].astype(str).apply(

        lambda x: preprocess(x,stop_words,
                             lemmatizer)
    )

    X = data["content"]
    y = data["label"]

    # Train Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print("Training :", len(X_train))
    print("Testing  :", len(X_test))

    # TF-IDF
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=50000,
        ngram_range=(1, 2)
    )

    X_train = vectorizer.fit_transform(X_train)
    X_test = vectorizer.transform(X_test)

    print("TF-IDF Applied")

    # Logistic Regression
    model = LogisticRegression(
        max_iter=2000,
        random_state=42
    )

    model.fit(X_train, y_train)

    print("Model Training Completed")

    # Prediction
    prediction = model.predict(X_test)

    accuracy = accuracy_score(y_test, prediction)

    print("\nAccuracy :", accuracy)

    print("\nClassification Report\n")

    print(classification_report(
        y_test,
        prediction,
        zero_division=0
    ))

    print("\nConfusion Matrix\n")

    print(confusion_matrix(
        y_test,
        prediction
    ))

    # Save Models
    MODELS_FOLDER.mkdir(exist_ok=True)

    joblib.dump(
        model,
        MODELS_FOLDER / "model.pkl"
    )

    joblib.dump(
        vectorizer,
        MODELS_FOLDER / "vectorizer.pkl"
    )

    metadata = {

    "accuracy": float(accuracy),

    "total_samples": len(data),

    "train_samples": X_train.shape[0],

    "test_samples": X_test.shape[0],

    "max_features": 50000,

    "ngram_range": [1, 2]

    }

    with open(MODELS_FOLDER / "metadata.json",
              "w",
              encoding="utf-8") as f:

        json.dump(metadata,
                  f,
                  indent=4)

    print("\nModel Saved Successfully")

    print("models/model.pkl")

    print("models/vectorizer.pkl")

    print("models/metadata.json")


if __name__ == "__main__":
    main()