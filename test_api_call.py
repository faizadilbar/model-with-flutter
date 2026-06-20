import requests

API_BASE_URL = "https://bgnuf22eight.com/cheating/proctoring-backend/public/api"

print("Testing API from Python...")

payload = {
    "student_id": "PYTHON_TEST",
    "student_name": "Python Test User",
    "book_name": "Test Course",
    "course_name": "Test Course",
    "quiz_code": "TEST123",
    "exam_date": "2024-01-15",
    "start_time": "10:00"
}

try:
    response = requests.post(
        f"{API_BASE_URL}/exam-sessions/start",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 201:
        print("✅ API WORKING! Python can call the API.")
    else:
        print("❌ API returned error")
        
except Exception as e:
    print(f"❌ Error: {e}")