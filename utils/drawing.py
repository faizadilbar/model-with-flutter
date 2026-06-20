# utils/drawing.py

import cv2
import numpy as np
import config


def draw_risk_bar(frame: np.ndarray, risk: float) -> None:
    """Render a horizontal risk bar at the top of the frame."""
    h, w = frame.shape[:2]
    bar_w = int(w * risk / 100)

    if risk >= 70:
        color = config.RISK_HIGH_COLOR
        label = f"Risk: {risk:.0f}  HIGH"
    elif risk >= 40:
        color = config.RISK_MED_COLOR
        label = f"Risk: {risk:.0f}  MEDIUM"
    else:
        color = config.RISK_LOW_COLOR
        label = f"Risk: {risk:.0f}  LOW"

    cv2.rectangle(frame, (0, 0), (w, 18), (30, 30, 30), -1)
    cv2.rectangle(frame, (0, 0), (bar_w, 18), color, -1)
    cv2.putText(frame, label, (8, 13),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)


def draw_stats(frame: np.ndarray, stats: dict) -> None:
    """Render per-frame statistics in the bottom-left corner."""
    lines = [
        f"Faces: {stats.get('face_count', 0)}",
        f"EAR: {stats.get('ear', 0):.3f}",
        f"Blinks: {stats.get('blink_count', 0)}  ({stats.get('blink_rate', 0):.1f}/min)",
        f"Gaze yaw: {stats.get('gaze_yaw', 0):.3f}  pitch: {stats.get('gaze_pitch', 0):.3f}",
        f"Head yaw: {stats.get('head_yaw', 0):.1f}  pitch: {stats.get('head_pitch', 0):.1f}",
    ]
    y0 = frame.shape[0] - (len(lines) * 18) - 6
    for i, line in enumerate(lines):
        y = y0 + i * 18
        cv2.putText(frame, line, (8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)


def draw_flags(frame: np.ndarray, flags: list[str]) -> None:
    """Render active alert flags in the top-right corner."""
    for i, flag in enumerate(flags):
        cv2.putText(frame, flag, (frame.shape[1] - 200, 40 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, config.RISK_HIGH_COLOR, 1, cv2.LINE_AA)