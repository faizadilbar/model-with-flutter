# app.py - Complete API for your model
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import cv2
import base64
import json
import os
from datetime import datetime

# Load your trained model here
# Example for different model types:

# If you have a pickle file (.pkl)
# import pickle
# with open('your_model.pkl', 'rb') as f:
#     model = pickle.load(f)

# If you have a TensorFlow model (.h5)
# from tensorflow import keras
# model = keras.models.load_model('your_model.h5')

# If you have a PyTorch model (.pt)
# import torch
# model = torch.load('your_model.pt')
# model.eval()

app = Flask(__name__)
CORS(app)  # Important - allows Flutter to call this API

# Store active sessions
active_sessions = {}

# ============================================
# HEALTH CHECK ENDPOINT
# ============================================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'running',
        'message': 'Your Model API is Live!',
        'time': datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model_loaded': True})

# ============================================
# START EXAM SESSION
# ============================================
@app.route('/start-session', methods=['POST'])
def start_session():
    try:
        data = request.json
        session_id = data.get('session_id')
        student_name = data.get('student_name')
        
        active_sessions[session_id] = {
            'student_name': student_name,
            'start_time': datetime.now().isoformat(),
            'risk_history': []
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Session started',
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ============================================
# PROCESS FRAME - MAIN MODEL ENDPOINT
# ============================================
@app.route('/process-frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        session_id = data.get('session_id')
        image_data = data.get('image')  # Base64 encoded image
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # ========================================
        # YOUR MODEL PROCESSING HERE
        # ========================================
        # This is where you use your trained model
        
        # Example processing (replace with your actual model):
        
        # 1. Face detection
        # 2. Eye tracking
        # 3. Head pose estimation
        # 4. Calculate risk score
        
        # For demonstration, let's calculate a sample risk
        # Replace this with your actual model prediction
        
        risk_score = 0
        gaze_status = "looking"
        head_status = "straight"
        is_cheating = False
        
        # Example: Your model returns these values
        # risk_score = model.predict(frame)
        # gaze_status = "away" if risk_score > 0.7 else "looking"
        
        # Temporary demo logic (replace with your model)
        import random
        risk_score = random.randint(0, 100)  # Replace with your model
        
        if risk_score > 70:
            gaze_status = "away"
            head_status = "turned"
            is_cheating = True
        elif risk_score > 40:
            gaze_status = "distracted"
            head_status = "slight_turn"
        else:
            gaze_status = "looking"
            head_status = "straight"
        
        # Store in session history
        if session_id in active_sessions:
            active_sessions[session_id]['risk_history'].append({
                'risk': risk_score,
                'time': datetime.now().isoformat()
            })
        
        # ========================================
        # SEND RESPONSE BACK TO FLUTTER
        # ========================================
        return jsonify({
            'status': 'success',
            'risk_score': risk_score,
            'gaze_status': gaze_status,
            'head_status': head_status,
            'is_cheating': is_cheating,
            'alert': risk_score > 70
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ============================================
# END SESSION
# ============================================
@app.route('/end-session', methods=['POST'])
def end_session():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if session_id in active_sessions:
            # Calculate average risk
            risks = [r['risk'] for r in active_sessions[session_id]['risk_history']]
            avg_risk = sum(risks) / len(risks) if risks else 0
            
            session_data = active_sessions[session_id]
            session_data['end_time'] = datetime.now().isoformat()
            session_data['avg_risk'] = avg_risk
            
            # Save to file (or database)
            with open('sessions_log.json', 'a') as f:
                json.dump(session_data, f)
                f.write('\n')
            
            # Remove from active sessions
            del active_sessions[session_id]
            
            return jsonify({
                'status': 'success',
                'avg_risk': avg_risk,
                'message': 'Session ended'
            })
        
        return jsonify({'status': 'error', 'message': 'Session not found'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ============================================
# GET SESSION REPORT
# ============================================
@app.route('/get-report/<session_id>', methods=['GET'])
def get_report(session_id):
    if session_id in active_sessions:
        return jsonify({
            'status': 'success',
            'data': active_sessions[session_id]
        })
    return jsonify({'status': 'error', 'message': 'Session not found'})

# ============================================
# RUN THE SERVER
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("YOUR MODEL API IS STARTING...")
    print("=" * 50)
    print("Server will run on: http://0.0.0.0:5000")
    print("Health check: http://localhost:5000/health")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)