# utils/face_mesh.py

import cv2
import numpy as np
import mediapipe as mp
import config

mp_face_mesh = mp.solutions.face_mesh


def create_face_mesh():
    return mp_face_mesh.FaceMesh(
        max_num_faces=config.MAX_NUM_FACES,
        refine_landmarks=config.REFINE_LANDMARKS,
        min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
        min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
    )


def process_frame(face_mesh, frame_bgr: np.ndarray):
    """Run landmark detection on a BGR frame."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return face_mesh.process(rgb)


# Landmark index constants
LEFT_EYE_INDICES  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

# Iris centres
LEFT_IRIS_CENTER  = 468
RIGHT_IRIS_CENTER = 473

# Head pose key points
HEAD_POSE_INDICES = [1, 152, 226, 446, 57, 287]