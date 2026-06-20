# validate_dataset.py
#
# Tests eye state detection accuracy against MRL Eye Dataset
# RUN: python validate_dataset.py

import cv2
import os
import numpy as np
from pathlib import Path

import config
from utils.face_mesh import (
    create_face_mesh,
    process_frame,
    LEFT_EYE_INDICES,
    RIGHT_EYE_INDICES,
)
from detectors.eye_aspect_ratio import compute_ear, average_ear
from detectors.blink_counter import BlinkCounter

# ─────────────────────────────────────────────
# Dataset paths
# ─────────────────────────────────────────────
TRAIN_PATH  = "data/mrl_eye/data/train"
TEST_PATH   = "data/mrl_eye/data/test"
AWAKE_FOLDER  = "awake"     # open eyes
SLEEPY_FOLDER = "sleepy"    # closed/drowsy eyes
MAX_IMAGES  = 300           # test 300 images per class


def get_ear_from_image(face_mesh, img_bgr: np.ndarray) -> float:
    """Run MediaPipe on image and return EAR value."""
    h, w = img_bgr.shape[:2]
    results = process_frame(face_mesh, img_bgr)

    if not results.multi_face_landmarks:
        return -1.0   # face not detected

    lm = results.multi_face_landmarks[0].landmark

    left_ear  = compute_ear(lm, LEFT_EYE_INDICES,  w, h)
    right_ear = compute_ear(lm, RIGHT_EYE_INDICES, w, h)
    return average_ear(left_ear, right_ear)


