/**
 * proctor.js — AI Proctoring Client
 * Captures webcam frames, sends to Laravel proxy → Python model API
 * Shows alarm overlay + plays sound when cheating detected
 */

(function () {
    'use strict';

    // ── CONFIG ────────────────────────────────────────────────────────────
    const FRAME_INTERVAL_MS   = 2500;   // Send frame every 2.5 seconds
    const METRICS_INTERVAL_MS = 3000;   // Poll metrics every 3 seconds
    const FRAME_WIDTH         = 320;
    const FRAME_HEIGHT        = 240;
    const FRAME_QUALITY       = 0.7;

    // ── STATE ─────────────────────────────────────────────────────────────
    let stream         = null;
    let videoEl        = null;
    let canvasEl       = null;
    let ctx            = null;
    let frameTimer     = null;
    let metricsTimer   = null;
    let alarmActive    = false;
    let sessionStarted = false;
    let examSubmitting = false;

    // ── CSRF TOKEN ────────────────────────────────────────────────────────
    function getCsrf() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    // ── INIT ──────────────────────────────────────────────────────────────
    async function init() {
        // Build hidden video + canvas for frame capture
        videoEl  = document.createElement('video');
        canvasEl = document.createElement('canvas');
        videoEl.width  = FRAME_WIDTH;
        videoEl.height = FRAME_HEIGHT;
        canvasEl.width  = FRAME_WIDTH;
        canvasEl.height = FRAME_HEIGHT;
        videoEl.autoplay  = true;
        videoEl.muted     = true;
        videoEl.playsInline = true;
        videoEl.style.display = 'none';
        canvasEl.style.display = 'none';
        document.body.appendChild(videoEl);
        document.body.appendChild(canvasEl);
        ctx = canvasEl.getContext('2d');

        await requestCamera();
    }

    // ── CAMERA ────────────────────────────────────────────────────────────
    async function requestCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { width: FRAME_WIDTH, height: FRAME_HEIGHT, facingMode: 'user' },
                audio: false
            });
            videoEl.srcObject = stream;
            videoEl.onloadedmetadata = () => {
                videoEl.play();
                startSession();
            };
            showCameraStatus('🟢 Camera active — Proctoring enabled', false);
        } catch (err) {
            showCameraStatus('⚠️ Camera access denied — Proctoring inactive', true);
            console.warn('[Proctor] Camera access denied:', err.message);
        }
    }

    // ── START SESSION (with Fallback Session ID & Guaranteed Timer) ───────
    let proctoringSessionId = null;

    async function startSession() {
        // Reset state for clean start on re-entry
        if (frameTimer) clearInterval(frameTimer);
        if (metricsTimer) clearInterval(metricsTimer);
        frameTimer = null;
        metricsTimer = null;
        sessionStarted = false;

        const quizCode   = window.PROCTOR_QUIZ_CODE   || '';
        const quizId     = window.PROCTOR_QUIZ_ID     || '';
        const courseName = window.PROCTOR_COURSE_NAME || '';
        const quizDate   = window.PROCTOR_QUIZ_DATE   || '';
        const startTime  = window.PROCTOR_START_TIME  || '';
        const endTime    = window.PROCTOR_END_TIME    || '';

        try {
            const res = await fetch(window.PROCTOR_START_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrf(),
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    quiz_code:   quizCode,
                    quiz_id:     quizId,
                    course_name: courseName,
                    quiz_date:   quizDate,
                    start_time:  startTime,
                    end_time:    endTime,
                })
            });

            const data = await res.json();
            if (data && (data.status === true || data.status === 1 || data.session_id)) {
                proctoringSessionId = data.session_id || data.id || null;
                console.log('[Proctor] Session started successfully:', data);
            }
        } catch (err) {
            console.warn('[Proctor] startSession delayed/failed, using fallback session ID:', err.message);
        }

        // Guaranteed Fallback Session ID if API response was delayed/failed so frame uploading NEVER stops
        if (!proctoringSessionId) {
            proctoringSessionId = Math.floor(Date.now() / 1000);
        }

        sessionStarted = true;
        startFrameCapture();
        startMetricsPoll();
    }

    // ── FRAME CAPTURE ─────────────────────────────────────────────────────
    function startFrameCapture() {
        if (!frameTimer) {
            frameTimer = setInterval(captureAndSend, FRAME_INTERVAL_MS);
            console.log('[Proctor] Frame upload timer started for Session #', proctoringSessionId);
        }
    }

    async function captureAndSend() {
        if (!sessionStarted || examSubmitting) return;
        if (!videoEl || videoEl.readyState < 2) return;

        try {
            ctx.drawImage(videoEl, 0, 0, FRAME_WIDTH, FRAME_HEIGHT);
            const b64 = canvasEl.toDataURL('image/jpeg', FRAME_QUALITY);

            await fetch(window.PROCTOR_FRAME_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrf(),
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ frame_b64: b64 })
            });
        } catch (err) {
            // Silent — frame upload failures are non-critical
        }
    }

    // ── METRICS POLL ──────────────────────────────────────────────────────
    function startMetricsPoll() {
        metricsTimer = setInterval(pollMetrics, METRICS_INTERVAL_MS);
    }

    async function pollMetrics() {
        if (!sessionStarted || examSubmitting) return;

        try {
            const res  = await fetch(window.PROCTOR_METRICS_URL, {
                headers: { 'Accept': 'application/json' }
            });
            const data = await res.json();

            updateRiskBadge(data);

            const level = (data.alarm_level || 'none').toLowerCase();
            // Only trigger alarm audio/popup for excessive movements (HIGH or CRITICAL violations)
            if (level === 'high' || level === 'critical' || level === 'severe') {
                triggerAlarm(level, data);
            } else {
                dismissAlarm();
            }
        } catch (err) {
            // Silent
        }
    }

    let localTriggeredAlarmsCount = 0;

    // ── STOP SESSION (called on quiz submit) ──────────────────────────────
    async function stopSession() {
        examSubmitting = true;
        clearInterval(frameTimer);
        clearInterval(metricsTimer);

        if (stream) {
            stream.getTracks().forEach(t => t.stop());
        }

        if (!sessionStarted) return;

        try {
            await fetch(window.PROCTOR_STOP_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrf(),
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    total_alarms: localTriggeredAlarmsCount
                })
            });
            console.log('[Proctor] Session stopped & report sent');
        } catch (err) {
            console.warn('[Proctor] stopSession error:', err.message);
        }
    }

    // ── ALARM OVERLAY ─────────────────────────────────────────────────────
    function buildAlarmOverlay() {
        if (document.getElementById('proctor-alarm-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'proctor-alarm-overlay';
        overlay.style.cssText = [
            'position:fixed',
            'top:80px',
            'right:20px',
            'z-index:999998',
            'max-width:360px',
            'width:calc(100% - 40px)',
            'background:linear-gradient(135deg,#1a0a0a,#3d0000)',
            'border:2px solid #EF4444',
            'border-radius:20px',
            'padding:20px 22px',
            'box-shadow:0 0 0 4px rgba(239,68,68,0.3),0 20px 40px rgba(0,0,0,0.5)',
            'display:none',
            'animation:proctorPulse 1s ease-in-out infinite',
            'font-family:DM Sans,system-ui,sans-serif',
        ].join(';');

        overlay.innerHTML = `
            <style>
                @keyframes proctorPulse {
                    0%,100% { box-shadow: 0 0 0 4px rgba(239,68,68,0.3), 0 20px 40px rgba(0,0,0,.5); }
                    50%     { box-shadow: 0 0 0 10px rgba(239,68,68,0.1), 0 20px 40px rgba(0,0,0,.5); }
                }
                @keyframes proctorBounce {
                    0%,100% { transform: translateY(0); }
                    50%     { transform: translateY(-6px); }
                }
                #proctor-alarm-overlay .pa-icon { animation: proctorBounce 0.6s ease-in-out infinite; display:inline-block; }
            </style>
            <div style="display:flex;align-items:flex-start;gap:14px;">
                <div class="pa-icon" style="font-size:34px;flex-shrink:0;">🚨</div>
                <div style="flex:1;min-width:0;">
                    <div id="proctor-alarm-title" style="font-size:15px;font-weight:800;color:#FF6B6B;margin-bottom:4px;font-family:Bricolage Grotesque,sans-serif;">
                        CHEATING DETECTED
                    </div>
                    <div id="proctor-alarm-msg" style="font-size:12px;color:rgba(255,255,255,0.75);line-height:1.5;">
                        Suspicious activity detected by AI proctor.
                    </div>
                    <div id="proctor-risk-bar-wrap" style="margin-top:10px;background:rgba(255,255,255,0.1);border-radius:6px;height:6px;overflow:hidden;">
                        <div id="proctor-risk-bar" style="height:100%;background:linear-gradient(90deg,#EF4444,#FF6B6B);width:0%;transition:width 0.6s ease;border-radius:6px;"></div>
                    </div>
                    <div id="proctor-risk-label" style="font-size:10px;color:rgba(255,255,255,0.5);margin-top:5px;text-align:right;">Risk: 0%</div>
                </div>
                <button onclick="window.PROCTOR_dismissAlarm()" style="background:rgba(255,255,255,0.1);border:none;border-radius:8px;padding:4px 8px;cursor:pointer;color:rgba(255,255,255,0.6);font-size:18px;flex-shrink:0;line-height:1;" title="Dismiss">×</button>
            </div>
        `;

        document.body.appendChild(overlay);
    }

    function buildRiskBadge() {
        if (document.getElementById('proctor-risk-badge')) return;

        const badge = document.createElement('div');
        badge.id = 'proctor-risk-badge';
        badge.style.cssText = [
            'position:fixed',
            'bottom:80px',
            'right:16px',
            'z-index:999997',
            'background:rgba(61,82,160,0.92)',
            'border:1px solid rgba(112,145,230,0.4)',
            'border-radius:14px',
            'padding:8px 14px',
            'display:flex',
            'align-items:center',
            'gap:8px',
            'font-family:DM Sans,system-ui,sans-serif',
            'font-size:11px',
            'color:#fff',
            'box-shadow:0 4px 20px rgba(0,0,0,0.25)',
            'cursor:default',
            'user-select:none',
            'backdrop-filter:blur(10px)',
        ].join(';');

        badge.innerHTML = `
            <span style="width:8px;height:8px;border-radius:50%;background:#10B981;flex-shrink:0;animation:secpulse 1.5s infinite;" id="proctor-dot"></span>
            <span style="font-weight:700;font-family:Bricolage Grotesque,sans-serif;letter-spacing:0.5px;">AI PROCTOR</span>
            <span id="proctor-risk-score" style="background:rgba(255,255,255,0.15);border-radius:6px;padding:2px 6px;font-weight:800;">0%</span>
        `;

        document.body.appendChild(badge);
    }

    function triggerAlarm(level, data) {
        const overlay = document.getElementById('proctor-alarm-overlay');
        if (!overlay) return;

        // If overlay was hidden, this is a new alarm ring event -> increment alarm counter
        if (!alarmActive || overlay.style.display === 'none') {
            localTriggeredAlarmsCount++;
        }
        alarmActive = true;

        // Update content
        const title = {
            'low':      '⚠️ LOW RISK DETECTED',
            'medium':   '🔶 MEDIUM RISK — WARNING',
            'high':     '🚨 HIGH RISK — VIOLATION',
            'critical': '🔴 CRITICAL — MAJOR VIOLATION',
        }[level] || '🚨 SUSPICIOUS ACTIVITY';

        const flags = data.flags || {};
        const lastAlarm = data.last_alarm_type || '';
        const msgs = [];

        if (flags.gaze_away || lastAlarm.includes('GAZE'))       msgs.push('Looking away from screen');
        if (flags.head_turn || lastAlarm.includes('HEAD'))       msgs.push('Head turned sideways');
        if (flags.multiple_faces || lastAlarm.includes('MULTI')) msgs.push('Multiple persons detected');
        if (flags.no_face || lastAlarm.includes('NO_FACE'))      msgs.push('No face visible');

        const msgText = msgs.length ? msgs.join(' • ') : 'Suspicious behavior detected by AI proctor';

        document.getElementById('proctor-alarm-title').innerHTML = title;
        document.getElementById('proctor-alarm-msg').textContent  = msgText;

        const riskScoreRaw = data.risk_score ?? data.max_risk_score ?? data.avg_risk_score ?? data.max_risk ?? 0;
        const riskPct = Math.min(100, Math.round(riskScoreRaw));
        document.getElementById('proctor-risk-bar').style.width = riskPct + '%';
        document.getElementById('proctor-risk-label').textContent = `Risk: ${riskPct}%`;

        overlay.style.display = 'block';

        // Update local UI immediately so "Alarms Triggered" box updates
        const alarmsEl = document.getElementById('liveProctorAlarms');
        if (alarmsEl) alarmsEl.textContent = Math.max(parseInt(alarmsEl.textContent || '0'), localTriggeredAlarmsCount);

        // Play alarm sound
        playAlarmSound(level);
    }

    function dismissAlarm() {
        alarmActive = false;
        const overlay = document.getElementById('proctor-alarm-overlay');
        if (overlay) overlay.style.display = 'none';

        // Pause sound if playing
        if (alarmAudio) {
            alarmAudio.pause();
            alarmAudio.currentTime = 0;
        }
    }
    window.PROCTOR_dismissAlarm = dismissAlarm;

    function updateRiskBadge(data) {
        const badge = document.getElementById('proctor-risk-badge');
        if (!badge) return;

        const riskScoreRaw = data.risk_score ?? data.max_risk_score ?? data.avg_risk_score ?? data.max_risk ?? 0;
        const riskPct = Math.round(riskScoreRaw);
        const level   = (data.alarm_level || 'none').toLowerCase();

        const gazeCount   = data.gaze_away_count ?? data.gaze_away ?? data.gaze ?? 0;
        const headCount   = data.head_turn_count ?? data.head_turns ?? data.head_turn ?? 0;
        const noFaceCount = data.no_face_count ?? data.no_face ?? data.no_faces ?? 0;
        const multiCount  = data.multiple_face_count ?? data.multi_face_count ?? data.multiple_faces_count ?? data.multi_face ?? data.multiple_faces ?? 0;
        const blinkCount  = data.blink_count ?? data.total_blinks ?? data.blinks ?? data.blinks_count ?? 0;

        const calculatedAlarms = gazeCount + headCount + noFaceCount + multiCount;
        const alarmsCount = Math.max(data.alarm_count || 0, data.total_alarms || 0, data.total_count || 0, calculatedAlarms, localTriggeredAlarmsCount);

        document.getElementById('proctor-risk-score').textContent = riskPct + '%';

        const dot = document.getElementById('proctor-dot');
        if (dot) {
            const colors = { none: '#10B981', low: '#FBBF24', medium: '#F97316', high: '#EF4444', critical: '#DC2626' };
            dot.style.background = colors[level] || '#10B981';
        }

        // Update Student Live Behavior Modal Elements
        const statusEl = document.getElementById('liveProctorStatus');
        if (statusEl) {
            const levelUpper = level === 'none' ? 'NORMAL' : level.toUpperCase();
            statusEl.textContent = levelUpper;
            statusEl.className = 'badge';
            const badgeClasses = { none: 'badge-green', low: 'badge-amber', medium: 'badge-amber', high: 'badge-red', critical: 'badge-red', calibrating: 'badge-gray' };
            statusEl.classList.add(badgeClasses[level] || 'badge-green');
        }

        const riskEl = document.getElementById('liveProctorRisk');
        if (riskEl) riskEl.textContent = riskPct + '%';

        const alarmsEl = document.getElementById('liveProctorAlarms');
        if (alarmsEl) alarmsEl.textContent = alarmsCount;

        const gazeEl = document.getElementById('liveGazeCount');
        if (gazeEl) gazeEl.textContent = gazeCount;

        const headEl = document.getElementById('liveHeadCount');
        if (headEl) headEl.textContent = headCount;

        const noFaceEl = document.getElementById('liveNoFaceCount');
        if (noFaceEl) noFaceEl.textContent = noFaceCount;

        const multiFaceEl = document.getElementById('liveMultiFaceCount');
        if (multiFaceEl) multiFaceEl.textContent = multiCount;

        const blinkEl = document.getElementById('liveBlinkCount');
        if (blinkEl) blinkEl.textContent = blinkCount;

        // ALSO Update Teacher Live Behavior Modal Elements (if present on Teacher Page)
        const tStatusEl = document.getElementById('teacherModalStatus');
        if (tStatusEl) {
            const levelUpper = level === 'none' ? 'NORMAL' : level.toUpperCase();
            tStatusEl.textContent = levelUpper;
            tStatusEl.className = 'badge';
            const badgeClasses = { none: 'badge-green', low: 'badge-amber', medium: 'badge-amber', high: 'badge-red', critical: 'badge-red', calibrating: 'badge-gray' };
            tStatusEl.classList.add(badgeClasses[level] || 'badge-green');
        }

        const tRiskEl = document.getElementById('teacherModalRisk');
        if (tRiskEl) tRiskEl.textContent = riskPct + '%';

        const tAlarmsEl = document.getElementById('teacherModalAlarms');
        if (tAlarmsEl) tAlarmsEl.textContent = alarmsCount;

        const tGazeEl = document.getElementById('teacherModalGaze');
        if (tGazeEl) tGazeEl.textContent = gazeCount;

        const tHeadEl = document.getElementById('teacherModalHead');
        if (tHeadEl) tHeadEl.textContent = headCount;

        const tNoFaceEl = document.getElementById('teacherModalNoFace');
        if (tNoFaceEl) tNoFaceEl.textContent = noFaceCount;

        const tMultiFaceEl = document.getElementById('teacherModalMultiFace');
        if (tMultiFaceEl) tMultiFaceEl.textContent = multiCount;

        const tBlinkEl = document.getElementById('teacherModalBlink');
        if (tBlinkEl) tBlinkEl.textContent = blinkCount;
    }

    // ── ALARM SOUND ───────────────────────────────────────────────────────
    function playAlarmSound(level) {
        const audioEl = document.getElementById('proctor-alarm-audio');
        if (audioEl) {
            audioEl.volume = level === 'critical' || level === 'high' ? 1.0 : 0.6;
            audioEl.currentTime = 0;
            audioEl.play().catch(() => {
                // User hasn't interacted yet — use Web Audio API beep fallback
                playBeep(level);
            });
        } else {
            playBeep(level);
        }
    }

    function playBeep(level) {
        try {
            const ctx  = new (window.AudioContext || window.webkitAudioContext)();
            const freq  = { critical: 880, high: 660, medium: 440, low: 330 }[level] || 440;
            const osc   = ctx.createOscillator();
            const gain  = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = freq;
            osc.type = 'square';
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.8);
        } catch (e) {
            // Web Audio not available
        }
    }

    // ── STATUS BADGE (camera) ─────────────────────────────────────────────
    function showCameraStatus(msg, isError) {
        const badge = document.getElementById('proctor-risk-badge');
        if (!badge) return;
        if (isError) {
            badge.style.background = 'rgba(239,68,68,0.85)';
            document.getElementById('proctor-dot').style.background = '#fff';
            document.getElementById('proctor-risk-score').textContent = 'OFF';
        }
    }

    // ── HOOK INTO EXISTING doSubmit ───────────────────────────────────────
    function hookSubmit() {
        const origDoSubmit = window.doSubmit;
        if (typeof origDoSubmit === 'function') {
            window.doSubmit = async function () {
                // Stop proctoring BEFORE submitting the quiz
                await stopSession();
                return origDoSubmit.apply(this, arguments);
            };
        }
    }

    // ── BOOT ──────────────────────────────────────────────────────────────
    function boot() {
        buildAlarmOverlay();
        buildRiskBadge();
        hookSubmit();

        // Small delay so page resources settle
        setTimeout(init, 1500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }

})();
