# 📮 Postman API Guide — Cheating Detection System
**Base URL:** `https://web-production-3a1d7.up.railway.app`

---

## 1. ✅ Health Check
**Test karo server chal raha hai ya nahi**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/health`
- **Body:** None

**Expected Response:**
```json
{
  "status": true,
  "message": "Proctoring server is running"
}
```

---

## 2. 📊 Status Check
**Exam chal raha hai ya nahi**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/status`
- **Body:** None

**Expected Response:**
```json
{
  "status": true,
  "running": false,
  "exam": {}
}
```

---

## 3. 🎬 Start Exam
**Exam monitoring shuru karo**

- **Method:** `POST`
- **URL:** `https://web-production-3a1d7.up.railway.app/start-exam`
- **Headers:**
  - `Content-Type: application/json`
- **Body (raw → JSON):**
```json
{
  "student_id": "S001",
  "student_name": "Test Student",
  "course_name": "Computer Science",
  "quiz_code": "CS101",
  "quiz_id": "Q1",
  "exam_date": "2026-07-16",
  "start_time": "20:30",
  "end_time": "21:30"
}
```

**Expected Response:**
```json
{
  "status": true,
  "message": "Exam monitoring started",
  "data": {
    "student_id": "S001",
    "student_name": "Test Student",
    "course_name": "Computer Science",
    "quiz_code": "CS101"
  }
}
```

---

## 4. 📈 Live Metrics
**Exam ke dauran live cheating metrics dekho**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/metrics`
- **Body:** None

**Expected Response (exam active ho to):**
```json
{
  "status": "active",
  "alarm_level": "none",
  "risk_score": 0.0,
  "max_risk": 0.0,
  "total_alarms": 0,
  "blink_count": 0,
  "last_alarm_type": "NONE",
  "flags": {
    "gaze_away": false,
    "head_turn": false,
    "multiple_faces": false,
    "no_face": false
  }
}
```

---

## 5. 📸 Upload Frame
**Camera ka ek frame server ko bhejo (cheating detect hogi)**

- **Method:** `POST`
- **URL:** `https://web-production-3a1d7.up.railway.app/upload-frame`
- **Headers:** *(koi Content-Type mat lagao — form-data khud set karta hai)*
- **Body:** `form-data`
  - Key: `frame` → Type: **File** → Value: *koi bhi JPEG image select karo*

> ⚠️ Pehle `/start-exam` call karo, phir yeh endpoint kaam karega

**Expected Response:**
```json
{
  "status": true,
  "message": "Frame processed successfully",
  "result": {
    "risk_score": 12.5,
    "alarm_level": "none",
    "gaze_away_count": 0,
    "head_turn_count": 0,
    "no_face_count": 0,
    "multiple_face_count": 0,
    "total_blinks": 2,
    "flags": {
      "gaze_away": false,
      "head_turn": false,
      "multiple_faces": false,
      "no_face": false
    }
  }
}
```

---

## 6. 🛑 Stop Exam
**Exam monitoring band karo aur report generate karo**

- **Method:** `POST`
- **URL:** `https://web-production-3a1d7.up.railway.app/stop-exam`
- **Body:** None (ya empty JSON `{}`)

**Expected Response:**
```json
{
  "status": true,
  "message": "Exam monitoring stopped and report generated"
}
```

---

## 7. 🗂️ All Sessions (Database)
**Tamam exam sessions ki list**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/api/sessions`
- **Body:** None

**Expected Response:**
```json
{
  "status": true,
  "count": 64,
  "sessions": [ ... ]
}
```

---

## 8. 🔍 Single Session Detail
**Ek specific session ki poori detail + violations**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/api/sessions/M77_1784005773`
- **Body:** None

*(session_id aap `/api/sessions` se le sakte ho)*

---

## 9. ⚠️ All Violations
**Tamam violations ki list**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/api/violations`
- **Body:** None

**Filter by session:**
- **URL:** `https://web-production-3a1d7.up.railway.app/api/violations?session_id=M77_1784005773`

---

## 10. 📉 Risk History
**Ek session ka risk score timeline**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/api/risk-history?session_id=M77_1784005773`
- **Body:** None

---

## 11. 🎥 Get Frame (Teacher View)
**Student ka latest camera frame dekho**

- **Method:** `GET`
- **URL:** `https://web-production-3a1d7.up.railway.app/get-frame/S001`
- **Body:** None

*(S001 ki jagah student_id dalo)*

---

## ⚡ Quick Test Flow (Postman Collection Order)

1. `GET /health` → Server check
2. `POST /start-exam` → Exam shuru karo
3. `GET /status` → Confirm exam chal raha hai
4. `POST /upload-frame` → Frame bhejo (form-data, file = JPEG)
5. `GET /metrics` → Live results dekho
6. `POST /stop-exam` → Exam band karo
7. `GET /api/sessions` → Report dekho

---

## 🔴 Common Errors

| Error | Reason | Fix |
|-------|--------|-----|
| `400 - No active exam session` | `/upload-frame` pehle `/start-exam` nahi kiya | Pehle start karo |
| `404 - No frame available` | `/get-frame` pe koi frame nahi | Upload karo pehle |
| `500 - Internal Server Error` | Server crash | `/health` check karo |
