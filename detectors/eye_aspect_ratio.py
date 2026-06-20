# detectors/eye_aspect_ratio.py

import numpy as np
from scipy.spatial import distance as dist


def compute_ear(landmarks, eye_indices: list[int], img_w: int, img_h: int) -> float:
    """
    Compute Eye Aspect Ratio for one eye.

    EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

    Args:
        landmarks : MediaPipe NormalizedLandmarkList
        eye_indices: 6 landmark indices [p1..p6]
        img_w, img_h: frame pixel dimensions for denormalization
    Returns:
        float EAR value (0.0 = fully closed, ~0.3 = fully open)
    """
    pts = []
    for idx in eye_indices:
        lm = landmarks[idx]
        pts.append((lm.x * img_w, lm.y * img_h))

    p1, p2, p3, p4, p5, p6 = pts
    vertical_a = dist.euclidean(p2, p6)
    vertical_b = dist.euclidean(p3, p5)
    horizontal  = dist.euclidean(p1, p4)

    ear = (vertical_a + vertical_b) / (2.0 * horizontal) if horizontal > 0 else 0.0
    return round(ear, 4)


def average_ear(left_ear: float, right_ear: float) -> float:
    return (left_ear + right_ear) / 2.0