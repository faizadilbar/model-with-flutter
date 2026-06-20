// lib/screens/live_monitor_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import '../models/session.dart';
import '../models/alarm.dart';
import '../services/api_service.dart';

class LiveMonitorScreen extends StatefulWidget {
  final ExamSession session;
  final String token;
  final Alarm? initialAlarm;

  const LiveMonitorScreen({
    super.key,
    required this.session,
    required this.token,
    this.initialAlarm,
  });

  @override
  State<LiveMonitorScreen> createState() => _LiveMonitorScreenState();
}

class _LiveMonitorScreenState extends State<LiveMonitorScreen> {
  Timer? _refreshTimer;
  Map<String, dynamic> _liveData = {};
  bool _loading = true;
  final List<Alarm> _recentAlarms = [];
  String _lastUpdated = '';

  @override
  void initState() {
    super.initState();
    _loadLiveData();
    _startLiveRefresh();
    if (widget.initialAlarm != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _showAlarmNotification(widget.initialAlarm!);
      });
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startLiveRefresh() {
    _refreshTimer = Timer.periodic(const Duration(seconds: 3), (timer) {
      _loadLiveData();
    });
  }

  Future<void> _loadLiveData() async {
    try {
      final data = await ApiService.getSession(widget.token, widget.session.id);
      if (mounted) {
        setState(() {
          _liveData = data['data'] ?? data;
          _loading = false;
          _lastUpdated = _getCurrentTime();
        });

        // Check for new alarms
        final alarmsData = _liveData['alarms'] as List?;
        if (alarmsData != null) {
          for (var alarmData in alarmsData) {
            final alarm = Alarm.fromJson(alarmData);
            if (!_recentAlarms.any((a) => a.id == alarm.id)) {
              setState(() {
                _recentAlarms.add(alarm);
              });
              _showAlarmNotification(alarm);
            }
          }
        }
      }
    } catch (e) {
      debugPrint('Live refresh error: $e');
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  String _getCurrentTime() {
    final now = DateTime.now();
    return '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}';
  }

  void _showAlarmNotification(Alarm alarm) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.notifications_active, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    '⚠️ ALARM TRIGGERED!',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text(
                    '${alarm.type.toUpperCase()} - ${alarm.studentName}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
        backgroundColor: alarm.severity == 'high' ? Colors.red : Colors.orange,
        duration: const Duration(seconds: 5),
        action: SnackBarAction(
          label: 'VIEW',
          textColor: Colors.white,
          onPressed: () {
            _showAlarmDetails(alarm);
          },
        ),
      ),
    );
  }

