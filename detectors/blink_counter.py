# detectors/blink_counter.py

import time
import config


class BlinkCounter:

    def __init__(self):
        self._counter        = 0
        self._consec_frames  = 0
        self._eye_closed     = False
        self._blink_timestamps: list[float] = []
        self._session_start  = time.time()

    def update(self, ear: float) -> bool:
        blink_detected = False

        if ear < config.EAR_BLINK_THRESHOLD:
            # Eye is closing
            self._consec_frames += 1
            self._eye_closed     = True
        else:
            # Eye opened — check if it was closed long enough
            if self._eye_closed and \
               self._consec_frames >= config.EAR_CONSEC_FRAMES:
                self._counter += 1
                self._blink_timestamps.append(time.time())
                blink_detected = True
            # Reset
            self._consec_frames = 0
            self._eye_closed    = False

        return blink_detected

    def blink_rate(self, window_seconds: int = 60) -> float:
        now     = time.time()
        cutoff  = now - window_seconds
        recent  = [t for t in self._blink_timestamps if t > cutoff]
        elapsed = min(now - self._session_start, window_seconds)
        if elapsed < 1:
            return 0.0
        return round(len(recent) / elapsed * 60, 1)

    def is_anomalous(self) -> bool:
        rate = self.blink_rate()
        return (rate < config.NORMAL_BLINK_RATE_MIN or
                rate > config.NORMAL_BLINK_RATE_MAX)

    @property
    def count(self) -> int:
        return self._counter