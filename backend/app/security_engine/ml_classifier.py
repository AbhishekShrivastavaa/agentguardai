"""Small local text classifier used as a second signal by the security rules."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


MODEL_PATH = Path(__file__).with_name("security_model.json")
MODEL_THRESHOLD = 0.90


def text_features(text: str) -> list[str]:
    """Return word and adjacent-word features for a prompt."""
    words = re.findall(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", text.lower())
    bigrams = [f"bi:{left} {right}" for left, right in zip(words, words[1:])]
    return words + bigrams


def fit_model(samples: list[dict[str, str]]) -> dict[str, Any]:
    """Train a multinomial Naive Bayes text model with Laplace smoothing."""
    labels: dict[str, dict[str, Any]] = {}
    vocabulary: set[str] = set()

    for label in ("attack", "benign"):
        rows = [row for row in samples if row["label"] == label]
        counts: Counter[str] = Counter()
        for row in rows:
            features = text_features(row["text"])
            counts.update(features)
            vocabulary.update(features)
        labels[label] = {
            "documents": len(rows),
            "token_total": sum(counts.values()),
            "token_counts": dict(counts),
        }

    if not labels["attack"]["documents"] or not labels["benign"]["documents"]:
        raise ValueError("Training data must contain both attack and benign examples.")

    return {
        "version": 1,
        "algorithm": "multinomial_naive_bayes_word_unigram_bigram",
        "threshold": MODEL_THRESHOLD,
        "training_samples": len(samples),
        "vocabulary_size": len(vocabulary),
        "vocabulary": sorted(vocabulary),
        "labels": labels,
    }


def predict_attack_probability(text: str, model: dict[str, Any] | None = None) -> float:
    """Return P(attack | text); returns 0.5 if no trained artifact is available."""
    if model is None:
        try:
            model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0.5

    labels = model["labels"]
    class_count = len(labels)
    vocabulary_size = max(1, int(model["vocabulary_size"]))
    document_total = sum(item["documents"] for item in labels.values())
    vocabulary = set(model["vocabulary"])
    features = text_features(text)
    log_scores: dict[str, float] = {}

    for label, stats in labels.items():
        score = math.log((stats["documents"] + 1) / (document_total + class_count))
        denominator = stats["token_total"] + vocabulary_size
        token_counts = stats["token_counts"]
        for feature in features:
            if feature in vocabulary:
                score += math.log((token_counts.get(feature, 0) + 1) / denominator)
        log_scores[label] = score

    offset = max(log_scores.values())
    weights = {label: math.exp(score - offset) for label, score in log_scores.items()}
    return weights.get("attack", 0.0) / max(sum(weights.values()), 1e-12)


def classify_prompt(text: str) -> dict[str, Any]:
    probability = predict_attack_probability(text)
    return {
        "label": "attack" if probability >= MODEL_THRESHOLD else "benign",
        "attack_probability": round(probability, 4),
        "threshold": MODEL_THRESHOLD,
        "available": MODEL_PATH.is_file(),
    }
