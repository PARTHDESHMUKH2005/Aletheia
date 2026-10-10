"""Accuracy, confusion matrix, avg seconds per classification, and the share of
low-confidence items the confidence gate correctly sends to review (BUILD.md
section 9, Phase 2). Reads eval/labels.csv, calls the real characterizer on
each photo in eval/test_photos/.

labels.csv's `material` column is either an exact Item.material enum value, or
the special value "metal_scrap_family" for photos where the ground truth only
says "some kind of clean metal scrap" (TrashNet's "metal" category doesn't
distinguish aluminium/steel/copper/mixed) -- a prediction in that family counts
as correct without claiming a precision the label data doesn't support.

Usage: python eval/run_eval.py
"""
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import os  # noqa: E402

for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from app.storage.local import LocalStorage  # noqa: E402
from app.tools.characterize import characterize_waste  # noqa: E402

LABELS_PATH = Path(__file__).resolve().parent / "labels.csv"
LOW_CONFIDENCE_THRESHOLD = 0.7
METAL_FAMILY = {"aluminium_scrap", "steel_scrap", "copper_scrap", "mixed_metal"}


def _guess_format(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower()
    return "jpeg" if ext == "jpg" else ext


def _is_correct(true_label: str, predicted: str | None) -> bool:
    if predicted is None:
        return False
    if true_label == "metal_scrap_family":
        return predicted in METAL_FAMILY
    return predicted == true_label


def run_eval() -> dict:
    if not LABELS_PATH.exists() or LABELS_PATH.stat().st_size == 0:
        print("eval/labels.csv is empty. Nothing to evaluate.", file=sys.stderr)
        return {"rows": 0}

    with LABELS_PATH.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("eval/labels.csv has a header but no data rows. Nothing to evaluate.", file=sys.stderr)
        return {"rows": 0}

    storage = LocalStorage(db_path=ROOT / ".local_data" / "eval.db")

    confusion: dict[tuple[str, str], int] = {}
    durations_ms: list[int] = []
    correct_count = 0
    low_confidence_and_wrong = 0
    low_confidence_and_right = 0
    high_confidence_and_wrong = 0
    missing_photos: list[str] = []
    errors_count = 0
    results: list[dict] = []

    for row in rows:
        photo_path = ROOT / row["image_path"]
        if not photo_path.exists():
            missing_photos.append(row["image_path"])
            continue

        true_label = row["material"]
        photo = {"format": _guess_format(photo_path), "bytes": photo_path.read_bytes()}

        start = time.monotonic()
        try:
            characterization = characterize_waste([photo], storage=storage)
        except Exception as exc:  # one bad photo should not end the run; it counts as wrong
            print(f"{row['image_path']:<40} ERROR {type(exc).__name__}")
            results.append({"image_path": row["image_path"], "true_label": row["material"], "predicted": None,
                            "confidence": 0.0, "correct": False, "ms": 0, "error": type(exc).__name__})
            errors_count += 1
            continue
        elapsed_ms = int((time.monotonic() - start) * 1000)
        durations_ms.append(elapsed_ms)

        item = characterization.items[0] if characterization.items else None
        predicted = item.material if item else None
        confidence = item.confidence if item else 0.0
        correct = _is_correct(true_label, predicted)
        if correct:
            correct_count += 1

        confusion[(true_label, predicted or "none")] = confusion.get((true_label, predicted or "none"), 0) + 1

        if confidence < LOW_CONFIDENCE_THRESHOLD:
            if correct:
                low_confidence_and_right += 1
            else:
                low_confidence_and_wrong += 1
        elif not correct:
            high_confidence_and_wrong += 1

        results.append({
            "image_path": row["image_path"], "true_label": true_label, "predicted": predicted,
            "confidence": confidence, "correct": correct, "ms": elapsed_ms,
        })
        print(f"{row['image_path']:<40} true={true_label:<22} pred={predicted!s:<22} "
              f"conf={confidence:.2f} {'OK' if correct else 'WRONG'} ({elapsed_ms} ms)")

    n = len(results)
    accuracy = correct_count / n if n else 0.0
    avg_ms = sum(durations_ms) / len(durations_ms) if durations_ms else 0.0
    errors = high_confidence_and_wrong + low_confidence_and_wrong
    review_gate_recall = (low_confidence_and_wrong / errors) if errors else None

    # Calibration: how often each confidence band was actually right. This is what
    # supports (or undercuts) showing the confidence number to users.
    bands = {"low (<0.70)": (0, 0.7), "medium (0.70-0.85)": (0.7, 0.85), "high (>=0.85)": (0.85, 1.01)}
    calibration = {}
    for name, (lo, hi) in bands.items():
        in_band = [r for r in results if "error" not in r and lo <= r["confidence"] < hi]
        calibration[name] = {
            "n": len(in_band),
            "accuracy": round(sum(r["correct"] for r in in_band) / len(in_band), 3) if in_band else None,
            "mean_confidence": round(sum(r["confidence"] for r in in_band) / len(in_band), 3) if in_band else None,
        }

    summary = {
        "calibration_by_confidence_band": calibration,
        "rows_evaluated": n,
        "rows_errored": errors_count,
        "rows_missing_photo": len(missing_photos),
        "missing_photos": missing_photos,
        "accuracy": round(accuracy, 3),
        "avg_seconds_per_classification": round(avg_ms / 1000, 2),
        "confusion_matrix": {f"{t} -> {p}": c for (t, p), c in sorted(confusion.items())},
        "low_confidence_and_wrong": low_confidence_and_wrong,
        "low_confidence_and_right": low_confidence_and_right,
        "high_confidence_and_wrong_missed_by_review_gate": high_confidence_and_wrong,
        "review_gate_recall_for_errors": round(review_gate_recall, 3) if review_gate_recall is not None else None,
    }

    print("\n--- summary ---")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run_eval()
