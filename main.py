# main.py - Complete Proctoring System with Alarm and API Integration

import cv2
import time
import datetime
import os
import json
import sqlite3
from datetime import datetime
import numpy as np
import threading
import requests
import uuid

import config
from utils.face_mesh import (
    create_face_mesh,
    process_frame,
    LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
    LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
    HEAD_POSE_INDICES,
)
from utils.drawing import draw_risk_bar, draw_stats, draw_flags
from detectors.eye_aspect_ratio import compute_ear, average_ear
from detectors.gaze_estimator import estimate_gaze
from detectors.blink_counter import BlinkCounter
from detectors.head_pose import estimate_head_pose, build_camera_matrix
from risk.scorer import RiskScorer
from report import SessionReport

# Import alarm module
try:
    from alarm import ProctoringAlarm
    ALARM_AVAILABLE = True
except ImportError:
    ALARM_AVAILABLE = False
    print("[WARNING] Alarm module not found. Alarm disabled.")

# =========================================================
# API CONFIGURATION
# =========================================================

API_BASE_URL = "https://bgnuf22eight.com/cheating/proctoring-backend/public/api"

# =========================================================
# LOCAL DATABASE SETUP
# =========================================================

def init_local_database():
    """Create local database for backup"""
    conn = sqlite3.connect('proctoring_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            student_id TEXT,
            student_name TEXT,
            course_name TEXT,
            quiz_code TEXT,
            exam_date TEXT,
            start_time TEXT,
            end_time TEXT,
            avg_risk_score REAL,
            max_risk_score REAL,
            total_blinks INTEGER,
            gaze_away_count INTEGER,
            head_turn_count INTEGER,
            no_face_count INTEGER,
            multiple_face_count INTEGER,
            cheating_status TEXT,
            alarm_triggered INTEGER DEFAULT 0,
            alarm_count INTEGER DEFAULT 0,
            alarm_history TEXT,
            report_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            risk_score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            violation_type TEXT,
            severity TEXT,
            risk_score REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[INFO] Local database initialized")

def save_session_local(session_data):
    """Save session to local database"""
    try:
        conn = sqlite3.connect('proctoring_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO exam_sessions 
            (session_id, student_id, student_name, course_name, quiz_code, 
             exam_date, start_time, end_time, avg_risk_score, max_risk_score,
             total_blinks, gaze_away_count, head_turn_count, no_face_count,
             multiple_face_count, cheating_status, alarm_triggered, alarm_count, alarm_history, report_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_data.get('session_id'),
            session_data.get('student_id'),
            session_data.get('student_name'),
            session_data.get('course_name'),
            session_data.get('quiz_code'),
            session_data.get('exam_date'),
            session_data.get('start_time'),
            session_data.get('end_time'),
            session_data.get('avg_risk_score'),
            session_data.get('max_risk_score'),
            session_data.get('total_blinks'),
            session_data.get('gaze_away_count'),
            session_data.get('head_turn_count'),
            session_data.get('no_face_count'),
            session_data.get('multiple_face_count'),
            session_data.get('cheating_status'),
            session_data.get('alarm_triggered', 0),
            session_data.get('alarm_count', 0),
            session_data.get('alarm_history'),
            session_data.get('report_path')
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Local save failed: {e}")

def save_risk_local(session_id, risk_score):
    """Save risk score to local database"""
    try:
        conn = sqlite3.connect('proctoring_data.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO risk_history (session_id, risk_score) VALUES (?, ?)', 
                      (session_id, risk_score))
        conn.commit()
        conn.close()
    except:
        pass

def save_violation_local(session_id, violation_type, severity, risk_score):
    """Save violation to local database"""
    try:
        conn = sqlite3.connect('proctoring_data.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO violations (session_id, violation_type, severity, risk_score) 
                         VALUES (?, ?, ?, ?)''', (session_id, violation_type, severity, risk_score))
        conn.commit()
        conn.close()
    except:
        pass

# =========================================================
# API FUNCTIONS
# =========================================================

def get_teacher_token():
    """Get teacher authentication token"""
    print("\n" + "=" * 50)
    print("   TEACHER AUTHENTICATION")
    print("=" * 50)
    email = input("Enter Teacher Email: ").strip()
    password = input("Enter Teacher Password: ").strip()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/teacher/login",
            json={"email": email, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            print(f"[API] ✅ Teacher authenticated successfully")
            return token
        else:
            print(f"[API] ❌ Authentication failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[API] ❌ Authentication error: {e}")
        return None

def start_session_on_server(student_info):
    """Start exam session on server"""
    try:
        payload = {
            "student_id": student_info['student_id'],
            "student_name": student_info['student_name'],
            "quiz_code": student_info['quiz_code'],
            "course_name": student_info['course_name'],
            "exam_date": student_info['exam_date'],
            "start_time": student_info['start_time'],
        }
        
        print(f"[API] Sending to: {API_BASE_URL}/exam-sessions/start")
        print(f"[API] Payload: {payload}")
        
        response = requests.post(
            f"{API_BASE_URL}/exam-sessions/start",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"[API] Response Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            server_session_id = data.get('session_id') or data.get('data', {}).get('id')
            print(f"[API] ✅ Session started! ID: {server_session_id}")
            return server_session_id
        else:
            print(f"[API] ⚠️ Failed: {response.status_code}")
            print(f"[API] Response: {response.text}")
            return None
    except Exception as e:
        print(f"[API] ❌ Error: {e}")
        return None

def send_live_update_to_server(session_id, risk_score, gaze_away, head_turns, 
                                no_face, multi_face, blinks):
    """Send live update to server with alarm tracking"""
    if not session_id:
        return
    try:
        alarm_triggered = risk_score >= 70
        
        payload = {
            "avg_risk_score": round(risk_score, 1),
            "gaze_away_count": gaze_away,
            "head_turn_count": head_turns,
            "no_face_count": no_face,
            "multiple_face_count": multi_face,
            "total_blinks": blinks,
            "alarm_triggered": alarm_triggered,
        }
        
        response = requests.post(
            f"{API_BASE_URL}/exam-sessions/{session_id}/live-update",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=2
        )
        
        if response.status_code == 200:
            print(f"[API] 📊 Live update sent: Risk={risk_score:.1f}%")
    except Exception as e:
        pass

def report_alarm_to_server(session_id, violation_type, severity, risk_score):
    """Report alarm to server"""
    if not session_id:
        return
    try:
        payload = {
            "violation_type": violation_type,
            "severity": severity,
            "risk_score": round(risk_score, 1)
        }
        response = requests.post(
            f"{API_BASE_URL}/exam-sessions/{session_id}/report-violation",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=2
        )
        if response.status_code == 200:
            print(f"[API] ✅ Alarm reported: {violation_type}")
    except Exception as e:
        print(f"[API] Alarm report failed: {e}")

def end_session_on_server(session_id, end_time, avg_risk, max_risk, total_blinks, 
                          gaze_away, head_turns, no_face, multi_face, cheating_status, alarm_count):
    """End session on server"""
    if not session_id:
        return
    try:
        if len(end_time) == 5:  # HH:MM format
            end_time = end_time + ":00"  # Make HH:MM:SS
        
        payload = {
            "end_time": end_time,
            "avg_risk_score": round(avg_risk, 1),
            "max_risk_score": round(max_risk, 1),
            "total_blinks": total_blinks,
            "gaze_away_count": gaze_away,
            "head_turn_count": head_turns,
            "no_face_count": no_face,
            "multiple_face_count": multi_face,
            "cheating_status": cheating_status,
            "alarm_count": alarm_count,
            "alarm_triggered": 1 if alarm_count > 0 else 0,
        }
        response = requests.post(
            f"{API_BASE_URL}/exam-sessions/{session_id}/end",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            print(f"[API] ✅ Session ended on server")
            return True
        else:
            print(f"[API] ⚠️ End session failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[API] ❌ End session error: {e}")
        return False

def upload_report_to_server(session_id, report_path, quiz_code):
    """Upload report to server with enhanced error handling"""
    if not session_id:
        print("[UPLOAD] No session ID, skipping upload")
        return False
    
    if not os.path.exists(report_path):
        print(f"[UPLOAD] ERROR: Report file not found at {report_path}")
        return False
        
    try:
        file_size = os.path.getsize(report_path)
        print(f"[UPLOAD] File found: {report_path} ({file_size} bytes)")
        
        with open(report_path, 'rb') as f:
            files = {'report': (os.path.basename(report_path), f, 'text/plain')}
            data = {'quiz_code': quiz_code}
            
            url = f"{API_BASE_URL}/exam-sessions/{session_id}/report"
            print(f"[UPLOAD] POST to: {url}")
            
            response = requests.post(
                f"{API_BASE_URL}/exam-sessions/{session_id}/report",
                files=files,
                data=data,
                timeout=30
            )
            
            print(f"[UPLOAD] Response status: {response.status_code}")
            print(f"[UPLOAD] Response body: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"[UPLOAD] ✅ Report uploaded successfully!")
                if response_data.get('report_path'):
                    print(f"[UPLOAD] Report path saved to DB: {response_data.get('report_path')}")
                return True
            else:
                print(f"[UPLOAD] ❌ Upload failed with status {response.status_code}")
                return False
                
    except requests.exceptions.Timeout:
        print(f"[UPLOAD] ❌ Request timeout - server took too long to respond")
        return False
    except Exception as e:
        print(f"[UPLOAD] ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

# =========================================================
# GET STUDENT DATA MANUALLY
# =========================================================

def get_student_info_manual():
    """Get student information manually from user input"""
    print("\n" + "=" * 50)
    print("   STUDENT INFORMATION")
    print("=" * 50)
    print()
    
    student_info = {
        "student_id": input("Enter Student ID / Roll No: ").strip(),
        "student_name": input("Enter Student Name: ").strip(),
        "quiz_code": input("Enter Quiz Code: ").strip(),
        "course_name": input("Enter Course Name: ").strip(),
        "exam_date": datetime.now().strftime("%Y-%m-%d"),
        "start_time": datetime.now().strftime("%H:%M"),
    }
    
    print("\n" + "-" * 50)
    print("Please verify the information:")
    print(f"   Student ID   : {student_info['student_id']}")
    print(f"   Student Name : {student_info['student_name']}")
    print(f"   Course Name  : {student_info['course_name']}")
    print(f"   Quiz Code    : {student_info['quiz_code']}")
    print("-" * 50)
    
    confirm = input("\nConfirm? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n[INFO] Please re-enter information.")
        return get_student_info_manual()
    
    return student_info

# =========================================================
# HEAD POSE CALIBRATION
# =========================================================

def calibrate_head_pose(face_mesh, cam_matrix, cap):
    """Calibrate head position baseline (3 seconds)"""
    print("\n[INFO] Calibrating head pose...")
    print("[CAL] Please look straight at the camera for 3 seconds.")
    
    yaw_samples = []
    start_time = time.time()
    
    while time.time() - start_time < 3.0:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        
        results = process_frame(face_mesh, frame)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            head_yaw, _, _ = estimate_head_pose(
                landmarks, HEAD_POSE_INDICES, w, h, cam_matrix
            )
            yaw_samples.append(head_yaw)
        
        cv2.putText(
            frame,
            "CALIBRATING - Look Straight",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Time remaining: {int(3 - (time.time() - start_time))}s",
            (10, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )
        
        cv2.imshow(config.DISPLAY_WINDOW_NAME, frame)
        cv2.waitKey(1)
    
    baseline_yaw = float(np.mean(yaw_samples)) if yaw_samples else config.HEAD_BASELINE_YAW
    print(f"[CAL] Baseline yaw angle: {baseline_yaw:.1f} degrees")
    
    return baseline_yaw

# =========================================================
# MAIN EXAM FUNCTION
# =========================================================

def run_proctored_exam():
    """Main function - Runs proctored exam with alarm and API"""
    
    print("=" * 60)
    print("   PROCTORED EXAMINATION SYSTEM")
    print("=" * 60)
    
    # Initialize local database
    init_local_database()
    
    # Get teacher authentication
    api_token = get_teacher_token()
    
    # Initialize alarm system
    alarm = None
    if ALARM_AVAILABLE:
        alarm = ProctoringAlarm()
        print("[INFO] Alarm system initialized")
    
    print("=" * 60)
    
    # =========================================
    # STEP 1: GET STUDENT DATA
    # =========================================
    
    student_info = get_student_info_manual()
    
    local_session_id = f"{student_info['student_id']}_{int(time.time())}"
    
    print("\n" + "=" * 60)
    print("   STUDENT & QUIZ INFORMATION")
    print("=" * 60)
    print(f"   Student Name  : {student_info['student_name']}")
    print(f"   Roll No       : {student_info['student_id']}")
    print(f"   Course Name   : {student_info['course_name']}")
    print(f"   Quiz Code     : {student_info['quiz_code']}")
    print("=" * 60)
    
    # =========================================
    # STEP 2: START SESSION ON SERVER
    # =========================================
    
    print("\n[API] Starting session on server...")
    server_session_id = start_session_on_server(student_info)
    
    if server_session_id:
        print(f"[API] ✅ Session active on server! ID: {server_session_id}")
    else:
        print("[API] ⚠️ Offline mode")
    
    # =========================================
    # STEP 3: INITIALIZE CAMERA
    # =========================================
    
    print("\n[INFO] Initializing camera...")
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    
    if not cap.isOpened():
        print("[ERROR] Cannot access camera!")
        input("\nPress Enter to exit...")
        return
    
    print("[INFO] Camera initialized successfully!")
    
    # =========================================
    # STEP 4: INITIALIZE DETECTORS
    # =========================================
    
    print("\n[INFO] Initializing face detection models...")
    face_mesh = create_face_mesh()
    blink_counter = BlinkCounter()
    scorer = RiskScorer(ema_alpha=0.25)
    session_report = SessionReport()
    
    cam_matrix = build_camera_matrix(config.FRAME_WIDTH, config.FRAME_HEIGHT)
    
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(config.DISPLAY_WINDOW_NAME, config.FRAME_WIDTH, config.FRAME_HEIGHT)
    
    # =========================================
    # STEP 5: CALIBRATE HEAD POSE
    # =========================================
    
    baseline_yaw = calibrate_head_pose(face_mesh, cam_matrix, cap)
    scorer.set_baseline(baseline_yaw)
    
    # =========================================
    # STEP 6: START EXAM MONITORING
    # =========================================
    
    print("\n" + "=" * 60)
    print("   EXAM STARTED")
    print("=" * 60)
    print("[INFO] Proctoring is now active!")
    if ALARM_AVAILABLE:
        print("[INFO] ALARM will sound on cheating detection!")
    print("[INFO] Press 'Q' to stop the exam")
    print("[INFO] Keep looking at the camera")
    print("=" * 60 + "\n")
    
    # Statistics counters
    session_start = time.time()
    gaze_away_count = 0
    head_turn_count = 0
    no_face_count = 0
    multi_face_count = 0
    
    # Consecutive violation counters
    consecutive_gaze_away = 0
    consecutive_head_turn = 0
    consecutive_no_face = 0
    alarm_history_list = []
    
    running = True
    frame_count = 0
    last_alarm_time = 0
    last_api_update = time.time()
    ALARM_COOLDOWN = 3
    API_UPDATE_INTERVAL = 5
    
    # Save initial session locally
    session_data = {
        'session_id': local_session_id,
        'student_id': student_info['student_id'],
        'student_name': student_info['student_name'],
        'course_name': student_info['course_name'],
        'quiz_code': student_info['quiz_code'],
        'exam_date': student_info['exam_date'],
        'start_time': student_info['start_time'],
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
        'alarm_history': None,
        'report_path': None
    }
    save_session_local(session_data)
    
    # =========================================
    # STEP 7: MAIN PROCESSING LOOP
    # =========================================
    
    while running:
        ret, frame = cap.read()
        if not ret:
            print("[WARNING] Camera frame lost!")
            break
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        frame_count += 1
        
        # Process face mesh
        results = process_frame(face_mesh, frame)
        
        # Default values
        face_count = 0
        ear = 0.0
        gaze_yaw = 0.0
        gaze_pitch = 0.0
        looking_away = False
        head_yaw = 0.0
        head_pitch = 0.0
        
        # If face detected
        if results.multi_face_landmarks:
            face_count = len(results.multi_face_landmarks)
            landmarks = results.multi_face_landmarks[0].landmark
            
            consecutive_no_face = 0
            
            # Eye aspect ratio
            left_ear = compute_ear(landmarks, LEFT_EYE_INDICES, w, h)
            right_ear = compute_ear(landmarks, RIGHT_EYE_INDICES, w, h)
            ear = average_ear(left_ear, right_ear)
            blink_counter.update(ear)
            
            # Gaze estimation
            gaze_yaw, gaze_pitch, looking_away = estimate_gaze(
                landmarks,
                LEFT_EYE_INDICES, RIGHT_EYE_INDICES,
                LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER,
                w, h,
            )
            
            # Head pose estimation
            head_yaw, head_pitch, _ = estimate_head_pose(
                landmarks, HEAD_POSE_INDICES, w, h, cam_matrix
            )
        else:
            consecutive_no_face += 1
        
        # Detect violations
        head_turned = abs(head_yaw - baseline_yaw) > config.HEAD_YAW_THRESHOLD
        
        # Update consecutive counters
        if looking_away:
            consecutive_gaze_away += 1
        else:
            consecutive_gaze_away = 0
            
        if head_turned:
            consecutive_head_turn += 1
        else:
            consecutive_head_turn = 0
        
        # Update total counts
        if face_count == 0:
            no_face_count += 1
        if face_count > 1:
            multi_face_count += 1
        if looking_away:
            gaze_away_count += 1
        if head_turned:
            head_turn_count += 1
        
        # Calculate risk score
        raw_risk, smooth_risk, flags = scorer.compute(
            face_count=face_count,
            looking_away=looking_away,
            gaze_yaw=gaze_yaw,
            gaze_pitch=gaze_pitch,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            blink_anomalous=blink_counter.is_anomalous(),
            baseline_yaw=baseline_yaw,
        )
        
        # Save risk locally every 30 frames
        if frame_count % 30 == 0:
            save_risk_local(local_session_id, smooth_risk)
        
        # Send live update to server every 5 seconds
        current_time = time.time()
        if server_session_id and (current_time - last_api_update) > API_UPDATE_INTERVAL:
            send_live_update_to_server(server_session_id, smooth_risk, 
                                       gaze_away_count, head_turn_count,
                                       no_face_count, multi_face_count, 
                                       blink_counter.count)
            last_api_update = current_time
        
        # =========================================
        # ALARM TRIGGERING LOGIC
        # =========================================
        
        if ALARM_AVAILABLE and hasattr(config, 'ALARM_ENABLED') and config.ALARM_ENABLED:
            if (current_time - last_alarm_time) > ALARM_COOLDOWN:
                
                # Multiple faces detected (cheating)
                if face_count > 1:
                    last_alarm_time = current_time
                    violation_type = 'multiple_faces'
                    severity = 'high'
                    
                    print(f"\n🚨🚨🚨 CHEATING ALERT! Multiple faces detected! ({face_count} people) 🚨🚨🚨")
                    
                    # Play alarm
                    alarm.play_cheating_sound()
                    
                    # Save to local DB
                    save_violation_local(local_session_id, violation_type, severity, smooth_risk)
                    alarm_history_list.append({'type': violation_type, 'severity': severity, 'risk': smooth_risk, 'time': datetime.now().isoformat()})
                    
                    # Report to server
                    report_alarm_to_server(server_session_id, violation_type, severity, smooth_risk)
                    
                    cv2.putText(frame, "CHEATING ALERT! Multiple Faces!", (10, 150), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Continuous gaze away
                elif consecutive_gaze_away > 15:
                    last_alarm_time = current_time
                    severity = 'high' if consecutive_gaze_away > 25 else 'medium'
                    violation_type = 'gaze_away'
                    
                    print(f"\n🚨 ALERT! Gaze away for {consecutive_gaze_away} frames!")
                    
                    # Play alarm
                    alarm.trigger_alarm(severity, violation_type)
                    
                    # Save to local DB
                    save_violation_local(local_session_id, violation_type, severity, smooth_risk)
                    alarm_history_list.append({'type': violation_type, 'severity': severity, 'risk': smooth_risk, 'time': datetime.now().isoformat()})
                    
                    # Report to server
                    report_alarm_to_server(server_session_id, violation_type, severity, smooth_risk)
                    
                    cv2.putText(frame, f"WARNING: Gaze away!", (10, 180), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Continuous head turn
                elif consecutive_head_turn > 15:
                    last_alarm_time = current_time
                    severity = 'high' if consecutive_head_turn > 25 else 'medium'
                    violation_type = 'head_turn'
                    
                    print(f"\n🚨 ALERT! Head turn for {consecutive_head_turn} frames!")
                    
                    # Play alarm
                    alarm.trigger_alarm(severity, violation_type)
                    
                    # Save to local DB
                    save_violation_local(local_session_id, violation_type, severity, smooth_risk)
                    alarm_history_list.append({'type': violation_type, 'severity': severity, 'risk': smooth_risk, 'time': datetime.now().isoformat()})
                    
                    # Report to server
                    report_alarm_to_server(server_session_id, violation_type, severity, smooth_risk)
                    
                    cv2.putText(frame, f"WARNING: Head turn!", (10, 210), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # No face detected
                elif consecutive_no_face > 20:
                    last_alarm_time = current_time
                    severity = 'low'
                    violation_type = 'no_face'
                    
                    print(f"\n⚠️ WARNING! Face not detected for {consecutive_no_face} frames!")
                    
                    # Play warning
                    alarm.play_warning_sound()
                    
                    # Save to local DB
                    save_violation_local(local_session_id, violation_type, severity, smooth_risk)
                    alarm_history_list.append({'type': violation_type, 'severity': severity, 'risk': smooth_risk, 'time': datetime.now().isoformat()})
                    
                    # Report to server
                    report_alarm_to_server(server_session_id, violation_type, severity, smooth_risk)
                    
                    cv2.putText(frame, f"WARNING: Face not detected!", (10, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                
                # Brief warnings (no sound)
                elif consecutive_gaze_away >= 8:
                    print(f"\n⚠️ Warning: Looking away ({consecutive_gaze_away} frames)")
                
                elif consecutive_head_turn >= 8:
                    print(f"\n⚠️ Warning: Head turned ({consecutive_head_turn} frames)")
        
        # Record statistics
        stats = {
            "face_count": face_count,
            "ear": ear,
            "blink_count": blink_counter.count,
            "blink_rate": blink_counter.blink_rate(),
            "gaze_yaw": gaze_yaw,
            "gaze_pitch": gaze_pitch,
            "head_yaw": head_yaw,
            "head_pitch": head_pitch,
            "raw_risk": raw_risk,
            "smooth_risk": smooth_risk,
        }
        
        session_report.record(time.time() - session_start, stats, flags)
        
        # Draw UI elements
        draw_risk_bar(frame, smooth_risk)
        draw_stats(frame, stats)
        draw_flags(frame, flags)
        
        # Risk color indicator
        if smooth_risk >= 70:
            risk_color = (0, 0, 255)
            risk_text = "HIGH RISK!"
        elif smooth_risk >= 40:
            risk_color = (0, 165, 255)
            risk_text = "MEDIUM RISK"
        else:
            risk_color = (0, 255, 0)
            risk_text = "LOW RISK"
        
        # Display information on frame
        cv2.putText(
            frame,
            f"Student: {student_info['student_name']} | Risk: {smooth_risk:.1f}% [{risk_text}]",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            risk_color,
            1,
        )
        
        cv2.putText(
            frame,
            f"Course: {student_info['course_name']} | Quiz: {student_info['quiz_code']}",
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (200, 200, 200),
            1,
        )
        
        cv2.putText(
            frame,
            f"Gaze: {gaze_away_count} | Head: {head_turn_count} | Blinks: {blink_counter.count}",
            (10, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (200, 200, 200),
            1,
        )
        
        # Show alarm status
        if ALARM_AVAILABLE:
            cv2.putText(
                frame,
                f"Alarms: {len(alarm_history_list)}",
                (10, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 255) if len(alarm_history_list) > 0 else (0, 255, 0),
                1,
            )
        
        cv2.putText(
            frame,
            f"Press 'Q' to stop exam | {'Online' if server_session_id else 'Offline'}",
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 0) if server_session_id else (0, 165, 255),
            1,
        )
        
        # Show frame
        cv2.imshow(config.DISPLAY_WINDOW_NAME, frame)
        
        # Check for exit key
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            print("\n[INFO] Exam stopped by user.")
            running = False
        elif key == 27:
            print("\n[INFO] Exam stopped by user.")
            running = False
        
        # Check if window was closed
        if cv2.getWindowProperty(config.DISPLAY_WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            running = False
    
    # =========================================
    # STEP 8: CLEANUP AND REPORT
    # =========================================
    
    print("\n[INFO] Stopping camera and saving data...")
    
    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    
    # Calculate exam duration
    exam_duration = time.time() - session_start
    minutes = int(exam_duration // 60)
    seconds = int(exam_duration % 60)
    
    # Save local report
    os.makedirs("reports", exist_ok=True)
    report_filename = f"reports/report_{student_info['student_id']}_{student_info['quiz_code']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    session_report.save(report_filename, alarm_history=alarm_history_list)
    
    # Calculate summary
    avg_risk = round(session_report.avg_risk(), 1)
    max_risk = round(session_report.max_risk(), 1)
    
    # Determine cheating status
    if avg_risk >= 70:
        cheating_status = "cheating"
    elif avg_risk >= 40:
        cheating_status = "suspicious"
    else:
        cheating_status = "clean"
    
    # Summary for API
    end_time_str = datetime.now().strftime("%H:%M:%S")
    
    # Save to local database with alarm history
    session_data = {
        'session_id': local_session_id,
        'student_id': student_info['student_id'],
        'student_name': student_info['student_name'],
        'course_name': student_info['course_name'],
        'quiz_code': student_info['quiz_code'],
        'exam_date': student_info['exam_date'],
        'start_time': student_info['start_time'],
        'end_time': end_time_str,
        'avg_risk_score': avg_risk,
        'max_risk_score': max_risk,
        'total_blinks': blink_counter.count,
        'gaze_away_count': gaze_away_count,
        'head_turn_count': head_turn_count,
        'no_face_count': no_face_count,
        'multiple_face_count': multi_face_count,
        'cheating_status': cheating_status,
        'alarm_triggered': 1 if len(alarm_history_list) > 0 else 0,
        'alarm_count': len(alarm_history_list),
        'alarm_history': json.dumps(alarm_history_list),
        'report_path': report_filename
    }
    save_session_local(session_data)
    
    # =========================================
    # STEP 9: SEND TO SERVER
    # =========================================
    
    if server_session_id:
        print("\n[API] Sending final data to server...")
        
        end_session_on_server(server_session_id, end_time_str, avg_risk, max_risk,
                              blink_counter.count, gaze_away_count, head_turn_count,
                              no_face_count, multi_face_count, cheating_status,
                              len(alarm_history_list))
        upload_report_to_server(server_session_id, report_filename, student_info['quiz_code'])
        print("[API] ✅ Data synchronized with server!")
    else:
        print("\n[API] No server connection. Data saved locally.")
    
    # =========================================
    # STEP 10: DISPLAY SUMMARY
    # =========================================
    
    print("\n" + "=" * 60)
    print("   EXAM SUMMARY")
    print("=" * 60)
    print(f"   Student        : {student_info['student_name']}")
    print(f"   Roll No        : {student_info['student_id']}")
    print(f"   Course Name    : {student_info['course_name']}")
    print(f"   Quiz Code      : {student_info['quiz_code']}")
    print(f"   Duration       : {minutes}m {seconds}s")
    print(f"   Average Risk   : {avg_risk}%")
    print(f"   Maximum Risk   : {max_risk}%")
    print(f"   Total Blinks   : {blink_counter.count}")
    print(f"   Gaze Away      : {gaze_away_count} times")
    print(f"   Head Turns     : {head_turn_count} times")
    print(f"   No Face        : {no_face_count} frames")
    print(f"   Multiple Faces : {multi_face_count} frames")
    print(f"   Cheating Status: {cheating_status.upper()}")
    print(f"   Total Alarms   : {len(alarm_history_list)}")
    print("=" * 60)
    
    print(f"\n[INFO] Report saved: {report_filename}")
    
    if server_session_id:
        print(f"[INFO] Server session ID: {server_session_id}")
    
    print("\n[INFO] Proctoring session completed successfully!")
    input("\nPress Enter to exit...")


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    # Delete old database to ensure correct schema
    if os.path.exists('proctoring_data.db'):
        os.remove('proctoring_data.db')
    run_proctored_exam()