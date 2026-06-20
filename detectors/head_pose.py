# detectors/head_pose.py

import cv2
import numpy as np

MODEL_POINTS = np.array([
    (0.0,    0.0,    0.0),
    (0.0,   -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0,  170.0, -135.0),
    (-150.0,-150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype=np.float64)

DIST_COEFFS = np.zeros((4, 1), dtype=np.float64)


def build_camera_matrix(img_w: int, img_h: int) -> np.ndarray:
    focal = img_w
    return np.array([
        [focal, 0,     img_w / 2],
        [0,     focal, img_h / 2],
        [0,     0,     1        ],
    ], dtype=np.float64)


def estimate_head_pose(
    landmarks,
    head_pose_indices: list,
    img_w: int,
    img_h: int,
    camera_matrix: np.ndarray,
) -> tuple[float, float, float]:

    try:
        image_points = np.array([
            (landmarks[i].x * img_w, landmarks[i].y * img_h)
            for i in head_pose_indices
        ], dtype=np.float64)

        success, rot_vec, _ = cv2.solvePnP(
            MODEL_POINTS,
            image_points,
            camera_matrix,
            DIST_COEFFS,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return 0.0, 0.0, 0.0

        rot_mat, _ = cv2.Rodrigues(rot_vec)
        sy = np.sqrt(rot_mat[0,0]**2 + rot_mat[1,0]**2)

        if sy > 1e-6:
            pitch = np.degrees(np.arctan2( rot_mat[2,1], rot_mat[2,2]))
            yaw   = np.degrees(np.arctan2(-rot_mat[2,0], sy))
            roll  = np.degrees(np.arctan2( rot_mat[1,0], rot_mat[0,0]))
        else:
            pitch = np.degrees(np.arctan2(-rot_mat[1,2], rot_mat[1,1]))
            yaw   = np.degrees(np.arctan2(-rot_mat[2,0], sy))
            roll  = 0.0

        return round(yaw, 2), round(pitch, 2), round(roll, 2)

    except Exception:
        return 0.0, 0.0, 0.0