  void _showAlarmDetails(Alarm alarm) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Icon(Icons.alarm,
                color: alarm.severity == 'high' ? Colors.red : Colors.orange),
            const SizedBox(width: 10),
            const Text('Alarm Details'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildDetailRow('Student', alarm.studentName),
            const SizedBox(height: 8),
            _buildDetailRow('Type', alarm.type.toUpperCase()),
            const SizedBox(height: 8),
            _buildDetailRow('Severity', alarm.severity.toUpperCase()),
            const SizedBox(height: 8),
            _buildDetailRow('Time', alarm.timestamp),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Risk Score:',
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  Text(
                    '${alarm.riskScore.toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: alarm.riskScore >= 70 ? Colors.red : Colors.orange,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
        Text(value, style: const TextStyle(color: Colors.grey)),
      ],
    );
  }

  void _showAlarmsList() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Container(
          width: double.maxFinite,
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.notifications_active, color: Colors.red),
                  SizedBox(width: 10),
                  Text('Alarm History',
                      style:
                          TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 20),
              if (_recentAlarms.isEmpty)
                const Center(
                  child: Text('No alarms triggered yet',
                      style: TextStyle(color: Colors.grey)),
                )
              else
                Flexible(
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: _recentAlarms.length,
                    itemBuilder: (context, index) {
                      final alarm = _recentAlarms[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: alarm.severity == 'high'
                                ? Colors.red.withOpacity(0.2)
                                : Colors.orange.withOpacity(0.2),
                            child: Icon(Icons.alarm,
                                color: alarm.severity == 'high'
                                    ? Colors.red
                                    : Colors.orange),
                          ),
                          title: Text(alarm.type.toUpperCase(),
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                  '${alarm.studentName} • ${alarm.courseName}'),
                              const SizedBox(height: 4),
                              Text(alarm.timestamp,
                                  style: const TextStyle(fontSize: 11)),
                            ],
                          ),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: alarm.severity == 'high'
                                  ? Colors.red.withOpacity(0.2)
                                  : Colors.orange.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              '${alarm.riskScore.toStringAsFixed(0)}%',
                              style: TextStyle(
                                color: alarm.severity == 'high'
                                    ? Colors.red
                                    : Colors.orange,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ),
                          onTap: () {
                            Navigator.pop(context);
                            _showAlarmDetails(alarm);
                          },
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: Colors.green,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.green.withOpacity(0.5),
                    blurRadius: 4,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('LIVE MONITORING',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  Text(
                    widget.session.studentName,
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0.5,
        actions: [
          if (_recentAlarms.isNotEmpty)
            Stack(
              children: [
                IconButton(
                  icon:
                      const Icon(Icons.notifications_active, color: Colors.red),
                  onPressed: _showAlarmsList,
                ),
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(3),
                    decoration: const BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 18,
                      minHeight: 18,
                    ),
                    child: Text(
                      '${_recentAlarms.length}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              ],
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadLiveData,
          ),
        ],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF1D9E75)))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // Live indicator
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Colors.green.shade50, Colors.green.shade100],
                      ),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.green.shade300),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.animation, color: Colors.green),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'LIVE MONITORING ACTIVE',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 12),
                              ),
                              Text(
                                'Auto-refreshing every 3 seconds • Last updated: $_lastUpdated',
                                style: TextStyle(
                                    fontSize: 10, color: Colors.grey[600]),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Current Risk Score
                  _buildRiskCard(),

                  const SizedBox(height: 16),

                  // Statistics Cards
                  _buildStatisticsGrid(),

                  const SizedBox(height: 16),

                  // Recent Alarms
                  if (_recentAlarms.isNotEmpty) _buildRecentAlarms(),

                  const SizedBox(height: 16),

                  // Behavior Metrics
                  _buildBehaviorMetrics(),
                ],
              ),
            ),
    );
  }

  Widget _buildRiskCard() {
    final avgRisk = (_liveData['avg_risk_score'] ?? 0).toDouble();
    final maxRisk = (_liveData['max_risk_score'] ?? 0).toDouble();
    final riskColor = avgRisk >= 70
        ? Colors.red
        : (avgRisk >= 40 ? Colors.orange : Colors.green);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [riskColor.withOpacity(0.1), riskColor.withOpacity(0.05)],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: riskColor.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Current Risk Score',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: riskColor,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  avgRisk >= 70
                      ? 'HIGH RISK'
                      : (avgRisk >= 40 ? 'MEDIUM RISK' : 'LOW RISK'),
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(avgRisk.toStringAsFixed(1),
                        style: TextStyle(
                            fontSize: 48,
                            fontWeight: FontWeight.bold,
                            color: riskColor)),
                    const Text('/100', style: TextStyle(color: Colors.grey)),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Peak Risk',
                        style: TextStyle(color: Colors.grey)),
                    Text(maxRisk.toStringAsFixed(1),
                        style: const TextStyle(
                            fontSize: 24, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: (avgRisk / 100).clamp(0, 1),
              minHeight: 10,
              backgroundColor: Colors.grey[200],
              valueColor: AlwaysStoppedAnimation<Color>(riskColor),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatisticsGrid() {
    final totalBlinks = (_liveData['total_blinks'] ?? 0).toInt();
    final gazeAway = (_liveData['gaze_away_count'] ?? 0).toInt();
    final headTurns = (_liveData['head_turn_count'] ?? 0).toInt();
    final noFace = (_liveData['no_face_count'] ?? 0).toInt();
    final multiFace = (_liveData['multiple_face_count'] ?? 0).toInt();

    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.2,
      children: [
        _buildMetricCard(
            'Total Blinks', '$totalBlinks', Icons.remove_red_eye, Colors.blue),
        _buildMetricCard(
            'Gaze Away', '$gazeAway', Icons.visibility_off, Colors.orange),
        _buildMetricCard(
            'Head Turns', '$headTurns', Icons.rotate_left, Colors.purple),
        _buildMetricCard(
            'No Face', '$noFace', Icons.face_retouching_off, Colors.red),
        _buildMetricCard(
            'Multiple Faces', '$multiFace', Icons.group, Colors.red),
      ],
    );
  }

  Widget _buildMetricCard(
      String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(height: 8),
          Text(value,
              style:
                  const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          Text(title,
              style: TextStyle(color: Colors.grey[600], fontSize: 11),
              textAlign: TextAlign.center),
        ],
      ),
    );
  }

  Widget _buildRecentAlarms() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.notifications_active, color: Colors.red),
              SizedBox(width: 8),
              Text('Recent Alarms',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          ..._recentAlarms.reversed.take(3).map((alarm) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: alarm.severity == 'high'
                        ? Colors.red.shade50
                        : Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.alarm,
                          color: alarm.severity == 'high'
                              ? Colors.red
                              : Colors.orange),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(alarm.type.toUpperCase(),
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold)),
                            Text(alarm.timestamp,
                                style: TextStyle(
                                    fontSize: 11, color: Colors.grey[600])),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: alarm.severity == 'high'
                              ? Colors.red.withOpacity(0.2)
                              : Colors.orange.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${alarm.riskScore.toStringAsFixed(0)}%',
                          style: TextStyle(
                            color: alarm.severity == 'high'
                                ? Colors.red
                                : Colors.orange,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              )),
          if (_recentAlarms.length > 3)
            TextButton(
              onPressed: _showAlarmsList,
              child: const Text('View All Alarms'),
            ),
        ],
      ),
    );
  }

  Widget _buildBehaviorMetrics() {
    final frameCount = (_liveData['frame_count'] ?? 0).toInt();
    final confidenceScore = (_liveData['confidence_score'] ?? 100).toDouble();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Additional Metrics',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildInfoRow('Frames Processed', frameCount.toString()),
              ),
              Expanded(
                child: _buildInfoRow(
                    'Confidence', '${confidenceScore.toStringAsFixed(1)}%'),
              ),
            ],
          ),
          if (_liveData['status'] != null) const SizedBox(height: 8),
          if (_liveData['status'] != null)
            _buildInfoRow('Session Status', _liveData['status']),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 12)),
          Text(value,
              style:
                  const TextStyle(fontWeight: FontWeight.w500, fontSize: 12)),
        ],
      ),
    );
  }
}
