# report.py - Complete with alarm history support

import time
from dataclasses import dataclass, field


@dataclass
class FrameRecord:
    elapsed_s: float
    stats: dict
    flags: list[str]


class SessionReport:
    """Accumulates per-frame data and writes a final text report."""

    def __init__(self):
        self._records: list[FrameRecord] = []
        self._alarms: list[dict] = []  # Added: store alarm history
        self._start_wall = time.time()

    def record(self, elapsed_s: float, stats: dict, flags: list[str]) -> None:
        self._records.append(FrameRecord(elapsed_s, dict(stats), list(flags)))

    # =========================================================
    # New method to add alarm to report
    # =========================================================
    
    def add_alarm(self, alarm_type: str, severity: str, risk_score: float) -> None:
        """Add alarm to report"""
        self._alarms.append({
            'time': time.strftime("%H:%M:%S"),
            'type': alarm_type,
            'severity': severity,
            'risk_score': risk_score
        })
        print(f"[REPORT] Alarm recorded: {alarm_type} ({severity})")

    def get_alarms(self) -> list:
        """Return all alarms"""
        return self._alarms

    # ─────────────────────────────────────────
    # Methods used by main.py for API
    # ─────────────────────────────────────────

    def avg_risk(self) -> float:
        """Return average smooth risk score across all frames."""
        if not self._records:
            return 0.0
        return sum(r.stats["smooth_risk"] for r in self._records) / len(self._records)

    def max_risk(self) -> float:
        """Return highest smooth risk score recorded."""
        if not self._records:
            return 0.0
        return max(r.stats["smooth_risk"] for r in self._records)

    def flag_counts(self) -> dict:
        """Return count of each flag type across all frames."""
        counts = {}
        for r in self._records:
            for f in r.flags:
                counts[f] = counts.get(f, 0) + 1
        return counts

    def high_risk_count(self) -> int:
        """Return number of frames where smooth risk was >= 70."""
        return sum(
            1 for r in self._records
            if r.stats["smooth_risk"] >= 70
        )

    def total_blinks(self) -> int:
        """Return total blink count from last frame."""
        if not self._records:
            return 0
        return self._records[-1].stats["blink_count"]

    def avg_blink_rate(self) -> float:
        """Return average blink rate per minute."""
        if not self._records:
            return 0.0
        return sum(
            r.stats["blink_rate"] for r in self._records
        ) / len(self._records)

    def duration(self) -> float:
        """Return total session duration in seconds."""
        if not self._records:
            return 0.0
        return self._records[-1].elapsed_s

    def frame_count(self) -> int:
        """Return total number of frames recorded."""
        return len(self._records)

    # ─────────────────────────────────────────
    # Save report to file with alarm history
    # ─────────────────────────────────────────

    def save(self, path: str, alarm_history: list = None) -> None:
        """Save report to file with alarm details"""
        if not self._records:
            return

        # Use provided alarm_history or stored alarms
        alarms = alarm_history if alarm_history else self._alarms

        n = len(self._records)
        duration = self.duration()
        avg_risk = self.avg_risk()
        max_risk = self.max_risk()
        total_blinks = self.total_blinks()
        avg_blink_rate = self.avg_blink_rate()
        flag_counts = self.flag_counts()
        high_risk_s = self.high_risk_count()

        lines = [
            "=" * 60,
            "  EYE MOVEMENT DETECTOR — SESSION REPORT",
            "=" * 60,
            f"  Duration         : {duration:.1f} s",
            f"  Frames analysed  : {n}",
            f"  Average risk     : {avg_risk:.1f} / 100",
            f"  Peak risk        : {max_risk:.1f} / 100",
            f"  High-risk frames : {high_risk_s} ({high_risk_s/n*100:.1f}%)",
            f"  Total blinks     : {total_blinks}",
            f"  Avg blink rate   : {avg_blink_rate:.1f} /min",
            "",
            "  Alert flag counts:",
        ]

        for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1]):
            pct = count / n * 100
            lines.append(f"    {flag:<20} {count:>5} frames  ({pct:.1f}%)")

        lines += [
            "",
            "  Risk timeline (every 10 s):",
        ]

        seen_ts: set[int] = set()
        for r in self._records:
            bucket = int(r.elapsed_s) // 10 * 10
            if bucket not in seen_ts:
                seen_ts.add(bucket)
                bar_len = int(r.stats["smooth_risk"] / 5)
                bar = "#" * bar_len + "-" * (20 - bar_len)
                lines.append(
                    f"    t={r.elapsed_s:>6.1f}s  [{bar}]  {r.stats['smooth_risk']:>5.1f}"
                )

        # =========================================================
        # ADD ALARM HISTORY SECTION
        # =========================================================
        if alarms:
            lines += [
                "",
                "-" * 60,
                "  ALARM / VIOLATION DETAILS",
                "-" * 60,
            ]
            for i, alarm in enumerate(alarms, 1):
                alarm_time = alarm.get('time', alarm.get('timestamp', 'N/A'))
                alarm_type = alarm.get('type', alarm.get('violation_type', 'unknown'))
                alarm_severity = alarm.get('severity', 'medium')
                alarm_risk = alarm.get('risk', alarm.get('risk_score', 0))
                lines.append(
                    f"    #{i:<3} Time: {alarm_time} | "
                    f"Type: {alarm_type.upper()} | "
                    f"Severity: {alarm_severity.upper()} | "
                    f"Risk: {alarm_risk:.1f}%"
                )
            lines.append(f"\n    Total Alarms: {len(alarms)}")
        else:
            lines += ["", "  Alarm History: No alarms triggered"]

        lines.append("=" * 60)

        # Write to file with UTF-8 encoding
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        print(f"[REPORT] Saved → {path}")