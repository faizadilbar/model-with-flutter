# debug_test.py
# RUN: python debug_test.py

import cv2
import numpy as np
import config
from utils.face_mesh import (
    create_face_mesh, process_frame,
    LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
    LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
    HEAD_POSE_INDICES,
)
from detectors.gaze_estimator import estimate_gaze
from detectors.head_pose import estimate_head_pose, build_camera_matrix

face_mesh  = create_face_mesh()
cam_matrix = build_camera_matrix(config.FRAME_WIDTH, config.FRAME_HEIGHT)
cap        = cv2.VideoCapture(0)

print("Live debug — press Q to quit")
print("Turn head LEFT and RIGHT and look LEFT and RIGHT")
print()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame   = cv2.flip(frame, 1)
    h, w    = frame.shape[:2]
    results = process_frame(face_mesh, frame)

    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark
        from detectors.eye_aspect_ratio import compute_ear, average_ear
        from utils.face_mesh import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
        left_ear  = compute_ear(lm, LEFT_EYE_INDICES,  w, h)
        right_ear = compute_ear(lm, RIGHT_EYE_INDICES, w, h)
        ear = average_ear(left_ear, right_ear)
        print(f"EAR={ear:.4f} ", end="")
        # Raw iris positions
        left_iris  = lm[LEFT_IRIS_CENTER]
        right_iris = lm[RIGHT_IRIS_CENTER]
        left_corner  = lm[LEFT_EYE_INDICES[0]]
        right_corner = lm[RIGHT_EYE_INDICES[3]]

        gaze_yaw, gaze_pitch, looking_away = estimate_gaze(
            lm,
            LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
            LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
            w, h,
        )

        head_yaw, head_pitch, _ = estimate_head_pose(
            lm, HEAD_POSE_INDICES, w, h, cam_matrix
        )

        print(f"Iris L=({left_iris.x:.3f},{left_iris.y:.3f})  "
              f"R=({right_iris.x:.3f},{right_iris.y:.3f})  "
              f"GazeYaw={gaze_yaw:.4f}  "
              f"HeadYaw={head_yaw:.1f}  "
              f"Away={looking_away}")

        cv2.putText(frame,
            f"GazeYaw:{gaze_yaw:.3f} HeadYaw:{head_yaw:.1f} Away:{looking_away}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    else:
        print("No face detected")

    cv2.imshow("Debug", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
face_mesh.close()