# risk/scorer.py

import config


class RiskScorer:
    """
    Weighted fusion of all detector signals -> risk score 0-100.
    Also maintains a simple exponential moving average for smoothing.
    """

    def __init__(self, ema_alpha: float = 0.25):
        self._ema_alpha   = ema_alpha
        self._smoothed    = 0.0
        self._baseline_yaw = config.HEAD_BASELINE_YAW

    def set_baseline(self, baseline_yaw: float):
        """Call this after calibration to set personal head baseline."""
        self._baseline_yaw = baseline_yaw

    def compute(
        self,
        face_count:      int,
        looking_away:    bool,
        gaze_yaw:        float,
        gaze_pitch:      float,
        head_yaw:        float,
        head_pitch:      float,
        blink_anomalous: bool,
        baseline_yaw:    float = None,
    ) -> tuple[float, float, list[str]]:
        """
        Returns (raw_score, smoothed_score, active_flags).
        """
        # Use passed baseline or stored baseline
        baseline = baseline_yaw if baseline_yaw is not None \
                   else self._baseline_yaw

        flags: list[str] = []

        # Component scores (each 0-1)
        face_absent_score = 1.0 if face_count == 0 else 0.0
        multi_face_score  = min(1.0, (face_count - 1) * 0.5) \
                            if face_count > 1 else 0.0
        gaze_score        = 1.0 if looking_away else 0.0
        head_score        = self._head_score(head_yaw, head_pitch, baseline)
        blink_score       = 1.0 if blink_anomalous else 0.0

        if face_count == 0:    flags.append("! NO FACE")
        if face_count > 1:     flags.append(f"! {face_count} FACES")
        if looking_away:       flags.append("! GAZE AWAY")
        if head_score > 0.5:   flags.append("! HEAD TURNED")
        if blink_anomalous:    flags.append("! BLINK ANOMALY")

        raw = (
            config.WEIGHT_FACE_ABSENT   * face_absent_score +
            config.WEIGHT_MULTI_FACE    * multi_face_score  +
            config.WEIGHT_GAZE_AWAY     * gaze_score        +
            config.WEIGHT_HEAD_TURN     * head_score        +
            config.WEIGHT_BLINK_ANOMALY * blink_score
        ) * 100

        self._smoothed = (self._ema_alpha * raw +
                          (1 - self._ema_alpha) * self._smoothed)

        return round(raw, 1), round(self._smoothed, 1), flags

    def _head_score(self, yaw: float, pitch: float,
                baseline: float = 0.0) -> float:
        yaw_excess   = max(0, abs(yaw - baseline) - config.HEAD_YAW_THRESHOLD)
        pitch_excess = max(0, abs(pitch) - config.HEAD_PITCH_THRESHOLD)
        return min(1.0, (yaw_excess + pitch_excess) / 30.0)

    @property
    def smoothed(self) -> float:
        return self._smoothed