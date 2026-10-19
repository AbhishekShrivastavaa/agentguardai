"""Train/evaluate AgentGuard's local prompt risk classifier."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.security_engine.ml_classifier import fit_model, predict_attack_probability  # noqa: E402


DATA_PATH = ROOT / "app" / "security_engine" / "training_data.jsonl"
MODEL_PATH = ROOT / "app" / "security_engine" / "security_model.json"
THRESHOLD = 0.90


def load_data() -> list[dict[str, str]]:
    rows = [json.loads(line) for line in DATA_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    invalid = [row for row in rows if row.get("label") not in {"attack", "benign"} or not row.get("text")]
    if invalid:
        raise ValueError(f"Invalid or unlabeled training rows: {len(invalid)}")
    return rows


def split_stratified(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rng = random.Random(42)
    train: list[dict[str, str]] = []
    test: list[dict[str, str]] = []
    for label in ("attack", "benign"):
        group = [row for row in rows if row["label"] == label]
        rng.shuffle(group)
        test_count = max(1, round(len(group) * 0.2))
        test.extend(group[:test_count])
        train.extend(group[test_count:])
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def main() -> None:
    rows = load_data()
    train, test = split_stratified(rows)
    evaluation_model = fit_model(train)

    true_positive = false_positive = true_negative = false_negative = 0
    for row in test:
        probability = predict_attack_probability(row["text"], evaluation_model)
        predicted_attack = probability >= THRESHOLD
        actual_attack = row["label"] == "attack"
        if predicted_attack and actual_attack:
            true_positive += 1
        elif predicted_attack:
            false_positive += 1
        elif actual_attack:
            false_negative += 1
        else:
            true_negative += 1

    total = max(1, len(test))
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    accuracy = (true_positive + true_negative) / total

    final_model = fit_model(rows)
    MODEL_PATH.write_text(json.dumps(final_model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Algorithm: {final_model['algorithm']}")
    print(f"Dataset: {len(rows)} examples ({sum(r['label'] == 'attack' for r in rows)} attack, {sum(r['label'] == 'benign' for r in rows)} benign)")
    print(f"Holdout: {len(test)} examples; accuracy={accuracy:.3f}, precision={precision:.3f}, recall={recall:.3f}")
    print(f"Confusion: TP={true_positive} FP={false_positive} TN={true_negative} FN={false_negative}")
    print(f"Trained artifact: {MODEL_PATH}")


if __name__ == "__main__":
    main()
