// lib/screens/report_screen.dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../models/session.dart';
import '../services/api_service.dart';

class ReportScreen extends StatefulWidget {
  final ExamSession session;
  final String token;

  const ReportScreen({
    super.key,
    required this.session,
    required this.token,
  });

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  double _avgRisk = 0;
  double _maxRisk = 0;
  int _totalBlinks = 0;
  int _gazeAway = 0;
  int _headTurns = 0;
  int _noFace = 0;
  int _multiFace = 0;
  int _alarmCount = 0;
  bool _alarmTriggered = false;
  List<dynamic> _alarmHistory = [];
  String _status = 'completed';
  String? _reportContent;
  bool _loading = true;
  String _lastUpdated = '';
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadFromSession(widget.session);
    _loadReport();
    if (widget.session.status == 'active') {
      _refreshTimer =
          Timer.periodic(const Duration(seconds: 5), (_) => _silentRefresh());
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _loadFromSession(ExamSession s) {
    _avgRisk = s.avgRiskScore;
    _maxRisk = s.maxRiskScore;
    _totalBlinks = s.totalBlinks;
    _gazeAway = s.gazeAwayCount;
    _headTurns = s.headTurnCount;
    _noFace = s.noFaceCount;
    _multiFace = s.multipleFaceCount;
    _status = s.status;
    _alarmCount = s.alarmCount ?? 0;
    _alarmTriggered = s.alarmTriggered ?? false;
    _alarmHistory = s.alarmHistory ?? [];
  }

  Future<void> _loadReport() async {
    if (!mounted) return;

    setState(() {
      _loading = true;
    });

    try {
      final sessionData =
          await ApiService.getSession(widget.token, widget.session.id);
      final data = sessionData['data'] ?? sessionData;

      if (!mounted) return;

      setState(() {
        _avgRisk =
            double.tryParse(data['avg_risk_score']?.toString() ?? '0') ?? 0;
        _maxRisk =
            double.tryParse(data['max_risk_score']?.toString() ?? '0') ?? 0;
        _totalBlinks =
            int.tryParse(data['total_blinks']?.toString() ?? '0') ?? 0;
        _gazeAway =
            int.tryParse(data['gaze_away_count']?.toString() ?? '0') ?? 0;
        _headTurns =
            int.tryParse(data['head_turn_count']?.toString() ?? '0') ?? 0;
        _noFace = int.tryParse(data['no_face_count']?.toString() ?? '0') ?? 0;
        _multiFace =
            int.tryParse(data['multiple_face_count']?.toString() ?? '0') ?? 0;
        _status = data['status']?.toString() ?? 'completed';
        _alarmCount = int.tryParse(data['alarm_count']?.toString() ?? '0') ?? 0;
        _alarmTriggered = data['alarm_triggered'] == true ||
            data['alarm_triggered'] == 1 ||
            data['alarm_triggered'] == '1';
        final historyVal = data['alarm_history'];
        if (historyVal is List) {
          _alarmHistory = historyVal;
        } else if (historyVal is String) {
          try {
            final decoded = jsonDecode(historyVal);
            _alarmHistory = decoded is List ? decoded : [];
          } catch (_) {
            _alarmHistory = [];
          }
        } else {
          _alarmHistory = [];
        }
        _lastUpdated = _getCurrentTime();
        _loading = false;
      });

      try {
        final reportData =
            await ApiService.getReport(widget.token, widget.session.id);
        if (mounted && reportData['report_content'] != null) {
          setState(() {
            _reportContent = reportData['report_content'].toString();
          });
        }
      } catch (e) {
        debugPrint('Report content not available: $e');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadFromSession(widget.session);
          _loading = false;
        });
      }
    }
  }

  Future<void> _silentRefresh() async {
    if (!mounted) return;

    try {
      final sessionData =
          await ApiService.getSession(widget.token, widget.session.id);
      final data = sessionData['data'] ?? sessionData;

      if (mounted) {
        setState(() {
          _avgRisk =
              double.tryParse(data['avg_risk_score']?.toString() ?? '0') ?? 0;
          _maxRisk =
              double.tryParse(data['max_risk_score']?.toString() ?? '0') ?? 0;
          _totalBlinks =
              int.tryParse(data['total_blinks']?.toString() ?? '0') ?? 0;
          _gazeAway =
              int.tryParse(data['gaze_away_count']?.toString() ?? '0') ?? 0;
          _headTurns =
              int.tryParse(data['head_turn_count']?.toString() ?? '0') ?? 0;
          _noFace = int.tryParse(data['no_face_count']?.toString() ?? '0') ?? 0;
          _multiFace =
              int.tryParse(data['multiple_face_count']?.toString() ?? '0') ?? 0;
          _status = data['status']?.toString() ?? 'completed';
          _alarmCount =
              int.tryParse(data['alarm_count']?.toString() ?? '0') ?? 0;
          _alarmTriggered = data['alarm_triggered'] == true ||
              data['alarm_triggered'] == 1 ||
              data['alarm_triggered'] == '1';
          final historyVal = data['alarm_history'];
          if (historyVal is List) {
            _alarmHistory = historyVal;
          } else if (historyVal is String) {
            try {
              final decoded = jsonDecode(historyVal);
              _alarmHistory = decoded is List ? decoded : [];
            } catch (_) {
              _alarmHistory = [];
            }
          } else {
            _alarmHistory = [];
          }
          _lastUpdated = _getCurrentTime();
        });
      }

      // Fetch report content via API if status changes or we need to update it
      try {
        final reportData =
            await ApiService.getReport(widget.token, widget.session.id);
        if (mounted && reportData['report_content'] != null) {
          setState(() {
            _reportContent = reportData['report_content'].toString();
          });
        }
      } catch (e) {
        debugPrint('Silent refresh report content load error: $e');
      }

      // If session is no longer active and we have successfully retrieved report content, cancel the timer
      if (_status != 'active' && _reportContent != null) {
        _refreshTimer?.cancel();
      }
    } catch (e) {
      debugPrint('Refresh error: $e');
    }
  }

  String _getCurrentTime() {
    final now = DateTime.now();
    return '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}';
  }

  bool get _isLive => _status == 'active';

  Color _riskColor(double v) {
    if (v >= 70) return const Color(0xFFE24B4A);
    if (v >= 40) return const Color(0xFFEF9F27);
    return const Color(0xFF639922);
  }

  String _riskLabel(double v) {
    if (v >= 70) return 'HIGH RISK';
    if (v >= 40) return 'MEDIUM RISK';
    return 'LOW RISK';
  }

  Color get _statusColor {
    if (_alarmCount >= 5) return const Color(0xFFE24B4A);
    if (_alarmCount >= 3) return const Color(0xFFEF9F27);
    if (_avgRisk >= 70) return const Color(0xFFE24B4A);
    if (_avgRisk >= 40) return const Color(0xFFEF9F27);
    return const Color(0xFF639922);
  }

  String get _statusLabel {
    if (_alarmCount >= 5) return 'CHEATING DETECTED';
    if (_alarmCount >= 3) return 'SUSPICIOUS';
    if (_avgRisk >= 70) return 'CHEATING DETECTED';
    if (_avgRisk >= 40) return 'SUSPICIOUS';
    return 'CLEAN';
  }

  IconData get _verdictIcon {
    if (_alarmCount >= 5) return Icons.warning_rounded;
    if (_alarmCount >= 3) return Icons.help_rounded;
    if (_avgRisk >= 70) return Icons.warning_rounded;
    if (_avgRisk >= 40) return Icons.help_rounded;
    return Icons.check_circle_rounded;
  }

  String _getSeverityIcon(String severity) {
    switch (severity.toLowerCase()) {
      case 'high':
        return '🔴';
      case 'medium':
        return '🟠';
      case 'low':
        return '🟡';
      default:
        return '⚪';
    }
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.amber;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.session;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(s.studentName,
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text('${s.studentId}  •  ${s.courseCode}',
                style: TextStyle(fontSize: 12, color: Colors.grey[600])),
          ],
        ),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0.5,
        actions: [
          if (_lastUpdated.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Center(
                child: Text('Updated $_lastUpdated',
                    style: TextStyle(fontSize: 10, color: Colors.grey[500])),
              ),
            ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadReport),
        ],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF1D9E75)))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(children: [
                if (_isLive)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.red[50],
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.red),
                    ),
                    child: const Row(children: [
                      Icon(Icons.circle, color: Colors.red, size: 10),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text('LIVE EXAM — auto-updating every 5 seconds',
                            style: TextStyle(
                                color: Colors.red,
                                fontSize: 13,
                                fontWeight: FontWeight.w500)),
                      ),
                    ]),
                  ),
                if (_alarmTriggered)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFE24B4A), Color(0xFFC0392B)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.red.withOpacity(0.3),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(Icons.notifications_active,
                            color: Colors.white, size: 24),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('🚨 ALARM ACTIVE / RINGING',
                                style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 15,
                                    fontWeight: FontWeight.bold,
                                    letterSpacing: 0.5)),
                            Text(
                              _alarmCount > 0
                                  ? 'Student has triggered $_alarmCount violation alarm(s)!'
                                  : 'Active rules violations detected for this student!',
                              style: TextStyle(
                                  color: Colors.white.withOpacity(0.9),
                                  fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      if (_alarmCount > 0)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text('$_alarmCount',
                              style: const TextStyle(
                                  color: Color(0xFFE24B4A),
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold)),
                        ),
                    ]),
                  ),
                Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.06),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: _statusColor.withOpacity(0.1),
                        borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(16)),
                        border: Border(
                            bottom: BorderSide(
                                color: _statusColor.withOpacity(0.3))),
                      ),
                      child: Row(children: [
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: _statusColor.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child:
                              Icon(_verdictIcon, color: _statusColor, size: 28),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Final Verdict',
                                  style: TextStyle(
                                      color: Colors.grey[600], fontSize: 12)),
                              Text(_statusLabel,
                                  style: TextStyle(
                                      color: _statusColor,
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                        if (_isLive)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: Colors.red,
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: const Row(children: [
                              Icon(Icons.circle, color: Colors.white, size: 8),
                              SizedBox(width: 4),
                              Text('LIVE',
                                  style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold)),
                            ]),
                          ),
                      ]),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildSectionTitle('Student Information'),
                          const SizedBox(height: 12),
                          _buildInfoRow('Student Name', s.studentName),
                          _buildInfoRow('Student ID', s.studentId.toString()),
                          _buildInfoRow('Course Code', s.courseCode),
                          _buildInfoRow('Course Name', s.courseName),
                          _buildInfoRow('Quiz Code', s.quizCode),
                          _buildInfoRow('Exam Date', s.examDate),
                          _buildInfoRow('Start Time', s.startTime),
                          _buildInfoRow(
                              'End Time',
                              _isLive
                                  ? 'In progress...'
                                  : (s.endTime ?? 'N/A')),
                          _buildInfoRow(
                              'Status', _isLive ? 'LIVE EXAM' : 'Completed'),
                          const SizedBox(height: 20),
                          const Divider(),
                          const SizedBox(height: 12),
                          _buildSectionTitle('Risk Analysis'),
                          const SizedBox(height: 14),
                          _buildRiskContainer('Average Risk Score', _avgRisk),
                          const SizedBox(height: 12),
                          _buildRiskContainer('Peak Risk Score', _maxRisk),
                          const SizedBox(height: 20),
                          const Divider(),
                          const SizedBox(height: 12),
                          if (_alarmHistory.isNotEmpty) ...[
                            _buildSectionTitle('Alarm / Violation Details'),
                            const SizedBox(height: 14),
                            _buildAlarmSection(),
                            const SizedBox(height: 20),
                            const Divider(),
                            const SizedBox(height: 12),
                          ],
                          _buildSectionTitle('Behavior Statistics'),
                          const SizedBox(height: 14),
                          _buildStatRow(Icons.remove_red_eye, 'Total Blinks',
                              '$_totalBlinks', Colors.blue),
                          _buildStatRow(Icons.visibility_off, 'Gaze Away',
                              '$_gazeAway times', Colors.orange),
                          _buildStatRow(Icons.rotate_left, 'Head Turns',
                              '$_headTurns times', Colors.purple),
                          _buildStatRow(
                              Icons.face_retouching_off,
                              'No Face Detected',
                              '$_noFace frames',
                              Colors.red),
                          _buildStatRow(Icons.group, 'Multiple Faces',
                              '$_multiFace frames', Colors.red),
                          if (_reportContent != null &&
                              _reportContent!.isNotEmpty) ...[
                            const SizedBox(height: 20),
                            const Divider(),
                            const SizedBox(height: 12),
                            _buildSectionTitle('Detailed Report'),
                            const SizedBox(height: 12),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF5F5F5),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: Colors.grey[300]!),
                              ),
                              child: Text(_reportContent!,
                                  style: const TextStyle(
                                      fontFamily: 'monospace',
                                      fontSize: 11,
                                      height: 1.5)),
                            ),
                          ] else if (_isLive) ...[
                            const SizedBox(height: 20),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: Colors.orange[50],
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: Colors.orange[200]!),
                              ),
                              child: const Row(children: [
                                Icon(Icons.info_outline,
                                    color: Colors.orange, size: 18),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                      'Report file will be available after exam ends.',
                                      style: TextStyle(
                                          color: Colors.orange, fontSize: 13)),
                                ),
                              ]),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ]),
                ),
                const SizedBox(height: 24),
              ]),
            ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(title,
        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold));
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
          Text(value,
              style:
                  const TextStyle(fontWeight: FontWeight.w500, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildRiskContainer(String label, double value) {
    final color = _riskColor(value);
    final risk = _riskLabel(value);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label,
                  style: TextStyle(color: Colors.grey[700], fontSize: 13)),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(risk,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(
                  value: (value / 100).clamp(0, 1),
                  minHeight: 12,
                  backgroundColor: Colors.grey[200],
                  valueColor: AlwaysStoppedAnimation<Color>(color),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Text(value.toStringAsFixed(1),
                style: TextStyle(
                    color: color, fontSize: 22, fontWeight: FontWeight.bold)),
            Text('/100',
                style: TextStyle(color: Colors.grey[500], fontSize: 12)),
          ]),
        ],
      ),
    );
  }

  Widget _buildAlarmSection() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.alarm, color: Colors.red, size: 20),
              const SizedBox(width: 8),
              Text('Total Alarms: $_alarmCount',
                  style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.red)),
            ],
          ),
          const SizedBox(height: 12),
          const Text('Alarm History:',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ..._alarmHistory.map((alarm) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  children: [
                    Text(_getSeverityIcon(alarm['severity'] ?? 'low'),
                        style: const TextStyle(fontSize: 16)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              alarm['type']?.toString().toUpperCase() ??
                                  'Unknown',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w600, fontSize: 13)),
                          Text(
                              alarm['timestamp']?.toString().substring(0, 19) ??
                                  '',
                              style: TextStyle(
                                  fontSize: 10, color: Colors.grey[600])),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: _getSeverityColor(alarm['severity'] ?? 'low')
                            .withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                          alarm['severity']?.toString().toUpperCase() ?? 'LOW',
                          style: TextStyle(
                              fontSize: 10,
                              color:
                                  _getSeverityColor(alarm['severity'] ?? 'low'),
                              fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildStatRow(IconData icon, String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Container(
          padding: const EdgeInsets.all(7),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, size: 16, color: color),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(label,
              style: TextStyle(color: Colors.grey[700], fontSize: 13)),
        ),
        Text(value,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
      ]),
    );
  }
}
