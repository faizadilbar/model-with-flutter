# config.py - Complete configuration for Proctoring System with Alarm

# =========================================================
# CAMERA SETTINGS
# =========================================================
CAMERA_INDEX = 0                    # 0 = built-in camera, 1 = external USB
FRAME_WIDTH = 640                   # Video capture width
FRAME_HEIGHT = 480                  # Video capture height
FPS_TARGET = 30                     # Target frames per second

# =========================================================
# FACE MESH SETTINGS (MediaPipe)
# =========================================================
MAX_NUM_FACES = 3                   # Maximum faces to detect
MIN_DETECTION_CONFIDENCE = 0.7      # Minimum confidence for face detection
MIN_TRACKING_CONFIDENCE = 0.6       # Minimum confidence for face tracking
REFINE_LANDMARKS = True             # Enable refined landmark detection

# =========================================================
# EYE ASPECT RATIO (Blink Detection)
# =========================================================
EAR_BLINK_THRESHOLD = 0.24          # EAR value below this = eye closed
EAR_CONSEC_FRAMES = 1               # Consecutive frames to confirm blink
NORMAL_BLINK_RATE_MIN = 10          # Minimum normal blinks per minute
NORMAL_BLINK_RATE_MAX = 30          # Maximum normal blinks per minute

# =========================================================
# GAZE ESTIMATION SETTINGS
# =========================================================
GAZE_YAW_THRESHOLD = 0.10           # Horizontal gaze threshold (radians)
GAZE_PITCH_THRESHOLD = 0.10         # Vertical gaze threshold (radians)

# =========================================================
# HEAD POSE ESTIMATION SETTINGS
# =========================================================
HEAD_YAW_THRESHOLD = 10             # Head turn threshold (degrees)
HEAD_PITCH_THRESHOLD = 12           # Head up/down threshold (degrees)
HEAD_BASELINE_YAW = -4.0            # Default head yaw baseline

# =========================================================
# RISK SCORE WEIGHTS (Sum should be 1.0)
# =========================================================
WEIGHT_FACE_ABSENT = 0.20           # No face detected
WEIGHT_MULTI_FACE = 0.15            # Multiple faces detected
WEIGHT_GAZE_AWAY = 0.35             # Looking away from screen
WEIGHT_HEAD_TURN = 0.30             # Head turned away
WEIGHT_BLINK_ANOMALY = 0.00         # Abnormal blinking (disabled)

# =========================================================
# ALARM SYSTEM SETTINGS
# =========================================================
ALARM_ENABLED = True
ALARM_COOLDOWN = 5          # Increase from 3 to 5 seconds
GAZE_WARNING_FRAMES = 10    # Increase from 5 to 10
GAZE_ALERT_FRAMES = 20      # Increase from 10 to 20
HEAD_TURN_WARNING_FRAMES = 10
HEAD_TURN_ALERT_FRAMES = 20


# Risk score threshold for continuous alarm
CONTINUOUS_ALARM_RISK = 70          # Risk score above this = continuous alarm

# =========================================================
# CONSECUTIVE VIOLATION THRESHOLDS (frames at 30 FPS)
# =========================================================
# Gaze away thresholds
GAZE_WARNING_FRAMES = 5             # 0.16 seconds - Brief glance away
GAZE_ALERT_FRAMES = 10              # 0.33 seconds - Looking away
GAZE_SEVERE_FRAMES = 20             # 0.66 seconds - Persistent looking away

# Head turn thresholds
HEAD_TURN_WARNING_FRAMES = 5        # 0.16 seconds - Quick head turn
HEAD_TURN_ALERT_FRAMES = 10         # 0.33 seconds - Head turned away
HEAD_TURN_SEVERE_FRAMES = 20        # 0.66 seconds - Persistent head turn

# No face detection thresholds
NO_FACE_WARNING_FRAMES = 15         # 0.5 seconds - Face not visible
NO_FACE_ALERT_FRAMES = 30           # 1 second - Face missing

