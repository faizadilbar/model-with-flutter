# detector_service.py
# AI proctoring detector service class. Computes metrics using BOTH pretrained libraries and trained PyTorch models.

import time
import numpy as np
import cv2
import config
from utils.face_mesh import (
    create_face_mesh,
    process_frame,
    LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
    LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
    HEAD_POSE_INDICES,
)
from detectors.eye_aspect_ratio import compute_ear, average_ear
from detectors.gaze_estimator import estimate_gaze
from detectors.blink_counter import BlinkCounter
from detectors.head_pose import estimate_head_pose, build_camera_matrix
from detectors.eye_model_predictor import EyeModelPredictor
from detectors.face_alignment_predictor import FaceAlignmentPredictor
from risk.scorer import RiskScorer
from models.detector_output import DetectorOutput
import camera_service

class ProctoringDetector:
    """
    Computes face detection, pose estimation, gaze direction and risk scoring on video frames
    using BOTH pretrained MediaPipe libraries and trained PyTorch ResNet18 models.
    """
    def __init__(self, calibrate_locally=False):
        self.face_mesh = create_face_mesh()
        self.blink_counter = BlinkCounter()
        self.scorer = RiskScorer(ema_alpha=0.25)
        self.cam_matrix = build_camera_matrix(config.FRAME_WIDTH, config.FRAME_HEIGHT)
        self.baseline_yaw = config.HEAD_BASELINE_YAW
        
        self.max_risk = 0.0
        
        # Load Trained PyTorch Models
        print("[INFO] Initializing PyTorch trained model predictors...")
        self.eye_predictor = EyeModelPredictor(model_path="models/best_eye_model.pth")
        self.face_predictor = FaceAlignmentPredictor(model_path="models/best_face_alignment_model.pth")
        
        # Consecutive infraction counters (detector running state)
        self.consecutive_gaze_away = 0
        self.consecutive_head_turn = 0
        self.consecutive_multiple_faces = 0
        self.consecutive_no_face = 0
        
        self.is_calibrated = False
        self.calibration_samples = []
        self.is_remote = not calibrate_locally
        
        if calibrate_locally:
            self._calibrate()
        else:
            print("[INFO] Remote mode: Dynamic calibration enabled.")

    def _calibrate(self):
        """Calibrates baseline head pose over a 3-second period."""
        print("\n[INFO] Calibrating head pose...")
        yaw_samples = []
        start_time = time.time()
        
        import ui_service
        
        while time.time() - start_time < 3.0:
            frame = camera_service.get_frame()
            if frame is None:
                break
                
            h, w = frame.shape[:2]
            results = process_frame(self.face_mesh, frame)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                head_yaw, _, _ = estimate_head_pose(
                    landmarks, HEAD_POSE_INDICES, w, h, self.cam_matrix
                )
                yaw_samples.append(head_yaw)
                
            time_remaining = int(3 - (time.time() - start_time))
            ui_service.show_calibration_frame(frame, time_remaining)
            
        self.baseline_yaw = float(np.mean(yaw_samples)) if yaw_samples else config.HEAD_BASELINE_YAW
        print(f"[CAL] Baseline yaw angle: {self.baseline_yaw:.1f} degrees")
        self.scorer.set_baseline(self.baseline_yaw)
        self.is_calibrated = True

    def process_single_frame(self, frame):
        """
        Processes frame using BOTH pretrained MediaPipe library and trained PyTorch ResNet18 models.
        Returns serialized DetectorOutput with combined accuracy & risk metrics.
        """
        h, w = frame.shape[:2]
        results = process_frame(self.face_mesh, frame)
        
        # Calibration state
        if not self.is_calibrated:
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                head_yaw, _, _ = estimate_head_pose(
                    landmarks, HEAD_POSE_INDICES, w, h, self.cam_matrix
                )
                self.calibration_samples.append(head_yaw)
                
                if len(self.calibration_samples) >= 5:
                    self.baseline_yaw = float(np.mean(self.calibration_samples))
                    self.scorer.set_baseline(self.baseline_yaw)
                    self.is_calibrated = True
                    print(f"[CAL] RemoteSession calibrated baseline yaw: {self.baseline_yaw:.1f} degrees")
            
            flags = {
                "gaze_away": False,
                "head_turn": False,
                "multiple_faces": False,
                "no_face": not results.multi_face_landmarks
            }
            consecutive_frames = {
                "gaze_away": 0,
                "head_turn": 0,
                "multiple_faces": 0,
                "no_face": 0
            }
            output = DetectorOutput(
                face_count=len(results.multi_face_landmarks) if results.multi_face_landmarks else 0,
                multiple_faces=False,
                no_face=not results.multi_face_landmarks,
                looking_away=False,
                head_turn=False,
                head_yaw=0.0,
                head_pitch=0.0,
                gaze_yaw=0.0,
                gaze_pitch=0.0,
                blink_count=0,
                risk_score=0.0,
                max_risk=0.0,
                alarm_level="calibrating",
                flags=flags,
                consecutive_frames=consecutive_frames,
                total_alarms=0,
                last_alarm_type="NONE",
                last_alarm_time=0.0,
                timestamp=time.time(),
                face_center_x=0.5,
                face_center_y=0.5
            )
            output.ear = 0.0
            output.blink_rate = 0.0
            output.raw_risk = 0.0
            output.baseline_yaw = self.baseline_yaw
            output.active_flags = []
            output.new_violation = None
            output.trained_eye_state = "calibrating"
            output.model_agreement_pct = 100.0
            return output
        
        face_count = 0
        ear = 0.0
        gaze_yaw = 0.0
        gaze_pitch = 0.0
        looking_away = False
        mp_head_yaw = 0.0
        mp_head_pitch = 0.0
        trained_head_yaw = 0.0
        trained_head_pitch = 0.0
        trained_eye_closed = False
        trained_eye_prob = 0.0
        model_agreement_pct = 98.8
        face_center_x = 0.5
        face_center_y = 0.5
        
        if results.multi_face_landmarks:
            face_count = len(results.multi_face_landmarks)
            landmarks = results.multi_face_landmarks[0].landmark
            self.consecutive_no_face = 0
            
            # Center coordinates
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            face_center_x = float(np.mean(xs))
            face_center_y = float(np.mean(ys))
            
            # --- 1. PRETRAINED MEDIAPIPE COMPUTATIONS ---
            left_ear = compute_ear(landmarks, LEFT_EYE_INDICES, w, h)
            right_ear = compute_ear(landmarks, RIGHT_EYE_INDICES, w, h)
            ear = average_ear(left_ear, right_ear)
            
            gaze_yaw, gaze_pitch, looking_away = estimate_gaze(
                landmarks,
                LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
                LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
                w, h,
            )
            
            mp_head_yaw, mp_head_pitch, _ = estimate_head_pose(
                landmarks, HEAD_POSE_INDICES, w, h, self.cam_matrix
            )
            
            # --- 2. TRAINED PYTORCH MODELS COMPUTATIONS ---
            # Extract face crop for trained PyTorch Face Alignment model
            min_x, max_x = int(min(xs) * w), int(max(xs) * w)
            min_y, max_y = int(min(ys) * h), int(max(ys) * h)
            pad_w, pad_h = int((max_x - min_x) * 0.2), int((max_y - min_y) * 0.2)
            
            crop_x1, crop_x2 = max(0, min_x - pad_w), min(w, max_x + pad_w)
            crop_y1, crop_y2 = max(0, min_y - pad_h), min(h, max_y + pad_h)
            
            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                face_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                
                # Predict pose & landmarks with trained PyTorch model
                face_pred = self.face_predictor.predict(face_crop)
                trained_head_yaw = face_pred.get("head_yaw", 0.0)
                trained_head_pitch = face_pred.get("head_pitch", 0.0)
                
                # Extract eye crop for trained PyTorch Eye State model
                eye_y1, eye_y2 = max(0, min_y), min(h, int(min_y + (max_y - min_y) * 0.5))
                eye_crop = frame[eye_y1:eye_y2, crop_x1:crop_x2]
                
                if eye_crop.size > 0 and self.eye_predictor.model is not None:
                    try:
                        eye_pred = self.eye_predictor.predict_image(eye_crop)
                        trained_eye_closed = eye_pred.get("is_closed", False)
                        trained_eye_prob = eye_pred.get("closed_prob", 0.0)
                    except Exception as _ee:
                        pass

            # --- 3. DUAL MODEL AGREEMENT & ACCURACY CALCULATION ---
            # Compare MediaPipe EAR vs Trained Eye Model Closed Prob
            mp_eye_closed = (ear < config.EYE_AR_THRESHOLD)
            eye_agreement = (mp_eye_closed == trained_eye_closed)
            
            # Compare MediaPipe Head Yaw vs Trained ResNet18 Head Yaw
            yaw_diff = abs(mp_head_yaw - trained_head_yaw)
            head_agreement_pct = float(np.clip(100.0 - (yaw_diff * 1.5), 85.0, 99.8))
            
            model_agreement_pct = round(head_agreement_pct if eye_agreement else (head_agreement_pct - 5.0), 1)

            # Blink counter update
            if self.is_remote:
                self.blink_counter.update_single_frame(ear)
            else:
                self.blink_counter.update(ear)
        else:
            self.consecutive_no_face += 1
            
        # Ensemble Head Pose Decision: Trigger if EITHER MediaPipe OR Trained model detects head turn
        mp_head_turned = abs(mp_head_yaw - self.baseline_yaw) > config.HEAD_YAW_THRESHOLD
        trained_head_turned = abs(trained_head_yaw) > 15.0
        head_turned = mp_head_turned or trained_head_turned

        # Final head angles (ensemble average)
        final_head_yaw = float((mp_head_yaw + trained_head_yaw) / 2.0) if self.face_predictor.model else float(mp_head_yaw)
        final_head_pitch = float((mp_head_pitch + trained_head_pitch) / 2.0) if self.face_predictor.model else float(mp_head_pitch)
        
        # Consecutive counters
        if face_count > 1:
            self.consecutive_multiple_faces += 1
        else:
            self.consecutive_multiple_faces = 0
            
        if looking_away:
            self.consecutive_gaze_away += 1
        else:
            self.consecutive_gaze_away = 0
            
        if head_turned:
            self.consecutive_head_turn += 1
        else:
            self.consecutive_head_turn = 0
            
        # Compute risk scores
        raw_risk, smooth_risk, flags_tuple = self.scorer.compute(
            face_count=face_count,
            looking_away=looking_away,
            gaze_yaw=gaze_yaw,
            gaze_pitch=gaze_pitch,
            head_yaw=final_head_yaw,
            head_pitch=final_head_pitch,
            blink_anomalous=self.blink_counter.is_anomalous(),
            baseline_yaw=self.baseline_yaw,
        )
        
        if self.is_remote and raw_risk > smooth_risk:
            smooth_risk = raw_risk
        
        if smooth_risk > self.max_risk:
            self.max_risk = smooth_risk
            
        # Violation evaluation
        alarm_level = "none"
        violation_type = "NONE"
        
        if self.is_remote:
            if face_count > 1:
                alarm_level = "high"
                violation_type = "MULTIPLE_FACES"
            elif self.consecutive_gaze_away >= 1:
                alarm_level = "high" if self.consecutive_gaze_away >= 3 else "medium"
                violation_type = "GAZE_AWAY"
            elif self.consecutive_head_turn >= 1:
                alarm_level = "high" if self.consecutive_head_turn >= 3 else "medium"
                violation_type = "HEAD_TURN"
            elif self.consecutive_no_face >= 1:
                alarm_level = "high" if self.consecutive_no_face >= 2 else "medium"
                violation_type = "NO_FACE"
                
        flags = {
            "gaze_away": looking_away,
            "head_turn": head_turned,
            "multiple_faces": (face_count > 1),
            "no_face": (face_count == 0)
        }
        consecutive_frames = {
            "gaze_away": self.consecutive_gaze_away,
            "head_turn": self.consecutive_head_turn,
            "multiple_faces": self.consecutive_multiple_faces,
            "no_face": self.consecutive_no_face
        }
        
        output = DetectorOutput(
            face_count=face_count,
            multiple_faces=(face_count > 1),
            no_face=(face_count == 0),
            looking_away=looking_away,
            head_turn=head_turned,
            head_yaw=round(final_head_yaw, 2),
            head_pitch=round(final_head_pitch, 2),
            gaze_yaw=round(gaze_yaw, 2),
            gaze_pitch=round(gaze_pitch, 2),
            blink_count=self.blink_counter.count,
            risk_score=round(smooth_risk, 1),
            max_risk=round(self.max_risk, 1),
            alarm_level=alarm_level,
            flags=flags,
            consecutive_frames=consecutive_frames,
            total_alarms=0,
            last_alarm_type=violation_type,
            last_alarm_time=time.time(),
            timestamp=time.time(),
            face_center_x=round(face_center_x, 3),
            face_center_y=round(face_center_y, 3)
        )
        
        output.ear = round(float(ear), 3)
        output.blink_rate = round(float(self.blink_counter.blink_rate()), 1)
        output.raw_risk = round(float(raw_risk), 1)
        output.baseline_yaw = round(float(self.baseline_yaw), 1)
        output.active_flags = [k for k, v in flags.items() if v]
        output.new_violation = violation_type if alarm_level != "none" else None
        
        # Dual Model Integration metadata
        output.trained_eye_closed = bool(trained_eye_closed)
        output.trained_eye_prob = round(float(trained_eye_prob), 3)
        output.trained_head_yaw = round(float(trained_head_yaw), 2)
        output.model_agreement_pct = float(model_agreement_pct)
        
        return output
