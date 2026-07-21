# session_service.py
# Exposes the ExamSession class. Consumes DetectorOutput models and handles SQLite/Laravel API operations.

import os
import time
import json
from datetime import datetime
import config
from report import SessionReport
from models.exam_session import ExamSessionState
import services.database_service as db_service
import services.api_service as api_service

# Import metrics writer (only available when running via flask_server)
try:
    from flask_server import write_live_metrics as _write_live_metrics
except Exception:
    # Fallback: write directly to live_metrics.json so Flutter HTTP polling
    # still works even when running main.py without flask_server.
    import json as _json
    _METRICS_FILE = os.path.join(os.path.dirname(__file__), 'live_metrics.json')

    def _write_live_metrics(data: dict):
        try:
            with open(_METRICS_FILE, 'w') as _f:
                _json.dump(data, _f)
        except Exception:
            pass

# Global variable to hold the currently active session for UI resolver
active_session = None

class ExamSession:
    """Manages proctoring session lifecycles, SQLite databases, and Laravel API sync."""
    def __init__(self):
        self.state = ExamSessionState()
        self._last_api_update = 0.0
        self.frame_count = 0

    def start(self):
        """Initializes database tables, gets student metadata,
        starts Laravel server session, and initializes statistics metrics.
        """
        global active_session
        active_session = self
        
        # Initialize SQLite database
        db_service.init_local_database()
        
        # Retrieve student information from exam_session.json (written by Flask /start-exam)
        self.state.student_info = self._get_student_info_from_file()
        self.state.local_session_id = f"{self.state.student_info['student_id']}_{int(time.time())}"
        
        print("\n" + "=" * 60)
        print("   STUDENT & QUIZ INFORMATION")
        print("=" * 60)
        print(f"   Student Name  : {self.state.student_info['student_name']}")
        print(f"   Roll No       : {self.state.student_info['student_id']}")
        print(f"   Course Name   : {self.state.student_info['course_name']}")
        print(f"   Quiz Code     : {self.state.student_info['quiz_code']}")
        print("=" * 60)
        
        # Start session on Laravel server (best-effort, non-blocking)
        print("\n[API] Starting session on server...")
        self.state.server_session_id = api_service.start_session_on_server(self.state.student_info)

        if self.state.server_session_id:
            print(f"[API] ✅ Session active on server! ID: {self.state.server_session_id}")
        else:
            # Fallback: use local session ID so all data still goes to SQLite via API guards
            self.state.server_session_id = self.state.local_session_id
            print(f"[API] ⚠️ Offline mode — data saved locally. Local ID: {self.state.local_session_id}")

        # Set up SessionReport tracking
        self.state.session_report = SessionReport()
        self.state.session_start_time = time.time()
        self.frame_count = 0

        # Save initial session metadata to SQLite (includes server_session_id for API linking)
        session_data = {
            'session_id': self.state.local_session_id,
            'student_id': self.state.student_info['student_id'],
            'student_name': self.state.student_info['student_name'],
            'course_name': self.state.student_info['course_name'],
            'quiz_code': self.state.student_info['quiz_code'],
            'exam_date': self.state.student_info['exam_date'],
            'start_time': self.state.student_info['start_time'],
            'end_time': None,
            'avg_risk_score': 0,
            'max_risk_score': 0,
            'total_blinks': 0,
            'gaze_away_count': 0,
            'head_turn_count': 0,
            'no_face_count': 0,
            'multiple_face_count': 0,
            'cheating_status': 'clean',
            'alarm_triggered': 0,
            'alarm_count': 0,
            'total_count': 0,
            'alarm_history': None,
            'report_path': None,
            'server_session_id': self.state.server_session_id,
        }
        db_service.save_session_local(session_data)
        self._last_api_update = time.time()

    def record(self, result):
        """Processes frame result, increments infraction counters, logs risk periodically, and records to report."""
        self.frame_count += 1
        
        face_count = result["face_count"]
        looking_away = result["looking_away"]
        head_yaw = result["head_yaw"]
        baseline_yaw = result.get("baseline_yaw", config.HEAD_BASELINE_YAW)
        head_turned = abs(head_yaw - baseline_yaw) > config.HEAD_YAW_THRESHOLD
        
        # Increment total infraction counters
        if face_count == 0:
            self.state.no_face_count += 1
        if face_count > 1:
            self.state.multi_face_count += 1
        if looking_away:
            self.state.gaze_away_count += 1
        if head_turned:
            self.state.head_turn_count += 1
            
        # Log risk score to database on every frame.
        # In remote mode frames arrive every 2 seconds so we cannot skip any.
        db_service.save_risk_local(self.state.local_session_id, result["risk_score"])
            
        # Populate frame record statistics
        stats = {
            "face_count": face_count,
            "ear": result.get("ear", 0.0),
            "blink_count": result["blink_count"],
            "blink_rate": result.get("blink_rate", 0.0),
            "gaze_yaw": result["gaze_yaw"],
            "gaze_pitch": result["gaze_pitch"],
            "head_yaw": head_yaw,
            "head_pitch": result["head_pitch"],
            "raw_risk": result.get("raw_risk", 0.0),
            "smooth_risk": result["risk_score"],
        }
        
        # Get active flag strings list from result["flags"] dict
        active_flags = []
        flags_dict = result.get("flags", {})
        if flags_dict.get("no_face"):
            active_flags.append("face_absent")
        if flags_dict.get("multiple_faces"):
            active_flags.append("multi_face")
        if flags_dict.get("gaze_away"):
            active_flags.append("gaze_away")
        if flags_dict.get("head_turn"):
            active_flags.append("head_turned")
            
        self.state.session_report.record(
            time.time() - self.state.session_start_time,
            stats,
            active_flags
        )

    def record_violation(self, result):
        """Saves violation locally and reports immediately to proctoring Laravel server."""
        violation = result.get("new_violation")
        if violation is not None:
            violation_type = violation["violation_type"]
            severity = violation["severity"]
            risk_score = violation["risk_score"]
            timestamp = violation["timestamp"]
            alarm_number = violation["alarm_number"]
            
            # Save locally
            db_service.save_violation_local(self.state.local_session_id, violation_type, severity, risk_score)
            
            # Append record to session alarm history
            alarm_record = {
                'type': violation_type,
                'severity': severity,
                'risk': risk_score,
                'time': timestamp,
                'timestamp': timestamp,
                'alarm_number': alarm_number
            }
            self.state.alarm_history_list.append(alarm_record)
            
            # Immediately report to API for the live teacher dashboard
            if self.state.server_session_id:
                payload = {
                    "session_id": self.state.server_session_id,
                    "violation_type": violation_type,
                    "severity": severity,
                    "risk_score": round(risk_score, 1),
                    "timestamp": timestamp,
                    "alarm_number": alarm_number
                }
                api_service.report_alarm_to_server(payload)

    def send_live_update(self, result):
        """Sends throttled live updates to server and writes live_metrics.json for Flutter HTTP polling."""
        current_time = time.time()
        if (current_time - self._last_api_update) > config.LIVE_UPDATE_INTERVAL:
            metrics_payload = {
                'alarm_level': result.get('alarm_level', 'calibrating'),
                'risk_score': round(float(result.get('risk_score', 0.0)), 1),
                'max_risk': round(float(self.state.session_report.max_risk()), 1) if self.state.session_report else 0.0,
                'total_alarms': len(self.state.alarm_history_list),
                'blink_count': int(result.get('blink_count', 0)),
                'blink_rate': round(float(result.get('blink_rate', 0.0)), 1),
                'last_alarm_type': result.get('last_alarm_type', 'NONE'),
                'flags': result.get('flags', {
                    'gaze_away': False,
                    'head_turn': False,
                    'multiple_faces': False,
                    'no_face': False
                }),
                # Cumulative session counts — used by web frontend live dashboard
                'gaze_away_count':     self.state.gaze_away_count,
                'head_turn_count':     self.state.head_turn_count,
                'no_face_count':       self.state.no_face_count,
                'multiple_face_count': self.state.multi_face_count,
                'status': 'active',
                'face_center_x': float(result.get('face_center_x', 0.5)),
                'face_center_y': float(result.get('face_center_y', 0.5))
            }
            _write_live_metrics(metrics_payload)

            # Also send to Laravel server if connected
            if self.state.server_session_id:
                alarm_triggered = len(self.state.alarm_history_list) > 0
                total_count = len(self.state.alarm_history_list)
                max_risk = round(self.state.session_report.max_risk(), 1) if self.state.session_report else 0.0
                api_service.send_live_update_to_server(
                    self.state.server_session_id,
                    result['risk_score'],
                    self.state.gaze_away_count,
                    self.state.head_turn_count,
                    self.state.no_face_count,
                    self.state.multi_face_count,
                    result['blink_count'],
                    alarm_triggered,
                    total_count,
                    max_risk_score=max_risk
                )
            self._last_api_update = current_time

    def end(self):
        """Calculates session totals, saves local session report, syncs with Laravel backend,
        and outputs the diagnostic CLI summary.
        """
        global active_session
        active_session = None

        # Clean up live metrics file so Flutter knows session is done
        try:
            metrics_file = os.path.join(os.path.dirname(__file__), 'live_metrics.json')
            if os.path.exists(metrics_file):
                os.remove(metrics_file)
        except Exception:
            pass
        
        # Calculate duration
        exam_duration = time.time() - self.state.session_start_time
        minutes = int(exam_duration // 60)
        seconds = int(exam_duration % 60)
        
        blink_count = self.state.session_report.total_blinks()
        
        # Save local report
        os.makedirs("reports", exist_ok=True)
        report_filename = f"reports/report_{self.state.student_info['student_id']}_{self.state.student_info['quiz_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.state.session_report.save(report_filename, alarm_history=self.state.alarm_history_list)
        
        # Calculate summary metrics
        avg_risk = round(self.state.session_report.avg_risk(), 1)
        max_risk = round(self.state.session_report.max_risk(), 1)
        
        if avg_risk >= 70:
            cheating_status = "cheating"
        elif avg_risk >= 40:
            cheating_status = "suspicious"
        else:
            cheating_status = "clean"
            
        end_time_str = datetime.now().strftime("%H:%M:%S")
        
        # Save final session stats to local SQLite
        session_data = {
            'session_id': self.state.local_session_id,
            'student_id': self.state.student_info['student_id'],
            'student_name': self.state.student_info['student_name'],
            'course_name': self.state.student_info['course_name'],
            'quiz_code': self.state.student_info['quiz_code'],
            'exam_date': self.state.student_info['exam_date'],
            'start_time': self.state.student_info['start_time'],
            'end_time': end_time_str,
            'avg_risk_score': avg_risk,
            'max_risk_score': max_risk,
            'total_blinks': blink_count,
            'gaze_away_count': self.state.gaze_away_count,
            'head_turn_count': self.state.head_turn_count,
            'no_face_count': self.state.no_face_count,
            'multiple_face_count': self.state.multi_face_count,
            'cheating_status': cheating_status,
            'alarm_triggered': 1 if len(self.state.alarm_history_list) > 0 else 0,
            'alarm_count': len(self.state.alarm_history_list),
            'total_count': len(self.state.alarm_history_list),
            'alarm_history': json.dumps(self.state.alarm_history_list),
            'report_path': report_filename
        }
        db_service.save_session_local(session_data)
        
        # Synchronize session completion with Laravel server
        if self.state.server_session_id:
            print("\n[API] Sending final data to server...")
            api_service.end_session_on_server(
                self.state.server_session_id, end_time_str, avg_risk, max_risk,
                blink_count, self.state.gaze_away_count, self.state.head_turn_count,
                self.state.no_face_count, self.state.multi_face_count, cheating_status,
                len(self.state.alarm_history_list)
            )
            api_service.upload_report_to_server(self.state.server_session_id, report_filename, self.state.student_info['quiz_code'])
            print("[API] ✅ Data synchronized with server!")
        else:
            print("\n[API] No server connection. Data saved locally.")
            
        # Print CLI summary details
        print("\n" + "=" * 60)
        print("   EXAM SUMMARY")
        print("=" * 60)
        print(f"   Student        : {self.state.student_info['student_name']}")
        print(f"   Roll No        : {self.state.student_info['student_id']}")
        print(f"   Course Name    : {self.state.student_info['course_name']}")
        print(f"   Quiz Code      : {self.state.student_info['quiz_code']}")
        print(f"   Duration       : {minutes}m {seconds}s")
        print(f"   Average Risk   : {avg_risk}%")
        print(f"   Maximum Risk   : {max_risk}%")
        print(f"   Total Blinks   : {blink_count}")
        print(f"   Gaze Away      : {self.state.gaze_away_count} times")
        print(f"   Head Turns     : {self.state.head_turn_count} times")
        print(f"   No Face        : {self.state.no_face_count} frames")
        print(f"   Multiple Faces : {self.state.multi_face_count} frames")
        print(f"   Cheating Status: {cheating_status.upper()}")
        print(f"   Total Alarms   : {len(self.state.alarm_history_list)}")
        
        if self.state.alarm_history_list:
            print("\nAlarm Details")
            for i, alarm in enumerate(self.state.alarm_history_list, 1):
                print(f"\nAlarm #{i}")
                print(f"Type       : {alarm['type'].upper()}")
                print(f"Severity   : {alarm['severity'].upper()}")
                print(f"Risk Score : {alarm['risk']:.1f}")
                print(f"Time       : {alarm['time']}")
        print("=" * 60)
        
        print(f"\n[INFO] Report saved: {report_filename}")
        if self.state.server_session_id:
            print(f"[INFO] Server session ID: {self.state.server_session_id}")
            
        print("\n[INFO] Proctoring session completed successfully!")

    def _get_student_info_from_file(self):
        """Read student credentials from exam_session.json written by Flask /start-exam.
        Never blocks — safe to call from a background thread."""
        import os
        from datetime import datetime as _dt
        session_file = os.path.join(os.path.dirname(__file__), 'exam_session.json')
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            
            raw_start_time = data.get('start_time', '') or _dt.now().strftime('%H:%M')
            if isinstance(raw_start_time, str) and ":" in raw_start_time:
                parts = raw_start_time.split(":")
                if len(parts) >= 2:
                    raw_start_time = f"{parts[0].strip()}:{parts[1].strip()}"

            std_info = {
                'student_id':   data.get('student_id', '') or 'unknown',
                'student_name': data.get('student_name', '') or 'Unknown Student',
                'quiz_code':    data.get('quiz_code', '') or data.get('course_code', '') or 'N/A',
                'course_name':  data.get('course_name', '') or data.get('book_name', '') or 'N/A',
                'exam_date':    data.get('exam_date', '') or _dt.now().strftime('%Y-%m-%d'),
                'start_time':   raw_start_time,
            }
            print(f"[SESSION] ✅ Loaded student info from exam_session.json:")
            print(f"[SESSION]    Name: {std_info['student_name']}")
            print(f"[SESSION]    ID: {std_info['student_id']}")
            print(f"[SESSION]    Course: {std_info['course_name']}")
            print(f"[SESSION]    Quiz: {std_info['quiz_code']}")
            print(f"[SESSION]    Date: {std_info['exam_date']}")
            print(f"[SESSION]    Time: {std_info['start_time']}")
            return std_info
        except FileNotFoundError:
            print("[SESSION] ⚠️  exam_session.json not found — using defaults.")
        except Exception as e:
            print(f"[SESSION] ⚠️  Could not read exam_session.json: {e}")

        # Fallback defaults (won't block)
        from datetime import datetime
        return {
            'student_id':   'unknown',
            'student_name': 'Unknown Student',
            'quiz_code':    'N/A',
            'course_name':  'N/A',
            'exam_date':    datetime.now().strftime('%Y-%m-%d'),
            'start_time':   datetime.now().strftime('%H:%M'),
        }
