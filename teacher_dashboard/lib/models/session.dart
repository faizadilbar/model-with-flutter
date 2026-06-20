// lib/models/session.dart
import 'dart:convert';
import 'package:flutter/material.dart';

class ExamSession {
  final int id;
  final int studentId;
  final String studentName;
  final String studentEmail;
  final String courseCode;
  final String courseName;
  final String bookName;
  final String quizCode;
  final String examDate;
  final String startTime;
  final String? endTime;
  final String status;
  final double avgRiskScore;
  final double maxRiskScore;
  final int totalBlinks;
  final int gazeAwayCount;
  final int headTurnCount;
  final int noFaceCount;
  final int multipleFaceCount;
  final String _cheatingStatus;

  String get cheatingStatus {
    final count = alarmCount ?? 0;
    if (count >= 5) return 'cheating';
    if (count >= 3) return 'suspicious';
    return _cheatingStatus;
  }
  final int? alarmCount;
  final bool? alarmTriggered;
  final List<dynamic>? alarmHistory;
  final DateTime createdAt;
  final DateTime updatedAt;

  ExamSession({
    required this.id,
    required this.studentId,
    required this.studentName,
    required this.studentEmail,
    required this.courseCode,
    required this.courseName,
    required this.bookName,
    required this.quizCode,
    required this.examDate,
    required this.startTime,
    this.endTime,
    required this.status,
    required this.avgRiskScore,
    required this.maxRiskScore,
    required this.totalBlinks,
    required this.gazeAwayCount,
    required this.headTurnCount,
    required this.noFaceCount,
    required this.multipleFaceCount,
    required String cheatingStatus,
    this.alarmCount,
    this.alarmTriggered,
    this.alarmHistory,
    required this.createdAt,
    required this.updatedAt,
  }) : _cheatingStatus = cheatingStatus;

  factory ExamSession.fromJson(Map<String, dynamic> json) {
    // Helper function to safely convert to int
    int toInt(dynamic value) {
      if (value == null) return 0;
      if (value is int) return value;
      if (value is String) return int.tryParse(value) ?? 0;
      if (value is double) return value.toInt();
      return 0;
    }

    // Helper function to safely convert to double
    double toDouble(dynamic value) {
      if (value == null) return 0.0;
      if (value is double) return value;
      if (value is int) return value.toDouble();
      if (value is String) return double.tryParse(value) ?? 0.0;
      return 0.0;
    }

    // Helper function to safely convert to String
    String toStringValue(dynamic value) {
      if (value == null) return '';
      return value.toString();
    }

    // Helper function to parse DateTime timezone-safely (UTC fallback)
    DateTime parseDateTime(dynamic value) {
      if (value == null) return DateTime.now();
      final str = toStringValue(value);
      if (str.isEmpty) return DateTime.now();
      
      String formatted = str;
      if (!formatted.endsWith('Z') && !formatted.contains('+') && !formatted.contains('-')) {
        formatted = formatted.replaceAll(' ', 'T');
        if (!formatted.contains('T')) {
          formatted += 'T00:00:00';
        }
        formatted += 'Z';
      }
      return DateTime.tryParse(formatted) ?? DateTime.now();
    }

    List<dynamic>? parseAlarmHistory(dynamic val) {
      if (val == null) return null;
      if (val is List) return val;
      if (val is String) {
        try {
          final decoded = jsonDecode(val);
          if (decoded is List) return decoded;
        } catch (_) {}
      }
      return null;
    }

    return ExamSession(
      id: toInt(json['id']),
      studentId: toInt(json['student_id']),
      studentName: toStringValue(json['student_name']),
      studentEmail: toStringValue(json['student_email']),
      courseCode: toStringValue(json['course_code']),
      courseName: toStringValue(json['course_name']),
      bookName: toStringValue(json['book_name'] ?? json['subject_name']),
      quizCode: toStringValue(json['quiz_code']),
      examDate: toStringValue(json['exam_date']),
      startTime: toStringValue(json['start_time']),
      endTime: toStringValue(json['end_time']),
      status: toStringValue(json['status']),
      avgRiskScore: toDouble(json['avg_risk_score']),
      maxRiskScore: toDouble(json['max_risk_score']),
      totalBlinks: toInt(json['total_blinks']),
      gazeAwayCount: toInt(json['gaze_away_count']),
      headTurnCount: toInt(json['head_turn_count']),
      noFaceCount: toInt(json['no_face_count']),
      multipleFaceCount: toInt(json['multiple_face_count']),
      cheatingStatus: toStringValue(json['cheating_status']),
      alarmCount:
          json['alarm_count'] != null ? toInt(json['alarm_count']) : null,
      alarmTriggered: json['alarm_triggered'] == true ||
          json['alarm_triggered'] == 1 ||
          json['alarm_triggered'] == '1',
      alarmHistory: parseAlarmHistory(json['alarm_history']),
      createdAt: parseDateTime(json['created_at']),
      updatedAt: parseDateTime(json['updated_at']),
    );
  }

  bool get isActive {
    if (status != 'active' && status != 'live') return false;
    if (endTime != null &&
        endTime!.isNotEmpty &&
        endTime != 'null' &&
        endTime != '0000-00-00 00:00:00') {
      return false;
    }

    // A session is considered active only if it has been updated in the last 60 seconds.
    // If the student stops recording/sending data, the session is no longer active.
    final difference = DateTime.now().toUtc().difference(updatedAt.toUtc()).abs();
    if (difference.inSeconds > 60) {
      return false;
    }

    return true;
  }
  bool get hasAlarm => alarmTriggered == true || (alarmCount ?? 0) > 0;

  Color get statusColor {
    if (cheatingStatus == 'cheating') return Colors.red;
    if (cheatingStatus == 'suspicious') return Colors.orange;
    return Colors.green;
  }

  String get statusLabel {
    if (cheatingStatus == 'cheating') return 'CHEATING';
    if (cheatingStatus == 'suspicious') return 'SUSPICIOUS';
    return 'CLEAN';
  }

  IconData get statusIcon {
    if (cheatingStatus == 'cheating') return Icons.warning;
    if (cheatingStatus == 'suspicious') return Icons.help;
    return Icons.check_circle;
  }

  Color get riskColor {
    if (avgRiskScore >= 70) return Colors.red;
    if (avgRiskScore >= 40) return Colors.orange;
    return Colors.green;
  }
}