# =========================================================
# SOUND FREQUENCIES (Hz) AND DURATIONS (ms)
# =========================================================
# Warning level (low risk)
SOUND_WARNING_FREQ = 800            # 800 Hz beep
SOUND_WARNING_DURATION = 200        # 200 milliseconds

# Violation level (medium risk)
SOUND_VIOLATION_FREQ = 1000         # 1000 Hz beep
SOUND_VIOLATION_DURATION = 300      # 300 milliseconds

# Cheating level (high risk)
SOUND_CHEATING_FREQ = 1500          # 1500 Hz beep
SOUND_CHEATING_DURATION = 400       # 400 milliseconds

# =========================================================
# DISPLAY COLORS (BGR format for OpenCV)
# =========================================================
# Risk level colors
RISK_HIGH_COLOR = (0, 0, 220)       # Red - High risk (70-100%)
RISK_MED_COLOR = (0, 165, 255)      # Orange - Medium risk (40-69%)
RISK_LOW_COLOR = (0, 200, 80)       # Green - Low risk (0-39%)

# Text colors
TEXT_NORMAL_COLOR = (200, 200, 200) # Grey - Normal information
TEXT_WARNING_COLOR = (0, 165, 255)  # Orange - Warning messages
TEXT_ALERT_COLOR = (0, 0, 255)      # Red - Alert messages
TEXT_SUCCESS_COLOR = (0, 255, 0)    # Green - Success messages

# =========================================================
# WINDOW SETTINGS
# =========================================================
DISPLAY_WINDOW_NAME = "Eye Movement Detector"

# =========================================================
# ALARM MESSAGES (Displayed on screen)
# =========================================================
ALARM_MESSAGES = {
    'gaze_warning': "⚠️ Please look at the camera!",
    'gaze_alert': "🚨 STOP looking away!",
    'gaze_severe': "🔴 SEVERE: Persistent gaze away!",
    'head_warning': "⚠️ Please face the camera!",
    'head_alert': "🚨 STOP turning your head!",
    'head_severe': "🔴 SEVERE: Persistent head movement!",
    'no_face': "⚠️ Face not detected! Sit properly.",
    'no_face_persistent': "🚨 Face missing for too long!",
    'multi_face': "🔴🔴🔴 CHEATING: Multiple people!",
    'risk_high': "🔴 HIGH RISK: Cheating behavior!",
}

# =========================================================
# LOGGING SETTINGS
# =========================================================
LOG_ALARMS = True                   # Print alarms to console
SAVE_ALARM_LOG = True               # Save alarms to file
ALARM_LOG_FILE = "alarm_log.txt"    # Alarm log filename

# =========================================================
# ADVANCED SETTINGS (Rarely changed)
# =========================================================
ENABLE_VOICE_ALERTS = False         # Text-to-speech alerts (requires pyttsx3)
ENABLE_SCREEN_FLASH = False         # Flash screen on alarm
SCREEN_FLASH_COLOR = (0, 0, 255)    # Flash color (red)
SCREEN_FLASH_DURATION = 100         # Flash duration (ms)

# =========================================================
# API AND NETWORK SETTINGS
# =========================================================
API_TIMEOUT = 10                    # API request timeout (seconds)
LIVE_UPDATE_INTERVAL = 5            # Send live update every N seconds
REPORT_RETRY_COUNT = 3              # Number of retries for failed uploads

# =========================================================
# FILE PATHS
# =========================================================
REPORTS_DIR = "reports"             # Directory for saving reports
MODELS_DIR = "models"               # Directory for ML models
LOGS_DIR = "logs"                   # Directory for log files

# =========================================================
# SESSION RECOVERY AND HEARTBEAT SETTINGS
# =========================================================
SESSION_CLEANUP_TIMEOUT = 30        # Timeout in seconds to hold disconnected sessions
HEARTBEAT_TIMEOUT = 10              # Timeout in seconds to wait for pings before marking connection silent
HEARTBEAT_INTERVAL = 3              # Timeout in seconds between client heartbeat pings