def test_folder(face_mesh, folder_path: str,
                label: str, expected_open: bool,
                max_images: int) -> dict:
    """Test all images in a folder and return accuracy."""

    image_files = []
    for ext in ["*.jpg", "*.png", "*.jpeg", "*.bmp"]:
        image_files += list(Path(folder_path).glob(ext))
        image_files += list(Path(folder_path).rglob(ext))

    image_files = list(set(image_files))[:max_images]

    if not image_files:
        print(f"  [WARNING] No images found in {folder_path}")
        return {"total": 0, "correct": 0, "accuracy": 0.0}

    print(f"  Testing {len(image_files)} {label} images...")

    correct       = 0
    total         = 0
    no_face       = 0
    ear_values    = []

    for i, img_path in enumerate(image_files):
        if i % 50 == 0:
            print(f"    Progress: {i}/{len(image_files)}")

        img = cv2.imread(str(img_path))
        if img is None:
            continue

        # Resize to standard size
        img = cv2.resize(img, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

        ear = get_ear_from_image(face_mesh, img)

        if ear < 0:
            no_face += 1
            total   += 1
            continue

        ear_values.append(ear)
        total += 1

        # Predict open or closed using EAR threshold
        predicted_open = ear >= config.EAR_BLINK_THRESHOLD

        # Check if prediction matches expected
        if predicted_open == expected_open:
            correct += 1

    accuracy  = (correct / total * 100) if total > 0 else 0
    avg_ear   = np.mean(ear_values) if ear_values else 0

    return {
        "total"    : total,
        "correct"  : correct,
        "accuracy" : accuracy,
        "no_face"  : no_face,
        "avg_ear"  : avg_ear,
    }


def main():
    print("=" * 60)
    print("  EYE STATE DETECTION ACCURACY")
    print("  Dataset: MRL Eye Dataset (Kaggle)")
    print("=" * 60)
    print()

    # Check dataset exists
    awake_path  = os.path.join(TRAIN_PATH, AWAKE_FOLDER)
    sleepy_path = os.path.join(TRAIN_PATH, SLEEPY_FOLDER)

    if not os.path.exists(awake_path):
        print(f"  [ERROR] Awake folder not found: {awake_path}")
        return

    if not os.path.exists(sleepy_path):
        print(f"  [ERROR] Sleepy folder not found: {sleepy_path}")
        return

    print(f"  Awake folder  : {awake_path}")
    print(f"  Sleepy folder : {sleepy_path}")
    print(f"  EAR threshold : {config.EAR_BLINK_THRESHOLD}")
    print()
    print("  [INFO] Loading MediaPipe face mesh...")
    face_mesh = create_face_mesh()
    print("  [INFO] Model loaded. Starting validation...")
    print()

    # ── Test awake images (eyes open) ─────────
    print("  [1/2] Testing AWAKE images (eyes should be open)...")
    awake_result = test_folder(
        face_mesh, awake_path,
        label="awake",
        expected_open=True,
        max_images=MAX_IMAGES,
    )

    print()

    # ── Test sleepy images (eyes closed) ──────
    print("  [2/2] Testing SLEEPY images (eyes should be closed)...")
    sleepy_result = test_folder(
        face_mesh, sleepy_path,
        label="sleepy",
        expected_open=False,
        max_images=MAX_IMAGES,
    )

    face_mesh.close()

    # ── Calculate overall accuracy ─────────────
    total_correct = awake_result["correct"]  + sleepy_result["correct"]
    total_images  = awake_result["total"]    + sleepy_result["total"]
    overall_acc   = (total_correct / total_images * 100) if total_images > 0 else 0

    # ── Print results ──────────────────────────
    print()
    print("=" * 60)
    print("  VALIDATION RESULTS")
    print("=" * 60)
    print()
    print(f"  Awake  (open eyes) :")
    print(f"    Images tested  : {awake_result['total']}")
    print(f"    Correct        : {awake_result['correct']}")
    print(f"    Accuracy       : {awake_result['accuracy']:.1f}%")
    print(f"    Avg EAR value  : {awake_result['avg_ear']:.4f}")
    print(f"    No face found  : {awake_result['no_face']}")
    print()
    print(f"  Sleepy (closed eyes) :")
    print(f"    Images tested  : {sleepy_result['total']}")
    print(f"    Correct        : {sleepy_result['correct']}")
    print(f"    Accuracy       : {sleepy_result['accuracy']:.1f}%")
    print(f"    Avg EAR value  : {sleepy_result['avg_ear']:.4f}")
    print(f"    No face found  : {sleepy_result['no_face']}")
    print()
    print("─" * 60)
    print(f"  Total images tested : {total_images}")
    print(f"  Total correct       : {total_correct}")
    print(f"  Overall accuracy    : {overall_acc:.1f}%")
    print()

    if overall_acc >= 80:
        verdict = "EXCELLENT — Model is working very well"
    elif overall_acc >= 65:
        verdict = "GOOD — Acceptable for FYP"
    elif overall_acc >= 50:
        verdict = "FAIR — Needs threshold adjustment"
    else:
        verdict = "POOR — Check lighting or threshold"

    print(f"  Verdict : {verdict}")
    print("=" * 60)

    # ── Save report ────────────────────────────
    os.makedirs("reports", exist_ok=True)
    report_path = "reports/dataset_validation_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("DATASET VALIDATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write("Dataset       : MRL Eye Dataset\n")
        f.write("Source        : kaggle.com/datasets/akashshingha850/mrl-eye-dataset\n")
        f.write("License       : MIT\n\n")
        f.write(f"EAR Threshold : {config.EAR_BLINK_THRESHOLD}\n\n")
        f.write("RESULTS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Awake (open eyes)\n")
        f.write(f"  Images tested : {awake_result['total']}\n")
        f.write(f"  Correct       : {awake_result['correct']}\n")
        f.write(f"  Accuracy      : {awake_result['accuracy']:.1f}%\n")
        f.write(f"  Avg EAR       : {awake_result['avg_ear']:.4f}\n\n")
        f.write(f"Sleepy (closed eyes)\n")
        f.write(f"  Images tested : {sleepy_result['total']}\n")
        f.write(f"  Correct       : {sleepy_result['correct']}\n")
        f.write(f"  Accuracy      : {sleepy_result['accuracy']:.1f}%\n")
        f.write(f"  Avg EAR       : {sleepy_result['avg_ear']:.4f}\n\n")
        f.write(f"Overall Accuracy : {overall_acc:.1f}%\n")
        f.write(f"Verdict          : {verdict}\n")

    print(f"\n  Report saved to : {report_path}")
    print()
    print("  Show this report to your supervisor as proof")
    print("  of dataset validation and model accuracy.")
    print()


if __name__ == "__main__":
    main()