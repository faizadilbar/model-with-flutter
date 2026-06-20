# check_accuracy.py

import cv2
import time
import numpy as np
import os

import config
from utils.face_mesh import (
    create_face_mesh, process_frame,
    LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
    LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
    HEAD_POSE_INDICES,
)
from detectors.eye_aspect_ratio import compute_ear, average_ear
from detectors.gaze_estimator   import estimate_gaze
from detectors.blink_counter    import BlinkCounter
from detectors.head_pose        import estimate_head_pose, build_camera_matrix
from risk.scorer                import RiskScorer

TESTS = [
    {
        "id": 1, "name": "Face Detection — Look straight at camera",
        "instruction": "Look straight at the camera. Stay still.",
        "duration": 5, "check": "face_detected", "expected": True,
    },
    {
        "id": 2, "name": "No Face Detection — Cover camera with hand",
        "instruction": "Cover the camera COMPLETELY with your hand.",
        "duration": 5, "check": "face_detected", "expected": False,
    },
    {
        "id": 3, "name": "Blink Detection — Blink slowly 5 times",
        "instruction": "Blink your eyes SLOWLY 5 times. Open fully between each blink.",
        "duration": 10, "check": "blink_count", "expected": 3,
    },
    {
        "id": 4, "name": "Gaze Detection — Look LEFT",
        "instruction": "Move only your EYES to the LEFT. Hold for 5 seconds.",
        "duration": 5, "check": "looking_away", "expected": True,
    },
    {
        "id": 5, "name": "Gaze Detection — Look RIGHT",
        "instruction": "Move only your EYES to the RIGHT. Hold for 5 seconds.",
        "duration": 5, "check": "looking_away", "expected": True,
    },
    {
        "id": 6, "name": "Gaze Detection — Look straight",
        "instruction": "Look straight at the screen. Do NOT look away.",
        "duration": 5, "check": "looking_away", "expected": False,
    },
    {
        "id": 7, "name": "Head Pose — Turn head LEFT",
        "instruction": "Turn your whole HEAD to the LEFT. Hold for 5 seconds.",
        "duration": 5, "check": "head_turned", "expected": True,
    },
    {
        "id": 8, "name": "Head Pose — Turn head RIGHT",
        "instruction": "Turn your whole HEAD to the RIGHT. Hold for 5 seconds.",
        "duration": 5, "check": "head_turned", "expected": True,
    },
    {
        "id": 9, "name": "Head Pose — Look straight",
        "instruction": "Look straight ahead. Do NOT turn head.",
        "duration": 5, "check": "head_turned", "expected": False,
    },
    {
        "id": 10, "name": "Risk Score — Cheat (look away + turn head)",
        "instruction": "Look away AND turn head at the same time.",
        "duration": 5, "check": "high_risk", "expected": True,
    },
    {
        "id": 11, "name": "Risk Score — Normal (look straight)",
        "instruction": "Sit normally and look straight at the screen.",
        "duration": 5, "check": "high_risk", "expected": False,
    },
]


def calibrate_baseline(face_mesh, cam_matrix, cap) -> float:
    print("  [CAL] Look straight for 3 seconds...")
    yaw_vals = []
    start = time.time()
    while time.time() - start < 3.0:
        ret, frame = cap.read()
        if not ret:
            break
        frame   = cv2.flip(frame, 1)
        h, w    = frame.shape[:2]
        results = process_frame(face_mesh, frame)
        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            yaw, _, _ = estimate_head_pose(lm, HEAD_POSE_INDICES, w, h, cam_matrix)
            yaw_vals.append(yaw)
        cv2.putText(frame, "Calibrating — look straight...",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 200, 80), 2)
        cv2.imshow("Accuracy Test", frame)
        cv2.waitKey(1)
    baseline = float(np.mean(yaw_vals)) if yaw_vals else config.HEAD_BASELINE_YAW
    print(f"  [CAL] Baseline yaw = {baseline:.1f} degrees")
    return baseline


