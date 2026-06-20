// lib/constants/api.dart

class ApiConstants {
  static const String baseUrl =
      'https://bgnuf22eight.com/cheating/proctoring-backend/public/api';

  static const String login = '$baseUrl/teacher/login';
  static const String register = '$baseUrl/teacher/register';
  static const String logout = '$baseUrl/teacher/logout';
  static const String dashboard = '$baseUrl/teacher/dashboard';

  static String sessionDetail(int id) => '$baseUrl/exam-sessions/$id';
  static String sessionReport(int id) =>
      '$baseUrl/teacher/sessions/$id/report/view';
}
