import 'dart:convert';
import 'dart:developer';
import 'package:http/http.dart' as http;

class ApiService {
  static const String _baseUrl =
      'https://bgnuf22eight.com/cheating/proctoring-backend/public/api';

  // Teacher Login
  static Future<Map<String, dynamic>> login(
      String email, String password) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/teacher/login'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'email': email,
              'password': password,
            }),
          )
          .timeout(const Duration(seconds: 30));

      if (response.body.isNotEmpty) {
        return jsonDecode(response.body);
      }
      return {'success': false, 'message': 'Empty response from server'};
    } catch (e) {
      return {'success': false, 'message': 'Connection error: $e'};
    }
  }

  // Teacher Register
  static Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    required String passwordConfirmation,
    required String subjectName,
    required String quizCode,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/teacher/register'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'name': name,
              'email': email,
              'password': password,
              'password_confirmation': passwordConfirmation,
              'subject_name': subjectName,
              'quiz_code': quizCode,
            }),
          )
          .timeout(const Duration(seconds: 30));

      if (response.body.isNotEmpty) {
        return jsonDecode(response.body);
      }
      return {'success': false, 'message': 'Empty response from server'};
    } catch (e) {
      return {'success': false, 'message': 'Connection error: $e'};
    }
  }

  // Get All Exam Sessions (with pagination support)
  static Future<Map<String, dynamic>> getAllExamSessions(String token,
      {int page = 1, int perPage = 100}) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/exam-sessions?page=$page&per_page=$perPage'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 30));

      log('Exam Sessions Response Status: ${response.statusCode}');

      if (response.statusCode == 200 && response.body.isNotEmpty) {
        return jsonDecode(response.body);
      }
      return {
        'success': false,
        'message': 'Failed to load sessions',
        'data': []
      };
    } catch (e) {
      log('Error loading sessions: $e');
      return {'success': false, 'message': 'Connection error: $e', 'data': []};
    }
  }

  // Get All Exam Sessions (fetch all sessions in a single robust request)
  static Future<List<Map<String, dynamic>>> fetchAllExamSessions(
      String token) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/exam-sessions?page=1&per_page=200'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 15));

      log('Fetch Sessions Response Status: ${response.statusCode}');

      if (response.statusCode == 200 && response.body.isNotEmpty) {
        final data = jsonDecode(response.body);
        List sessions = [];

        if (data is Map && data.containsKey('data') && data['data'] is List) {
          sessions = data['data'];
        } else if (data is List) {
          sessions = data;
        } else if (data is Map) {
          sessions = data.values.toList();
        }

        return sessions.map((s) => Map<String, dynamic>.from(s)).toList();
      }
    } catch (e) {
      log('Error fetching sessions: $e');
    }
    return [];
  }

  // Get Teacher Dashboard
  static Future<Map<String, dynamic>> getTeacherDashboard(String token) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/teacher/dashboard'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 30));

      log('Dashboard Response Status: ${response.statusCode}');

      if (response.statusCode == 200 && response.body.isNotEmpty) {
        return jsonDecode(response.body);
      }
      return {'success': false, 'message': 'Failed to load dashboard'};
    } catch (e) {
      log('Dashboard error: $e');
      return {'success': false, 'message': 'Connection error: $e'};
    }
  }

  // Get Single Session
  static Future<Map<String, dynamic>> getSession(
      String token, int sessionId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/exam-sessions/$sessionId'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 30));

      if (response.body.isNotEmpty && response.body.trim().startsWith('{')) {
        return jsonDecode(response.body);
      }
      return {'success': false, 'message': 'Invalid response format'};
    } catch (e) {
      return {'success': false, 'message': 'Connection error: $e'};
    }
  }

  // Get Session Report
  static Future<Map<String, dynamic>> getReport(
      String token, int sessionId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/exam-sessions/$sessionId/report'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 30));

      if (response.body.isNotEmpty && response.body.trim().startsWith('{')) {
        return jsonDecode(response.body);
      }
      return {'success': false, 'report_content': null};
    } catch (e) {
      return {'success': false, 'report_content': null};
    }
  }

  // Logout
  static Future<Map<String, dynamic>> logout(String token) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/logout'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      ).timeout(const Duration(seconds: 30));

      if (response.body.isNotEmpty) {
        return jsonDecode(response.body);
      }
      return {'success': true};
    } catch (e) {
      return {'success': true};
    }
  }
}
