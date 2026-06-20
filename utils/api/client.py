# api/client.py

import requests
import json
import time
import threading
import queue
from pathlib import Path


class ProctoringAPIClient:
    """
    Handles all communication between the Python proctoring app
    and the Laravel backend API.
    """

    def __init__(self, base_url: str):
        self.base_url   = base_url.rstrip("/")
        self._token     = None
        self._session_id = None
        self._event_queue: queue.Queue = queue.Queue()
        self._flush_interval = 5        # send events every 5 seconds
        self._batch_size     = 50       # max events per batch
        self._running        = False

    # ------------------------------------------------------------------ auth
    def login(self, student_id: str, password: str) -> bool:
        try:
            r = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"student_id": student_id, "password": password},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                self._token = data["token"]
                print(f"[API] Logged in as {data['name']}")
                return True
            print(f"[API] Login failed: {r.json().get('message')}")
            return False
        except requests.RequestException as e:
            print(f"[API] Login error: {e}")
            return False

    def logout(self):
        self._post("/api/auth/logout")
        self._token = None

    # --------------------------------------------------------------- session
    def start_session(self, exam_id: str, exam_name: str = "") -> int | None:
        r = self._post("/api/sessions/start", {
            "exam_id":   exam_id,
            "exam_name": exam_name,
        })
        if r and r.status_code == 201:
            self._session_id = r.json()["session_id"]
            self._start_flush_thread()
            print(f"[API] Session started: ID {self._session_id}")
            return self._session_id
        return None

    def end_session(self, summary: dict):
        # Flush remaining events first
        self._flush_events(force=True)
        self._running = False

        if self._session_id:
            self._post(f"/api/sessions/{self._session_id}/end", summary)
            print(f"[API] Session {self._session_id} ended and summary saved.")

    # --------------------------------------------------------------- events
    def queue_event(self, elapsed_s: float, stats: dict, flags: list[str]):
        """Call this every frame — events are batched and sent every 5 s."""
        event = {
            "elapsed_seconds": round(elapsed_s, 2),
            "raw_risk":        stats["raw_risk"],
            "smooth_risk":     stats["smooth_risk"],
            "face_count":      stats["face_count"],
            "ear":             round(stats["ear"], 4),
            "gaze_yaw":        round(stats["gaze_yaw"], 4),
            "gaze_pitch":      round(stats["gaze_pitch"], 4),
            "head_yaw":        round(stats["head_yaw"], 2),
            "head_pitch":      round(stats["head_pitch"], 2),
            "blink_rate":      round(stats["blink_rate"], 1),
            "flags":           flags,
            "recorded_at":     time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._event_queue.put(event)

    def _start_flush_thread(self):
        self._running = True
        threading.Thread(target=self._flush_loop, daemon=True).start()

    def _flush_loop(self):
        while self._running:
            time.sleep(self._flush_interval)
            self._flush_events()

    def _flush_events(self, force: bool = False):
        events = []
        try:
            while True:
                events.append(self._event_queue.get_nowait())
                if not force and len(events) >= self._batch_size:
                    break
        except queue.Empty:
            pass

        if not events or not self._session_id:
            return

        r = self._post(
            f"/api/sessions/{self._session_id}/events",
            {"events": events},
        )
        if r and r.status_code == 201:
            print(f"[API] Flushed {len(events)} events.")
        else:
            # Put them back on failure so they are not lost
            for e in events:
                self._event_queue.put(e)
            print("[API] Event flush failed — will retry.")

    # ------------------------------------------------------------- snapshots
    def upload_snapshot(self, image_path: str, elapsed_s: float,
                        risk: float, flags: list[str]) -> bool:
        if not self._session_id:
            return False
        try:
            with open(image_path, "rb") as f:
                r = requests.post(
                    f"{self.base_url}/api/sessions/{self._session_id}/snapshots",
                    headers=self._auth_headers(),
                    data={
                        "elapsed_seconds": elapsed_s,
                        "risk_at_capture": risk,
                        "flags[]":         flags,
                    },
                    files={"image": (Path(image_path).name, f, "image/jpeg")},
                    timeout=15,
                )
            return r.status_code == 201
        except requests.RequestException as e:
            print(f"[API] Snapshot upload error: {e}")
            return False

    # ------------------------------------------------------------ internals
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _post(self, endpoint: str, data: dict = None):
        if not self._token:
            return None
        try:
            return requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers=self._auth_headers(),
                timeout=10,
            )
        except requests.RequestException as e:
            print(f"[API] POST {endpoint} failed: {e}")
            return None