def run_test(test, face_mesh, cam_matrix, cap, baseline_yaw) -> dict:
    w = config.FRAME_WIDTH
    h = config.FRAME_HEIGHT

    frames_total      = 0
    face_detected_cnt = 0
    looking_away_cnt  = 0
    head_turned_cnt   = 0
    blink_detected    = 0
    risk_scores       = []
    blink_counter     = BlinkCounter()
    scorer            = RiskScorer(ema_alpha=0.25)
    scorer.set_baseline(baseline_yaw)

    start = time.time()

    while time.time() - start < test["duration"]:
        ret, frame = cap.read()
        if not ret:
            break

        frame   = cv2.flip(frame, 1)
        results = process_frame(face_mesh, frame)
        remain  = test["duration"] - (time.time() - start)

        face_count   = 0
        ear          = 0.0
        gaze_yaw     = 0.0
        gaze_pitch   = 0.0
        looking_away = False
        head_yaw     = 0.0
        head_pitch   = 0.0

        if results.multi_face_landmarks:
            face_count = len(results.multi_face_landmarks)
            lm         = results.multi_face_landmarks[0].landmark

            left_ear  = compute_ear(lm, LEFT_EYE_INDICES,  w, h)
            right_ear = compute_ear(lm, RIGHT_EYE_INDICES, w, h)
            ear       = average_ear(left_ear, right_ear)

            if blink_counter.update(ear):
                blink_detected += 1
                print(f"BLINK! EAR={ear:.3f} total={blink_detected}")
                
            gaze_yaw, gaze_pitch, looking_away = estimate_gaze(
                lm,
                LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
                LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
                w, h,
            )

            head_yaw, head_pitch, _ = estimate_head_pose(
                lm, HEAD_POSE_INDICES, w, h, cam_matrix
            )

        # Use calibrated baseline for head turn
        head_turned = abs(head_yaw - baseline_yaw) > config.HEAD_YAW_THRESHOLD

        _, smooth_risk, _ = scorer.compute(
            face_count=face_count,
            looking_away=looking_away,
            gaze_yaw=gaze_yaw,
            gaze_pitch=gaze_pitch,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            blink_anomalous=False,
            baseline_yaw=baseline_yaw,
        )

        frames_total      += 1
        risk_scores.append(smooth_risk)
        if face_count > 0:  face_detected_cnt += 1
        if looking_away:    looking_away_cnt  += 1
        if head_turned:     head_turned_cnt   += 1

        # Overlay
        cv2.rectangle(frame, (0, 0), (w, 90), (20, 20, 20), -1)
        cv2.putText(frame, f"TEST {test['id']}: {test['name']}",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 100), 1)
        cv2.putText(frame, test["instruction"],
                    (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 255, 200), 1)
        cv2.putText(frame, f"Time: {remain:.1f}s",
                    (10, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(frame,
                    f"Face:{face_count} EAR:{ear:.2f} "
                    f"GazeYaw:{gaze_yaw:.3f} Away:{looking_away} "
                    f"HeadYaw:{head_yaw:.1f} Turned:{head_turned} "
                    f"Risk:{smooth_risk:.0f}",
                    (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)

        cv2.imshow("Accuracy Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if frames_total == 0:
        return {"passed": False, "detail": "No frames captured"}

    face_pct  = face_detected_cnt / frames_total * 100
    gaze_pct  = looking_away_cnt  / frames_total * 100
    head_pct  = head_turned_cnt   / frames_total * 100
    avg_risk  = sum(risk_scores)  / len(risk_scores)

    check    = test["check"]
    expected = test["expected"]
    passed   = False
    detail   = ""

    if check == "face_detected":
        if expected:
            passed = face_pct >= 70
            detail = f"Face detected in {face_pct:.1f}% (need >=70%)"
        else:
            passed = face_pct <= 30
            detail = f"Face detected in {face_pct:.1f}% (need <=30%)"

    elif check == "blink_count":
        passed = blink_detected >= expected
        detail = f"Detected {blink_detected} blinks (need >={expected})"

    elif check == "looking_away":
        if expected:
            passed = gaze_pct >= 60
            detail = f"Looking away {gaze_pct:.1f}% (need >=60%)"
        else:
            passed = gaze_pct <= 20
            detail = f"Looking away {gaze_pct:.1f}% (need <=20%)"

    elif check == "head_turned":
        if expected:
            passed = head_pct >= 60
            detail = f"Head turned {head_pct:.1f}% (need >=60%)"
        else:
            passed = head_pct <= 20
            detail = f"Head turned {head_pct:.1f}% (need <=20%)"

    elif check == "high_risk":
        if expected:
            passed = avg_risk >= 30
            detail = f"Avg risk {avg_risk:.1f} (need >=30)"
        else:
            passed = avg_risk <= 25
            detail = f"Avg risk {avg_risk:.1f} (need <=25)"

    return {
        "passed": passed, "detail": detail,
        "face_pct": face_pct, "gaze_pct": gaze_pct,
        "head_pct": head_pct, "avg_risk": avg_risk,
        "blinks":  blink_detected,
    }


def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print("  EYE PROCTORING — MODEL ACCURACY TEST")
    print("=" * 60)
    print()
    print("  11 tests using your webcam.")
    print("  Follow instructions for each test.")
    print("  Press Q to skip any test.")
    print()
    input("  Press Enter to begin...")

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        print("  [ERROR] Cannot open camera.")
        return

    face_mesh  = create_face_mesh()
    cam_matrix = build_camera_matrix(config.FRAME_WIDTH, config.FRAME_HEIGHT)

    # Calibrate baseline first
    print()
    print("  CALIBRATION PHASE")
    print("  Look straight at camera for 3 seconds.")
    input("  Press Enter when ready...")
    cv2.namedWindow("Accuracy Test", cv2.WINDOW_NORMAL)
    baseline_yaw = calibrate_baseline(face_mesh, cam_matrix, cap)
    print(f"  Baseline = {baseline_yaw:.1f} degrees. Good.")
    print()

    results = []

    for test in TESTS:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"  TEST {test['id']}/{len(TESTS)}: {test['name']}")
        print()
        print(f"  ACTION : {test['instruction']}")
        print(f"  TIME   : {test['duration']} seconds")
        print()
        input("  Press Enter when ready...")
        print("  Starting in 2 seconds...")
        time.sleep(2)

        result = run_test(test, face_mesh, cam_matrix, cap, baseline_yaw)
        result["test_id"]   = test["id"]
        result["test_name"] = test["name"]
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n  Result: {status} — {result.get('detail', '')}")
        time.sleep(1)
        input("  Press Enter for next test...")

    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()

    # Final report
    os.system('cls' if os.name == 'nt' else 'clear')
    passed = sum(1 for r in results if r["passed"])
    total  = len(results)
    acc    = passed / total * 100

    print("=" * 60)
    print("  MODEL ACCURACY REPORT")
    print("=" * 60)
    print()

    for r in results:
        symbol = "PASS" if r["passed"] else "FAIL"
        print(f"  {symbol}  Test {r['test_id']:<3} {r['test_name']}")
        print(f"           {r.get('detail', '')}")
        print()

    print("-" * 60)
    print(f"  Tests passed : {passed} / {total}")
    print(f"  Accuracy     : {acc:.1f}%")
    print()

    if acc >= 80:
        verdict = "EXCELLENT"
    elif acc >= 60:
        verdict = "GOOD"
    elif acc >= 40:
        verdict = "FAIR"
    else:
        verdict = "POOR"

    print(f"  RESULT: {verdict}")
    print("=" * 60)

    # Save report
    os.makedirs("reports", exist_ok=True)
    with open("reports/accuracy_report.txt", "w", encoding="utf-8") as f:
        f.write("MODEL ACCURACY REPORT\n")
        f.write("=" * 60 + "\n\n")
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            f.write(f"Test {r['test_id']}: {r['test_name']}\n")
            f.write(f"  Status : {status}\n")
            f.write(f"  Detail : {r.get('detail', '')}\n\n")
        f.write(f"Overall Accuracy: {acc:.1f}%\n")
        f.write(f"Verdict: {verdict}\n")

    print("\n  Report saved to reports/accuracy_report.txt")
    print()
    input("  Press Enter to exit...")


if __name__ == "__main__":
    main()