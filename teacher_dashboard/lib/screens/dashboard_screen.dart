import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/session.dart';
import '../models/teacher.dart';
import 'report_screen.dart';

class DashboardScreen extends StatefulWidget {
  final String token;
  final Teacher teacher;

  const DashboardScreen({
    super.key,
    required this.token,
    required this.teacher,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<ExamSession> _teacherSessions = [];
  bool _loading = true;
  String? _error;
  Timer? _refreshTimer;
  Timer? _liveUpdateTimer;


  // Keep track of session IDs to prevent duplicates
  final Set<int> _sessionIds = {};

  // Stats (only for teacher's sessions)
  int _totalSessions = 0;
  int _cheatingCount = 0;
  int _suspiciousCount = 0;
  int _cleanCount = 0;
  int _activeSessions = 0;
  int _alarmTriggeredCount = 0;
  double _averageRisk = 0.0;

  // Real-time updates
  final List<String> _recentAlerts = [];

  // Filter
  String? _selectedStatusFilter;
  final List<String> _statusFilters = const [
    'All',
    'active',
    'cheating',
    'suspicious',
    'clean',
    'alarms'
  ];

  @override
  void initState() {
    super.initState();
    _loadAllSessions();
    _startRealTimeUpdates();
  }

  void _startRealTimeUpdates() {
    // Live update every 5 seconds — always runs to detect newly joined students
    _liveUpdateTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (mounted) {
        _updateLiveSessions();
      }
    });

    // Full refresh every 60 seconds to pick up new sessions from DB
    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (timer) {
      if (mounted) {
        _loadAllSessions(showLoading: false);
      }
    });
  }

  // Improved session ownership check with null safety
  bool _isTeacherSession(ExamSession session) {
    try {
      final teacherSubject = widget.teacher.subjectName.trim().toLowerCase();
      final teacherCourseCode = widget.teacher.courseCode.trim().toLowerCase();
      
      final sessionCourse = session.courseName.trim().toLowerCase();
      final sessionBook = session.bookName.trim().toLowerCase();
      final sessionCourseCode = session.courseCode.trim().toLowerCase();

      // Flexible course matching using subject name or course code
      final courseMatch = 
          sessionCourse == teacherSubject || 
          sessionBook == teacherSubject ||
          sessionCourseCode == teacherCourseCode ||
          sessionCourseCode == teacherSubject ||
          sessionCourse.contains(teacherSubject) ||
          teacherSubject.contains(sessionCourse) ||
          sessionBook.contains(teacherSubject) ||
          teacherSubject.contains(sessionBook);

      // Flexible quiz matching (case-insensitive and trimmed)
      // If either the teacher's quizCode or the session's quizCode is empty/null,
      // or if they match, we consider it a match.
      final teacherQuizCode = (widget.teacher.quizCode ?? '').trim().toLowerCase();
      final sessionQuizCode = session.quizCode.trim().toLowerCase();
      
      final quizMatch = teacherQuizCode.isEmpty || 
                        sessionQuizCode.isEmpty || 
                        sessionQuizCode == teacherQuizCode ||
                        sessionQuizCode.contains(teacherQuizCode) ||
                        teacherQuizCode.contains(sessionQuizCode);

      return courseMatch && quizMatch;
    } catch (e) {
      debugPrint('Error in _isTeacherSession: $e');
      return false;
    }
  }

  // Filter sessions that belong to this teacher only
  List<ExamSession> get _filteredTeacherSessions {
    return _teacherSessions;
  }

  // Apply status filter on teacher's sessions
  List<ExamSession> get _displaySessions {
    if (_selectedStatusFilter == null || _selectedStatusFilter == 'All') {
      return _filteredTeacherSessions;
    }
    if (_selectedStatusFilter == 'active') {
      return _filteredTeacherSessions.where((s) => s.isActive).toList();
    }
    if (_selectedStatusFilter == 'alarms') {
      return _filteredTeacherSessions.where((s) => s.hasAlarm).toList();
    }
    return _filteredTeacherSessions
        .where((s) => s.cheatingStatus == _selectedStatusFilter)
        .toList();
  }

  Future<void> _updateLiveSessions() async {
    try {
      final allSessionsData = await ApiService.fetchAllExamSessions(widget.token);

      if (!mounted) return;

      if (allSessionsData.isEmpty) return;

      final allSessions =
          allSessionsData.map((s) => ExamSession.fromJson(s)).toList();

      final Set<int> prevAlarmIds =
          _teacherSessions.where((s) => s.hasAlarm).map((s) => s.id).toSet();

      // Filter sessions belonging to this teacher
      final List<ExamSession> updatedTeacherSessions = [];
      for (var session in allSessions) {
        if (_isTeacherSession(session)) {
          updatedTeacherSessions.add(session);
        }
      }

      setState(() {
        // Show alarm notifications for newly alarmed sessions
        for (final updated in updatedTeacherSessions) {
          if (updated.hasAlarm && !prevAlarmIds.contains(updated.id)) {
            WidgetsBinding.instance.addPostFrameCallback(
                (_) => _showAlarmNotification(updated));
          }
        }
        
        _teacherSessions = updatedTeacherSessions;
        _sessionIds
          ..clear()
          ..addAll(updatedTeacherSessions.map((s) => s.id));
          
        _recalculateStats();
      });
    } catch (e) {
      debugPrint('Live update error: $e');
    }
  }

  void _recalculateStats() {
    _totalSessions = _teacherSessions.length;
    _cheatingCount =
        _teacherSessions.where((s) => s.cheatingStatus == 'cheating').length;
    _suspiciousCount =
        _teacherSessions.where((s) => s.cheatingStatus == 'suspicious').length;
    _cleanCount =
        _teacherSessions.where((s) => s.cheatingStatus == 'clean').length;
    _activeSessions = _teacherSessions.where((s) => s.isActive).length;
    _alarmTriggeredCount = _teacherSessions.where((s) => s.hasAlarm).length;

    if (_teacherSessions.isNotEmpty) {
      _averageRisk =
          _teacherSessions.map((s) => s.avgRiskScore).reduce((a, b) => a + b) /
              _teacherSessions.length;
    } else {
      _averageRisk = 0.0;
    }
  }

  void _showAlarmNotification(ExamSession session) {
    if (!mounted) return;

    // Add to recent alerts (avoid duplicate alerts)
    final alertMessage =
        '⚠️ ALARM: ${session.studentName} - Risk: ${session.avgRiskScore.toInt()}%';
    if (!_recentAlerts.contains(alertMessage)) {
      _recentAlerts.insert(0, alertMessage);
      if (_recentAlerts.length > 5) _recentAlerts.removeLast();
      setState(() {});
    }

    // Show snackbar
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
                  const Text('⚠️ ALARM TRIGGERED!',
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  Text(
                      '${session.studentName} - Risk: ${session.avgRiskScore.toInt()}%'),
                ],
              ),
            ),
          ],
        ),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 5),
        action: SnackBarAction(
          label: 'VIEW',
          textColor: Colors.white,
          onPressed: () {
            if (mounted) {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => ReportScreen(
                    session: session,
                    token: widget.token,
                  ),
                ),
              );
            }
          },
        ),
      ),
    );
  }

  Future<void> _loadAllSessions({bool showLoading = true}) async {
    if (!mounted) return;

    if (showLoading && _teacherSessions.isEmpty) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      final allSessionsData =
          await ApiService.fetchAllExamSessions(widget.token);

      if (!mounted) return;

      if (allSessionsData.isEmpty && _teacherSessions.isNotEmpty) {
        // API returned empty but we have cached data — keep it
        setState(() => _loading = false);
        return;
      }

      final allSessions =
          allSessionsData.map((s) => ExamSession.fromJson(s)).toList();

      // Filter & deduplicate sessions belonging to this teacher
      final uniqueTeacherSessions = <int, ExamSession>{};
      for (var session in allSessions) {
        if (_isTeacherSession(session)) {
          uniqueTeacherSessions[session.id] = session;
        }
      }
      final finalTeacherSessions = uniqueTeacherSessions.values.toList();

      if (finalTeacherSessions.isNotEmpty || _teacherSessions.isEmpty) {
        setState(() {
          _teacherSessions = finalTeacherSessions;
          _sessionIds
            ..clear()
            ..addAll(finalTeacherSessions.map((s) => s.id));
          _recalculateStats();
          _loading = false;
        });
      } else {
        setState(() => _loading = false);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Network error: $e';
          _loading = false;
        });
      }
    }
  }

  void _logout() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext dialogContext) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () {
              if (mounted) {
                Navigator.pop(dialogContext);
              }
            },
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              // Close the dialog
              if (mounted) {
                Navigator.pop(dialogContext);
              }

              try {
                await ApiService.logout(widget.token);
              } catch (e) {
                // Ignore logout errors
              }

              // Cancel timers
              _refreshTimer?.cancel();
              _liveUpdateTimer?.cancel();

              // Navigate to login screen
              if (mounted) {
                Navigator.pushNamedAndRemoveUntil(
                  context,
                  '/login',
                  (route) => false,
                );
              }
            },
            child: const Text('Logout', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _liveUpdateTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      appBar: AppBar(
        titleSpacing: 12,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Flexible(
              child: Text(
                'Proctoring',
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
              ),
            ),
            if (_activeSessions > 0)
              Container(
                margin: const EdgeInsets.only(left: 6),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.red,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'LIVE: $_activeSessions',
                  style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                ),
              ),
          ],
        ),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0.5,
        actions: [
          // Alarm bell
          if (_alarmTriggeredCount > 0)
            Stack(
              alignment: Alignment.center,
              children: [
                IconButton(
                  icon:
                      const Icon(Icons.notifications_active, color: Colors.red, size: 20),
                  onPressed: () {
                    _showAlertsDialog();
                  },
                ),
                Positioned(
                  right: 4,
                  top: 4,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: const BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 14,
                      minHeight: 14,
                    ),
                    child: Text(
                      '$_alarmTriggeredCount',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 8,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              ],
            ),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Center(
              child: Text(
                widget.teacher.name.split(' ').first,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () => _loadAllSessions(),
          ),
          IconButton(
            icon: const Icon(Icons.logout, size: 20),
            onPressed: _logout,
          ),
        ],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFF1D9E75)))
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline,
                          size: 48, color: Colors.red),
                      const SizedBox(height: 16),
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: () => _loadAllSessions(),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1D9E75),
                        ),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: () => _loadAllSessions(),
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        _buildWelcomeCard(),
                        const SizedBox(height: 20),

                        // Live Alerts Banner
                        if (_recentAlerts.isNotEmpty) _buildAlertsBanner(),
                        if (_recentAlerts.isNotEmpty)
                          const SizedBox(height: 20),

                        _buildStatsGrid(),
                        const SizedBox(height: 20),
                        _buildAverageRiskCard(),
                        const SizedBox(height: 20),
                        if (_activeSessions > 0) _buildActiveSessionsSection(),
                        if (_activeSessions > 0) const SizedBox(height: 20),
                        _buildSessionsHeader(),
                        const SizedBox(height: 12),
                        if (_displaySessions.isEmpty)
                          _buildEmptyState()
                        else
                          ListView.builder(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: _displaySessions.length,
                            itemBuilder: (context, index) {
                              final session = _displaySessions[index];
                              return _buildSessionCard(session);
                            },
                          ),
                      ],
                    ),
                  ),
                ),
    );
  }

  Widget _buildAlertsBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.red.shade700, Colors.red.shade500],
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.notifications_active, color: Colors.white),
              SizedBox(width: 8),
              Text('Recent Alerts',
                  style: TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 8),
          ..._recentAlerts.take(3).map((alert) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(alert,
                    style: const TextStyle(color: Colors.white, fontSize: 12)),
              )),
        ],
      ),
    );
  }

  Widget _buildWelcomeCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1D9E75), Color(0xFF0F6B4D)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.school, color: Colors.white, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome, ${widget.teacher.name}!',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.teacher.subjectName,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildInfoChip(
                    Icons.code, 'Course Code', widget.teacher.courseCode),
                _buildInfoChip(Icons.qr_code, 'Quiz Code',
                    widget.teacher.quizCode ?? 'N/A'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoChip(IconData icon, String label, String value) {
    return Column(
      children: [
        Icon(icon, color: Colors.white, size: 20),
        const SizedBox(height: 4),
        Text(label,
            style: const TextStyle(color: Colors.white70, fontSize: 10)),
        Text(value,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildStatsGrid() {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.5,
      children: [
        InkWell(
          onTap: () {
            setState(() {
              _selectedStatusFilter = 'All';
            });
          },
          borderRadius: BorderRadius.circular(12),
          child: _buildStatCard('Total Sessions', _totalSessions.toString(), Colors.blue,
              Icons.assessment),
        ),
        InkWell(
          onTap: () {
            setState(() {
              _selectedStatusFilter = 'active';
            });
          },
          borderRadius: BorderRadius.circular(12),
          child: _buildLiveStatCard('Active', _activeSessions.toString(), Colors.green,
              Icons.play_circle, true),
        ),
        InkWell(
          onTap: () {
            setState(() {
              _selectedStatusFilter = 'cheating';
            });
          },
          borderRadius: BorderRadius.circular(12),
          child: _buildStatCard(
              'Cheating', _cheatingCount.toString(), Colors.red, Icons.warning),
        ),
        InkWell(
          onTap: () {
            setState(() {
              _selectedStatusFilter = 'suspicious';
            });
          },
          borderRadius: BorderRadius.circular(12),
          child: _buildStatCard('Suspicious', _suspiciousCount.toString(), Colors.orange,
              Icons.help),
        ),
        InkWell(
          onTap: () {
            setState(() {
              _selectedStatusFilter = 'clean';
            });
          },
          borderRadius: BorderRadius.circular(12),
          child: _buildStatCard(
              'Clean', _cleanCount.toString(), Colors.green, Icons.check_circle),
        ),
        InkWell(
          onTap: () {
            setState(() {
              _selectedStatusFilter = 'alarms';
            });
          },
          borderRadius: BorderRadius.circular(12),
          child: _buildStatCard('Alarms', _alarmTriggeredCount.toString(), Colors.red,
              Icons.notifications_active),
        ),
      ],
    );
  }

  Widget _buildLiveStatCard(
      String title, String value, Color color, IconData icon, bool isLive) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: isLive && _activeSessions > 0
            ? Border.all(color: Colors.green, width: 2)
            : null,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Stack(
              children: [
                Icon(icon, color: color, size: 24),
                if (isLive && _activeSessions > 0)
                  Positioned(
                    right: 0,
                    top: 0,
                    child: Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: Colors.green,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(title,
                    style: TextStyle(color: Colors.grey[600], fontSize: 11)),
                Row(
                  children: [
                    Text(value,
                        style: const TextStyle(
                            fontSize: 20, fontWeight: FontWeight.bold)),
                    if (isLive && _activeSessions > 0)
                      Container(
                        margin: const EdgeInsets.only(left: 6),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 4, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.green,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text('LIVE',
                            style: TextStyle(color: Colors.white, fontSize: 8)),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(
      String title, String value, Color color, IconData icon) {
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
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(title,
                    style: TextStyle(color: Colors.grey[600], fontSize: 11)),
                Text(value,
                    style: const TextStyle(
                        fontSize: 20, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAverageRiskCard() {
    Color riskColor = _getRiskColor(_averageRisk);
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
          const Text('Average Risk Score',
              style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 8),
          Row(
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 500),
                child: Text(
                  _averageRisk.toStringAsFixed(1),
                  key: ValueKey(_averageRisk),
                  style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: riskColor),
                ),
              ),
              const Text('/100', style: TextStyle(color: Colors.grey)),
              const SizedBox(width: 12),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (_averageRisk / 100).clamp(0, 1),
                    minHeight: 10,
                    backgroundColor: Colors.grey[200],
                    valueColor: AlwaysStoppedAnimation<Color>(riskColor),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildActiveSessionsSection() {
    final activeSessions = _teacherSessions.where((s) => s.isActive).toList();
    if (activeSessions.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.live_tv, color: Colors.blue, size: 20),
              SizedBox(width: 8),
              Text('LIVE EXAM SESSIONS',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
            ],
          ),
          const SizedBox(height: 12),
          ...activeSessions.map((session) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _buildLiveSessionCard(session),
              )),
        ],
      ),
    );
  }

  Widget _buildLiveSessionCard(ExamSession session) {
    return InkWell(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ReportScreen(
              session: session,
              token: widget.token,
            ),
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: session.hasAlarm ? Colors.red.shade400 : Colors.green.shade200,
            width: session.hasAlarm ? 1.5 : 1,
          ),
        ),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Colors.green,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Row(
                    children: [
                      Text(session.studentName,
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                      if (session.hasAlarm) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                          decoration: BoxDecoration(
                            color: Colors.red,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text('ALARM RINGING',
                              style: TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.red,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Text('LIVE',
                      style: TextStyle(color: Colors.white, fontSize: 10)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildLiveRiskIndicator(session.avgRiskScore),
                const SizedBox(width: 12),
                _buildLiveMetric(
                    Icons.remove_red_eye, session.totalBlinks.toString()),
                const SizedBox(width: 12),
                if (session.hasAlarm)
                  _buildLiveMetric(
                      Icons.notifications_active, session.alarmCount.toString(),
                      color: Colors.red),
                const Spacer(),
                Text(session.courseCode,
                    style: TextStyle(fontSize: 11, color: Colors.grey[600])),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLiveRiskIndicator(double risk) {
    Color color = _getRiskColor(risk);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.analytics, size: 12, color: color),
          const SizedBox(width: 4),
          Text('${risk.toInt()}%',
              style: TextStyle(
                  fontSize: 11, color: color, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildLiveMetric(IconData icon, String value,
      {Color color = Colors.blue}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 2),
          Text(value, style: TextStyle(fontSize: 10, color: color)),
        ],
      ),
    );
  }

  Widget _buildSessionsHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text('Exam Sessions (${_displaySessions.length})',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        DropdownButton<String>(
          value: _selectedStatusFilter,
          hint: const Text('Filter'),
          items: _statusFilters.map((filter) {
            return DropdownMenuItem(
              value: filter,
              child: Text(filter),
            );
          }).toList(),
          onChanged: (value) {
            setState(() {
              _selectedStatusFilter = value;
            });
          },
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.all(32),
      alignment: Alignment.center,
      child: Column(
        children: [
          const Icon(Icons.inbox, size: 64, color: Colors.grey),
          const SizedBox(height: 16),
          const Text('No sessions found for your course',
              style: TextStyle(color: Colors.grey, fontSize: 16)),
          const SizedBox(height: 8),
          Text('Course: ${widget.teacher.subjectName}',
              style: TextStyle(color: Colors.grey[500], fontSize: 12)),
          Text('Quiz Code: ${widget.teacher.quizCode ?? 'N/A'}',
              style: TextStyle(color: Colors.grey[500], fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildSessionCard(ExamSession session) {
    final statusColor = session.statusColor;
    final statusLabel = session.statusLabel;
    final statusIcon = session.statusIcon;
    final isActive = session.isActive;
    final hasAlarm = session.hasAlarm;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: hasAlarm ? Border.all(color: Colors.red.shade400, width: 1.5) : null,
        boxShadow: [
          BoxShadow(
            color: hasAlarm ? Colors.red.withOpacity(0.08) : Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ReportScreen(
                  session: session,
                  token: widget.token,
                ),
              ),
            );
          },
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              children: [
                Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(statusIcon, color: statusColor, size: 22),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(session.studentName,
                                  style: const TextStyle(
                                      fontSize: 15, fontWeight: FontWeight.bold)),
                              if (hasAlarm) ...[
                                const SizedBox(width: 8),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.red,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.warning, color: Colors.white, size: 10),
                                      SizedBox(width: 2),
                                      Text('ALARM RINGING', style: TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.bold)),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ),
                          Text('${session.studentId}  •  ${session.courseCode}',
                              style: TextStyle(
                                  fontSize: 11, color: Colors.grey[600])),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(statusLabel,
                          style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: statusColor)),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    _buildStatChip(Icons.analytics,
                        '${session.avgRiskScore.toInt()}%', session.riskColor),
                    const SizedBox(width: 8),
                    _buildStatChip(Icons.remove_red_eye,
                        session.totalBlinks.toString(), Colors.blue),
                    const SizedBox(width: 8),
                    if (hasAlarm)
                      _buildStatChip(Icons.notifications_active,
                          session.alarmCount.toString(), Colors.red),
                    const Spacer(),
                    if (isActive)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.green,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.circle, color: Colors.white, size: 8),
                            SizedBox(width: 4),
                            Text('LIVE',
                                style: TextStyle(
                                    color: Colors.white, fontSize: 9)),
                          ],
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatChip(IconData icon, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(label,
              style: TextStyle(
                  fontSize: 11, color: color, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  void _showAlertsDialog() {
    final alarmedSessions = _teacherSessions.where((s) => s.hasAlarm).toList();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.notifications_active, color: Colors.red),
            SizedBox(width: 10),
            Text('Alarm Details',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          ],
        ),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: alarmedSessions.length,
            itemBuilder: (context, index) {
              final session = alarmedSessions[index];
              return ListTile(
                leading: const Icon(Icons.alarm, color: Colors.red),
                title: Text(session.studentName),
                subtitle: Text(
                    'Risk: ${session.avgRiskScore.toInt()}% • ${session.courseCode}'),
                trailing: Text('${session.alarmCount} alarms',
                    style: const TextStyle(color: Colors.red)),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ReportScreen(
                        session: session,
                        token: widget.token,
                      ),
                    ),
                  );
                },
              );
            },
          ),
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

  Color _getRiskColor(double risk) {
    if (risk >= 70) return Colors.red;
    if (risk >= 40) return Colors.orange;
    return Colors.green;
  }
}
