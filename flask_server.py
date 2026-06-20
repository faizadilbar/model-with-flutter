# flask_server.py - Complete Flask Server for Flutter Integration
# Run this alongside main.py
# Flutter calls this to start/stop exam

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import subprocess
import sys
import os
import json
import signal
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter

# Store current exam info
current_exam = {}
exam_process = None
exam_thread = None
is_exam_running = False

# Path to main.py
MAIN_PY_PATH = os.path.join(os.path.dirname(__file__), 'main.py')

@app.route('/start-exam', methods=['POST'])
def start_exam():
    global current_exam, is_exam_running, exam_thread
    
    try:
        data = request.json
        print(f"[FLASK] Received exam start request: {data}")
        
        # Store exam info that Python will use
        current_exam = {
            "student_id": data.get('roll_no', data.get('student_id', '')),
            "student_name": data.get('student_name', ''),
            "book_name": data.get('course_name', data.get('book_name', '')),
            "course_code": data.get('quiz_code', data.get('course_code', '')),
            "quiz_code": data.get('quiz_code', ''),
            "quiz_id": data.get('quiz_id', ''),
            "exam_date": data.get('exam_date', ''),
            "start_time": data.get('start_time', ''),
        }
        
        # Write to temp file so main.py can read it
        with open('exam_session.json', 'w') as f:
            json.dump(current_exam, f)
        
        # Remove stop signal if exists
        if os.path.exists('exam_stop.signal'):
            os.remove('exam_stop.signal')
        
        print(f"[FLASK] Exam started for {current_exam['student_name']}")
        
        # Start the proctoring system in a separate thread
        if not is_exam_running:
            exam_thread = threading.Thread(target=run_proctoring_system)
            exam_thread.daemon = True
            exam_thread.start()
            is_exam_running = True
        
        return jsonify({
            'status': True,
            'message': 'Exam monitoring started',
            'data': current_exam
        })
        
    except Exception as e:
        print(f"[FLASK] Error starting exam: {e}")
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/stop-exam', methods=['POST'])
def stop_exam():
    global is_exam_running
    
    try:
        # Write stop signal
        with open('exam_stop.signal', 'w') as f:
            f.write('stop')
        
        print("[FLASK] Exam stop signal received")
        is_exam_running = False
        
        return jsonify({
            'status': True,
            'message': 'Exam monitoring stopped'
        })
        
    except Exception as e:
        print(f"[FLASK] Error stopping exam: {e}")
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def status():
    try:
        exam_running = os.path.exists('exam_session.json')
        stop_signal = os.path.exists('exam_stop.signal')
        
        # Read current exam data if exists
        exam_data = {}
        if exam_running:
            try:
                with open('exam_session.json', 'r') as f:
                    exam_data = json.load(f)
            except:
                pass
        
        return jsonify({
            'status': True,
            'running': exam_running and not stop_signal,
            'exam': exam_data
        })
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': True,
        'message': 'Proctoring server is running'
    })

def run_proctoring_system():
    """Run the main proctoring system"""
    try:
        # Import and run main function
        import main
        main.run_proctored_exam()
    except Exception as e:
        print(f"[FLASK] Proctoring system error: {e}")
    finally:
        global is_exam_running
        is_exam_running = False

def run_flask_server():
    """Run Flask server"""
    print("=" * 50)
    print("  EYE PROCTORING — FLASK SERVER")
    print("=" * 50)
    print("  Listening on http://localhost:5000")
    print("  Flutter should call /start-exam to begin")
    print("  Endpoints:")
    print("    POST /start-exam - Start exam monitoring")
    print("    POST /stop-exam  - Stop exam monitoring")
    print("    GET  /status     - Get current status")
    print("    GET  /health     - Health check")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

if __name__ == '__main__':
    run_flask_server()