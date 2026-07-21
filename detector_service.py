# detector_service.py
# AI proctoring detector service class. Computes metrics without drawing overlays.

import time
import numpy as np
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
from risk.scorer import RiskScorer
from models.detector_output import DetectorOutput
import camera_service

class ProctoringDetector:
    """Computes face detection, pose estimation, gaze direction and risk scoring on video frames."""
    def __init__(self, calibrate_locally=False):
        self.face_mesh = create_face_mesh()
        self.blink_counter = BlinkCounter()
        self.scorer = RiskScorer(ema_alpha=0.25)
        self.cam_matrix = build_camera_matrix(config.FRAME_WIDTH, config.FRAME_HEIGHT)
        self.baseline_yaw = config.HEAD_BASELINE_YAW
        
        self.max_risk = 0.0
        
        # Consecutive infraction counters (detector running state)
        self.consecutive_gaze_away = 0
        self.consecutive_head_turn = 0
        self.consecutive_multiple_faces = 0
        self.consecutive_no_face = 0
        
        self.is_calibrated = True
        self.calibration_samples = []
        self.is_remote = not calibrate_locally
        
        # Perform initial baseline calibration if run locally
        if calibrate_locally:
            self._calibrate()
            self.is_calibrated = True
        else:
            print("[INFO] Remote mode: Dynamic calibration enabled.")

    def _calibrate(self):
        """Calibrates baseline head pose over a 3-second period."""
        print("\n[INFO] Calibrating head pose...")
        print("[CAL] Please look straight at the camera for 3 seconds.")
        
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
                
            # Delegate rendering the calibration screen window to the UI service
            time_remaining = int(3 - (time.time() - start_time))
            ui_service.show_calibration_frame(frame, time_remaining)
            
        self.baseline_yaw = float(np.mean(yaw_samples)) if yaw_samples else config.HEAD_BASELINE_YAW
        print(f"[CAL] Baseline yaw angle: {self.baseline_yaw:.1f} degrees")
        self.scorer.set_baseline(self.baseline_yaw)
        self.is_calibrated = True

    def process_single_frame(self, frame):
        """Processes frame to produce proctoring calculations and returns a serialized DetectorOutput."""
        h, w = frame.shape[:2]
        results = process_frame(self.face_mesh, frame)
        
        # Dynamically refine baseline_yaw over first 5 frames passively, without blocking predictions!
        if len(self.calibration_samples) < 5:
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                head_yaw, _, _ = estimate_head_pose(
                    landmarks, HEAD_POSE_INDICES, w, h, self.cam_matrix
                )
                self.calibration_samples.append(head_yaw)
                if len(self.calibration_samples) == 5:
                    self.baseline_yaw = float(np.mean(self.calibration_samples))
                    self.scorer.set_baseline(self.baseline_yaw)
                    print(f"[CAL] RemoteSession dynamically updated baseline yaw to: {self.baseline_yaw:.1f} degrees")
        
        face_count = 0
        ear = 0.0
        gaze_yaw = 0.0
        gaze_pitch = 0.0
        looking_away = False
        head_yaw = 0.0
        head_pitch = 0.0
        face_center_x = 0.5
        face_center_y = 0.5
        
        if results.multi_face_landmarks:
            face_count = len(results.multi_face_landmarks)
            landmarks = results.multi_face_landmarks[0].landmark
            self.consecutive_no_face = 0
            
            # Calculate face center coordinates
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            face_center_x = float(np.mean(xs))
            face_center_y = float(np.mean(ys))
            
            # Eye aspect ratio
            left_ear = compute_ear(landmarks, LEFT_EYE_INDICES, w, h)
            right_ear = compute_ear(landmarks, RIGHT_EYE_INDICES, w, h)
            ear = average_ear(left_ear, right_ear)
            
            # Gaze estimation
            gaze_yaw, gaze_pitch, looking_away = estimate_gaze(
                landmarks,
                LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
                LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
                w, h,
            )
            
            # Head pose estimation
            head_yaw, head_pitch, _ = estimate_head_pose(
                landmarks, HEAD_POSE_INDICES, w, h, self.cam_matrix
            )
            
            # Blink counting — remote mode uses single-frame detection
            # (frames arrive every ~2s so full open→close→open cycle is not captured)
            if self.is_remote:
                self.blink_counter.update_single_frame(ear)
            else:
                self.blink_counter.update(ear)
        else:
            self.consecutive_no_face += 1
            
        head_turned = abs(head_yaw - self.baseline_yaw) > config.HEAD_YAW_THRESHOLD
        
        # Update consecutive frame infraction counters
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
            
        # Calculate risk scores
        raw_risk, smooth_risk, flags_tuple = self.scorer.compute(
            face_count=face_count,
            looking_away=looking_away,
            gaze_yaw=gaze_yaw,
            gaze_pitch=gaze_pitch,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            blink_anomalous=self.blink_counter.is_anomalous(),
            baseline_yaw=self.baseline_yaw,
        )
        
        # In remote 2-second stream mode, ensure instant high-accuracy risk escalation on violations
        if self.is_remote and raw_risk > smooth_risk:
            smooth_risk = raw_risk
        
        # Track maximum risk
        if smooth_risk > self.max_risk:
            self.max_risk = smooth_risk
            
        # Determine potential alarm severity and violation type
        alarm_level = "none"
        violation_type = "NONE"
        
        if self.is_remote:
            # Remote stream mode (frames every 2 seconds) -> Instant frame-1 cheating detection
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
        else:
            # Local high-FPS webcam mode
            if face_count > 1:
                alarm_level = "high"
                violation_type = "MULTIPLE_FACES"
            elif self.consecutive_gaze_away > 15:
                alarm_level = "high" if self.consecutive_gaze_away > 25 else "medium"
                violation_type = "GAZE_AWAY"
            elif self.consecutive_head_turn > 15:
                alarm_level = "high" if self.consecutive_head_turn > 25 else "medium"
                violation_type = "HEAD_TURN"
            elif self.consecutive_no_face > 20:
                alarm_level = "low"
                violation_type = "NO_FACE"
            
        # Map boolean flags dict
        flags = {
            "gaze_away": looking_away,
            "head_turn": head_turned,
            "multiple_faces": face_count > 1,
            "no_face": face_count == 0
        }
        
        # Map consecutive frames counter dict
        consecutive_frames = {
            "gaze_away": self.consecutive_gaze_away,
            "head_turn": self.consecutive_head_turn,
            "multiple_faces": self.consecutive_multiple_faces,
            "no_face": self.consecutive_no_face
        }
        
        import alarm_service
        
        # Instantiate standardized DetectorOutput model
        output = DetectorOutput(
            face_count=face_count,
            multiple_faces=face_count > 1,
            no_face=face_count == 0,
            looking_away=looking_away,
            head_turn=head_turned,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            gaze_yaw=gaze_yaw,
            gaze_pitch=gaze_pitch,
            blink_count=self.blink_counter.count,
            risk_score=smooth_risk,
            max_risk=self.max_risk,
            alarm_level=alarm_level,
            flags=flags,
            consecutive_frames=consecutive_frames,
            total_alarms=alarm_service.total_alarms,
            last_alarm_type=violation_type,
            last_alarm_time=alarm_service._last_alarm_time,
            timestamp=time.time(),
            face_center_x=face_center_x,
            face_center_y=face_center_y
        )
        
        # Set dynamic properties for drawing/session compatibility
        output.ear = ear
        output.blink_rate = self.blink_counter.blink_rate()
        output.raw_risk = raw_risk
        output.baseline_yaw = self.baseline_yaw
        output.active_flags = flags_tuple
        output.new_violation = None
        
        return output

    def reset(self):
        """Resets all metrics and counters."""
        self.consecutive_gaze_away = 0
        self.consecutive_head_turn = 0
        self.consecutive_multiple_faces = 0
        self.consecutive_no_face = 0
        self.max_risk = 0.0
        self.blink_counter = BlinkCounter()
        self.scorer = RiskScorer(ema_alpha=0.25)
        self.scorer.set_baseline(self.baseline_yaw)

    def close(self):
        """Closes detector resources."""
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
