# detectors/gaze_estimator.py

import numpy as np
import config


def estimate_gaze(
    landmarks,
    left_eye_indices:  list,
    right_eye_indices: list,
    left_iris_idx:     int,
    right_iris_idx:    int,
    img_w: int,
    img_h: int,
) -> tuple[float, float, bool]:

    try:
        def pt(idx):
            lm = landmarks[idx]
            return np.array([lm.x * img_w, lm.y * img_h])

        # Left eye corners and iris
        ll = pt(left_eye_indices[0])
        lr = pt(left_eye_indices[3])
        li = pt(left_iris_idx)

        # Right eye corners and iris
        rl = pt(right_eye_indices[0])
        rr = pt(right_eye_indices[3])
        ri = pt(right_iris_idx)

        def offset(iris, c_l, c_r):
            width = np.linalg.norm(c_r - c_l)
            if width < 1.0:
                return 0.0, 0.0
            center = (c_l + c_r) / 2.0
            diff   = iris - center
            return diff[0] / width, diff[1] / width

        lx, ly = offset(li, ll, lr)
        rx, ry = offset(ri, rl, rr)

        gaze_yaw   = round((lx + rx) / 2.0, 4)
        gaze_pitch = round((ly + ry) / 2.0, 4)

        looking_away = (
            abs(gaze_yaw)   > config.GAZE_YAW_THRESHOLD or
            abs(gaze_pitch) > config.GAZE_PITCH_THRESHOLD
        )

        return gaze_yaw, gaze_pitch, looking_away

    except Exception:
        return 0.0, 0.0, False