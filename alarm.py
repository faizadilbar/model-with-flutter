# alarm.py - Non-Blocking Proctoring Alarm System (Video Won't Freeze)

import threading
import time
import winsound
import sys
import os

# Try to import pygame for better sound quality
try:
    import pygame
    import numpy as np
    PYGAME_AVAILABLE = True
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    print("[ALARM] Pygame initialized for high-quality audio")
except ImportError:
    PYGAME_AVAILABLE = False
    print("[ALARM] Pygame not available. Using winsound (still effective)")

class ProctoringAlarm:
    """Non-Blocking Alarm system - Video continues while alarm plays"""
    
    def __init__(self):
        self.violation_count = 0
        self.last_alarm_time = 0
        self.alarm_cooldown = 3  # Minimum seconds between alarms
        
        # Pre-generate sounds if pygame is available
        if PYGAME_AVAILABLE:
            self._generate_sounds()
    
    def _generate_sounds(self):
        """Generate synthetic beep sounds at maximum volume using numpy"""
        try:
            sample_rate = 44100
            
            def create_stereo_sound(frequency, duration):
                samples = int(sample_rate * duration)
                t = np.linspace(0, duration, samples, False)
                mono_wave = 0.5 * np.sin(frequency * 2 * np.pi * t)
                stereo_wave = np.zeros((samples, 2), dtype=np.float32)
                stereo_wave[:, 0] = mono_wave
                stereo_wave[:, 1] = mono_wave
                return (stereo_wave * 32767).astype(np.int16)
            
            self.warning_sound = create_stereo_sound(800, 0.3)
            self.violation_sound = create_stereo_sound(1200, 0.4)
            self.cheating_sound = create_stereo_sound(2000, 0.5)
            
            # Siren sound
            duration = 2.0
            samples = int(sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            freq = 800 + (1700 * t / duration)
            mono_wave = 0.5 * np.sin(2 * np.pi * freq * t)
            stereo_wave = np.zeros((samples, 2), dtype=np.float32)
            stereo_wave[:, 0] = mono_wave
            stereo_wave[:, 1] = mono_wave
            self.siren_sound = (stereo_wave * 32767).astype(np.int16)
            
            print("[ALARM] Sounds generated successfully")
        except Exception as e:
            print(f"[ALARM] Could not generate sounds: {e}")
    
    # =========================================================
    # NON-BLOCKING PLAY METHODS (using threads)
    # =========================================================
    
    def _play_winsound_async(self, frequency, duration, repeats):
        """Play winsound beep in background thread (NON-BLOCKING)"""
        def _beep():
            for _ in range(repeats):
                winsound.Beep(frequency, duration)
                time.sleep(0.05)
        threading.Thread(target=_beep, daemon=True).start()
    
    def _play_pygame_async(self, sound, repeats=1):
        """Play pygame sound in background (NON-BLOCKING)"""
        def _play():
            for _ in range(repeats):
                snd = pygame.sndarray.make_sound(sound)
                snd.set_volume(1.0)
                snd.play()
                time.sleep(0.2)  # Small gap between repeats
        threading.Thread(target=_play, daemon=True).start()
    
    def play_warning_sound(self):
        """Play warning sound (NON-BLOCKING)"""
        print("\n⚠️⚠️⚠️ WARNING: Cheating behavior detected! ⚠️⚠️⚠️")
        if PYGAME_AVAILABLE and hasattr(self, 'warning_sound'):
            self._play_pygame_async(self.warning_sound, 2)
        else:
            self._play_winsound_async(800, 300, 2)
    
    def play_violation_sound(self):
        """Play violation sound (NON-BLOCKING)"""
        print("\n🚨🚨🚨 VIOLATION ALERT: Suspicious behavior detected! 🚨🚨🚨")
        if PYGAME_AVAILABLE and hasattr(self, 'violation_sound'):
            self._play_pygame_async(self.violation_sound, 3)
        else:
            self._play_winsound_async(1000, 400, 3)
    
    def play_cheating_sound(self):
        """Play cheating alarm (NON-BLOCKING)"""
        print("\n🔴🔴🔴🔴🔴 CHEATING DETECTED! 🔴🔴🔴🔴🔴")
        print("🔴 IMMEDIATE ATTENTION REQUIRED! 🔴")
        
        if PYGAME_AVAILABLE and hasattr(self, 'siren_sound'):
            # Play siren in background
            self._play_pygame_async(self.siren_sound, 1)
            time.sleep(0.1)  # Small delay
            self._play_pygame_async(self.cheating_sound, 5)
        else:
            self._play_winsound_async(2000, 500, 5)
    
    def play_mass_alert(self):
        """Mass alert for widespread cheating (NON-BLOCKING)"""
        print("\n🔴🔴🔴🔴🔴 MASSIVE CHEATING ALERT! ENTIRE CLASSROOM NOTIFIED! 🔴🔴🔴🔴🔴")
        
        if PYGAME_AVAILABLE and hasattr(self, 'siren_sound'):
            def _mass_alert():
                for _ in range(3):
                    snd = pygame.sndarray.make_sound(self.siren_sound)
                    snd.set_volume(1.0)
                    snd.play()
                    time.sleep(2.0)
            threading.Thread(target=_mass_alert, daemon=True).start()
        else:
            self._play_winsound_async(1500, 400, 10)
    
    def trigger_alarm(self, risk_level, violation_type):
        """
        Trigger alarm based on risk level (NON-BLOCKING)
        risk_level: 'low', 'medium', 'high'
        violation_type: 'gaze_away', 'head_turn', 'no_face', 'multi_face'
        """
        current_time = time.time()
        
        # Prevent alarm spam (cooldown)
        if current_time - self.last_alarm_time < self.alarm_cooldown:
            return
        
        self.last_alarm_time = current_time
        self.violation_count += 1
        
        # Different alarm patterns for different violations
        if risk_level == 'high':
            print("=" * 80)
            print(f"🔴🔴🔴 HIGH RISK ALERT! {violation_type.upper()} DETECTED! 🔴🔴🔴")
            print(f"🔴 Alarm #{self.violation_count} - Immediate attention required!")
            print("=" * 80)
            self.play_cheating_sound()
            
        elif risk_level == 'medium':
            print("=" * 80)
            print(f"🚨🚨 MEDIUM RISK ALERT! {violation_type.upper()} detected! 🚨🚨")
            print(f"🚨 Alarm #{self.violation_count} - Please check student behavior")
            print("=" * 80)
            self.play_violation_sound()
            
        else:  # low risk
            print(f"⚠️ WARNING: {violation_type.upper()} detected (Alarm #{self.violation_count})")
            self.play_warning_sound()
    
    def trigger_mass_alert(self, violation_type="MULTIPLE_CHEATING"):
        """Trigger alarm for widespread cheating (NON-BLOCKING)"""
        current_time = time.time()
        
        if current_time - self.last_alarm_time < self.alarm_cooldown:
            return
        
        self.last_alarm_time = current_time
        self.violation_count += 1
        
        print("=" * 80)
        print(f"🔴🔴🔴🔴🔴 MASS ALERT! {violation_type} DETECTED! 🔴🔴🔴🔴🔴")
        print(f"🔴 This alarm is designed to be heard by 500+ students!")
        print(f"🔴 Alarm #{self.violation_count} - Full classroom intervention required!")
        print("=" * 80)
        
        self.play_mass_alert()
    
    def continuous_alarm(self, duration=15):
        """Continuous alarm for persistent cheating (NON-BLOCKING)"""
        print("🔴🔴🔴 CONTINUOUS CHEATING ALARM ACTIVATED! 🔴🔴🔴")
        print(f"🔴 This alarm will sound for {duration} seconds! 🔴")
        
        if PYGAME_AVAILABLE and hasattr(self, 'siren_sound'):
            def _continuous():
                end_time = time.time() + duration
                while time.time() < end_time:
                    snd = pygame.sndarray.make_sound(self.siren_sound)
                    snd.set_volume(1.0)
                    snd.play()
                    time.sleep(2.0)
            threading.Thread(target=_continuous, daemon=True).start()
        else:
            self._play_winsound_async(2000, 200, duration)
    
    def stop_alarm(self):
        """Stop any currently playing alarm"""
        print("[ALARM] Stopping alarm...")
        if PYGAME_AVAILABLE:
            pygame.mixer.stop()
    
    def reset(self):
        """Reset alarm state"""
        print(f"[ALARM] Resetting alarm system. Total alarms triggered: {self.violation_count}")
        self.violation_count = 0
        self.last_alarm_time = 0
    
    def get_alarm_statistics(self):
        """Get alarm statistics"""
        return {
            'total_alarms': self.violation_count,
            'last_alarm_time': self.last_alarm_time,
            'alarm_cooldown': self.alarm_cooldown,
            'pygame_available': PYGAME_AVAILABLE,
        }
    
    def test_alarm_sequence(self):
        """Test all alarm sounds in sequence"""
        print("\n" + "=" * 80)
        print("TESTING ALARM SYSTEM - LOUD SOUNDS AHEAD!")
        print("=" * 80)
        
        print("\n[1/5] Testing WARNING sound...")
        self.play_warning_sound()
        time.sleep(1)
        
        print("\n[2/5] Testing VIOLATION sound...")
        self.play_violation_sound()
        time.sleep(1)
        
        print("\n[3/5] Testing CHEATING sound...")
        self.play_cheating_sound()
        time.sleep(1)
        
        print("\n[4/5] Testing MASS ALERT...")
        self.play_mass_alert()
        time.sleep(1)
        
        print("\n[5/5] Testing CONTINUOUS ALARM (5 seconds)...")
        self.continuous_alarm(5)
        
        print("\n" + "=" * 80)
        print("All alarm tests completed!")
        print("=" * 80)


# =========================================================
# QUICK TEST FUNCTION
# =========================================================

def quick_test():
    """Quick test to verify alarm is working"""
    alarm = ProctoringAlarm()
    print("\n🔔 Testing alarm system...")
    print("You should hear a series of beeps/alarms")
    print("If you don't hear anything, check your system volume\n")
    
    time.sleep(1)
    alarm.play_warning_sound()
    time.sleep(1)
    alarm.play_violation_sound()
    
    print("\n✅ Alarm test completed!")
    print(f"Alarm statistics: {alarm.get_alarm_statistics()}")


if __name__ == "__main__":
    # Run full test sequence
    test_alarm = ProctoringAlarm()
    test_alarm.test_alarm_sequence()
    
    print("\n" + "=" * 80)
    print("To use this alarm in your proctoring system, import it:")
    print("  from alarm import ProctoringAlarm")
    print("  alarm = ProctoringAlarm()")
    print("  alarm.trigger_alarm('high', 'gaze_away')")
    print("=" * 80)