// lib/models/teacher.dart
class Teacher {
  final int id;
  final String name;
  final String email;
  final String subjectName;
  final String courseCode;
  final String? quizCode;
  final String? department;
  final String? designation;
  final String? phone;
  final DateTime? lastLoginAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  Teacher({
    required this.id,
    required this.name,
    required this.email,
    required this.subjectName,
    required this.courseCode,
    this.quizCode,
    this.department,
    this.designation,
    this.phone,
    this.lastLoginAt,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Teacher.fromJson(Map<String, dynamic> json) {
    // Helper function to safely convert to int
    int toInt(dynamic value) {
      if (value == null) return 0;
      if (value is int) return value;
      if (value is String) return int.tryParse(value) ?? 0;
      return 0;
    }

    // Helper function to safely convert to String
    String toStringValue(dynamic value) {
      if (value == null) return '';
      return value.toString();
    }

    return Teacher(
      id: toInt(json['id']),
      name: toStringValue(json['name']),
      email: toStringValue(json['email']),
      subjectName: toStringValue(json['subject_name']),
      courseCode: toStringValue(json['course_code']),
      quizCode: toStringValue(json['quiz_code']),
      department: toStringValue(json['department']),
      designation: toStringValue(json['designation']),
      phone: toStringValue(json['phone']),
      lastLoginAt: json['last_login_at'] != null
          ? DateTime.tryParse(toStringValue(json['last_login_at']))
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(toStringValue(json['created_at'])) ??
              DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(toStringValue(json['updated_at'])) ??
              DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'subject_name': subjectName,
      'course_code': courseCode,
      'quiz_code': quizCode,
      'department': department,
      'designation': designation,
      'phone': phone,
      'last_login_at': lastLoginAt?.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
