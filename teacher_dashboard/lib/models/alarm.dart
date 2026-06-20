// lib/models/alarm.dart
class Alarm {
  final int id;
  final int sessionId;
  final String studentName;
  final String studentId;
  final String courseCode;
  final String courseName;
  final String type;
  final String severity;
  final String timestamp;
  final double riskScore;
  final Map<String, dynamic> details;

  Alarm({
    required this.id,
    required this.sessionId,
    required this.studentName,
    required this.studentId,
    required this.courseCode,
    required this.courseName,
    required this.type,
    required this.severity,
    required this.timestamp,
    required this.riskScore,
    required this.details,
  });

  factory Alarm.fromJson(Map<String, dynamic> json) {
    return Alarm(
      id: json['id'] ?? 0,
      sessionId: json['session_id'] ?? 0,
      studentName: json['student_name']?.toString() ?? '',
      studentId: json['student_id']?.toString() ?? '',
      courseCode: json['course_code']?.toString() ?? '',
      courseName: json['course_name']?.toString() ?? '',
      type: json['type']?.toString() ?? 'unknown',
      severity: json['severity']?.toString() ?? 'low',
      timestamp: json['timestamp']?.toString() ?? '',
      riskScore: (json['risk_score'] ?? 0).toDouble(),
      details: json['details'] as Map<String, dynamic>? ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'session_id': sessionId,
      'student_name': studentName,
      'student_id': studentId,
      'course_code': courseCode,
      'course_name': courseName,
      'type': type,
      'severity': severity,
      'timestamp': timestamp,
      'risk_score': riskScore,
      'details': details,
    };
  }
}
