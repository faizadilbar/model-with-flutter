import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'screens/dashboard_screen.dart';
import 'models/teacher.dart';

void main() {
  runApp(const TeacherPortalApp());
}

class TeacherPortalApp extends StatelessWidget {
  const TeacherPortalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Teacher Portal',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.teal,
        visualDensity: VisualDensity.adaptivePlatformDensity,
        fontFamily: 'Segoe UI',
      ),
      initialRoute: '/login',
      routes: {
        '/login': (context) => const LoginScreen(),
        '/dashboard': (context) => const DashboardScreenWrapper(),
      },
    );
  }
}

// Wrapper for DashboardScreen to receive data
class DashboardScreenWrapper extends StatelessWidget {
  const DashboardScreenWrapper({super.key});

  @override
  Widget build(BuildContext context) {
    final args = ModalRoute.of(context)?.settings.arguments;
    if (args != null && args is Map<String, dynamic>) {
      return DashboardScreen(
        token: args['token'],
        teacher: args['teacher'],
      );
    }
    // Fallback - should not happen
    return const Scaffold(
      body: Center(child: Text('Error: No user data found')),
    );
  }
}

// ==================== LOGIN SCREEN ====================
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  String _statusMessage = '';
  bool _isSuccess = false;

  static const String _loginUrl =
      'https://bgnuf22eight.com/cheating/proctoring-backend/public/api/teacher/login';

  Future<void> _loginTeacher() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _statusMessage = '';
      _isSuccess = false;
    });

    final Map<String, String> payload = {
      'email': _emailController.text.trim(),
      'password': _passwordController.text,
    };

    try {
      final response = await http
          .post(
            Uri.parse(_loginUrl),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 15));

      final Map<String, dynamic> responseData;
      if (response.body.isNotEmpty) {
        responseData = jsonDecode(response.body);
      } else {
        responseData = {};
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        // Extract token and teacher data
        String token = '';
        Map<String, dynamic> teacherData = {};

        // Handle different response formats
        if (responseData.containsKey('token')) {
          token = responseData['token'];
        } else if (responseData.containsKey('data') &&
            responseData['data'].containsKey('token')) {
          token = responseData['data']['token'];
        } else if (responseData.containsKey('access_token')) {
          token = responseData['access_token'];
        }

        // Get teacher data
        if (responseData.containsKey('teacher')) {
          teacherData = responseData['teacher'];
        } else if (responseData.containsKey('data') &&
            responseData['data'].containsKey('teacher')) {
          teacherData = responseData['data']['teacher'];
        } else if (responseData.containsKey('user')) {
          teacherData = responseData['user'];
        }

        // If no teacher data in response, create minimal teacher object
        if (teacherData.isEmpty) {
          teacherData = {
            'id': 1,
            'name': _emailController.text.trim().split('@').first,
            'email': _emailController.text.trim(),
            'subject_name': 'General',
            'course_code': 'GEN101',
          };
        }

        final teacher = Teacher.fromJson(teacherData);

        setState(() {
          _isLoading = false;
          _statusMessage = '✅ Login successful!';
          _isSuccess = true;
        });

        // Navigate to dashboard
        if (mounted && token.isNotEmpty) {
          // Show success message
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Login successful! Redirecting...'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 1),
            ),
          );

          // Navigate to dashboard after a short delay
          Future.delayed(const Duration(milliseconds: 500), () {
            if (mounted) {
              Navigator.pushReplacementNamed(
                context,
                '/dashboard',
                arguments: {
                  'token': token,
                  'teacher': teacher,
                },
              );
            }
          });
        } else {
          setState(() {
            _statusMessage = '❌ No token received from server';
            _isSuccess = false;
          });
        }
      } else {
        String errorMsg = 'Login failed';
        if (responseData.containsKey('message')) {
          errorMsg = responseData['message'];
        } else if (responseData.containsKey('errors')) {
          final errors = responseData['errors'] as Map<String, dynamic>;
          final firstError = errors.values.first;
          if (firstError is List && firstError.isNotEmpty) {
            errorMsg = firstError.first;
          } else {
            errorMsg = errors.toString();
          }
        }

        setState(() {
          _isLoading = false;
          _statusMessage = '❌ $errorMsg';
          _isSuccess = false;
        });
      }
    } catch (e) {
      String errorMsg = _getErrorMessage(e);
      setState(() {
        _isLoading = false;
        _statusMessage = errorMsg;
        _isSuccess = false;
      });
    }
  }

  String _getErrorMessage(dynamic e) {
    if (e.toString().contains('TimeoutException')) {
      return '⏰ Request timeout. Please check your connection.';
    } else if (e.toString().contains('SocketException')) {
      return '🌐 Network error: Unable to connect to the server.';
    }
    return '⚠️ Error: ${e.toString()}';
  }

  String? _validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Please enter your email';
    }
    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    if (!emailRegex.hasMatch(value.trim())) {
      return 'Enter a valid email';
    }
    return null;
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter your password';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.teal.shade50,
              Colors.blue.shade50,
              Colors.grey.shade100
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Card(
                elevation: 8,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(32)),
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Header
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: const BoxDecoration(
                          color: Colors.teal,
                          borderRadius: BorderRadius.only(
                            topLeft: Radius.circular(32),
                            topRight: Radius.circular(32),
                          ),
                        ),
                        child: const Column(
                          children: [
                            Icon(Icons.person, size: 50, color: Colors.white),
                            SizedBox(height: 12),
                            Text(
                              'Teacher Login',
                              style: TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white),
                            ),
                            SizedBox(height: 6),
                            Text(
                              'Access your proctoring dashboard',
                              style: TextStyle(
                                  fontSize: 14, color: Colors.white70),
                            ),
                          ],
                        ),
                      ),

                      // Form Body
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              // Email
                              TextFormField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                decoration: InputDecoration(
                                  labelText: 'Email Address',
                                  hintText: 'teacher@gmail.com',
                                  prefixIcon: const Icon(Icons.email_outlined),
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16)),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide:
                                        BorderSide(color: Colors.grey.shade300),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide: const BorderSide(
                                        color: Colors.teal, width: 2),
                                  ),
                                ),
                                validator: _validateEmail,
                              ),
                              const SizedBox(height: 16),

                              // Password
                              TextFormField(
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                decoration: InputDecoration(
                                  labelText: 'Password',
                                  hintText: '••••••••',
                                  prefixIcon: const Icon(Icons.lock_outline),
                                  suffixIcon: IconButton(
                                    icon: Icon(_obscurePassword
                                        ? Icons.visibility_off
                                        : Icons.visibility),
                                    onPressed: () => setState(() =>
                                        _obscurePassword = !_obscurePassword),
                                  ),
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16)),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide:
                                        BorderSide(color: Colors.grey.shade300),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide: const BorderSide(
                                        color: Colors.teal, width: 2),
                                  ),
                                ),
                                validator: _validatePassword,
                              ),
                              const SizedBox(height: 24),

                              // Login Button
                              SizedBox(
                                width: double.infinity,
                                height: 52,
                                child: ElevatedButton(
                                  onPressed: _isLoading ? null : _loginTeacher,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.teal.shade700,
                                    shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(28)),
                                    elevation: 3,
                                  ),
                                  child: _isLoading
                                      ? const SizedBox(
                                          height: 20,
                                          width: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            valueColor:
                                                AlwaysStoppedAnimation<Color>(
                                                    Colors.white),
                                          ),
                                        )
                                      : const Text('Login',
                                          style: TextStyle(
                                              fontSize: 16,
                                              fontWeight: FontWeight.bold)),
                                ),
                              ),

                              // Status Message
                              if (_statusMessage.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: _isSuccess
                                        ? Colors.green.shade50
                                        : Colors.red.shade50,
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(
                                        color: _isSuccess
                                            ? Colors.green.shade200
                                            : Colors.red.shade200),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(
                                          _isSuccess
                                              ? Icons.check_circle
                                              : Icons.error_outline,
                                          color: _isSuccess
                                              ? Colors.green
                                              : Colors.red,
                                          size: 20),
                                      const SizedBox(width: 10),
                                      Expanded(
                                          child: Text(_statusMessage,
                                              style: TextStyle(
                                                  color: _isSuccess
                                                      ? Colors.green.shade800
                                                      : Colors.red.shade800,
                                                  fontSize: 13))),
                                    ],
                                  ),
                                ),
                              ],

                              const SizedBox(height: 20),
                              // Register Link
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Text("Don't have an account? "),
                                  TextButton(
                                    onPressed: () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                            builder: (context) =>
                                                const RegistrationScreen()),
                                      );
                                    },
                                    style: TextButton.styleFrom(
                                        foregroundColor: Colors.teal.shade700),
                                    child: const Text('Register Now',
                                        style: TextStyle(
                                            fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ==================== REGISTRATION SCREEN ====================
class RegistrationScreen extends StatefulWidget {
  const RegistrationScreen({super.key});

  @override
  State<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends State<RegistrationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _courseNameController = TextEditingController();
  final _quizCodeController = TextEditingController();

  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  String _statusMessage = '';
  bool _isSuccess = false;

  static const String _registerUrl =
      'https://bgnuf22eight.com/cheating/proctoring-backend/public/api/teacher/register';

  Future<void> _registerTeacher() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
      _statusMessage = '';
      _isSuccess = false;
    });

    final Map<String, String> payload = {
      'name': _nameController.text.trim(),
      'email': _emailController.text.trim(),
      'password': _passwordController.text,
      'password_confirmation': _confirmPasswordController.text,
      'subject_name': _courseNameController.text.trim(),
      'quiz_code': _quizCodeController.text.trim(),
    };

    try {
      final response = await http
          .post(
            Uri.parse(_registerUrl),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 15));

      final Map<String, dynamic> responseData;
      if (response.body.isNotEmpty) {
        responseData = jsonDecode(response.body);
      } else {
        responseData = {};
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        String successMsg = '✅ Registration successful!';
        if (responseData.containsKey('message')) {
          successMsg = '✅ ${responseData['message']}';
        }

        setState(() {
          _isLoading = false;
          _statusMessage = successMsg;
          _isSuccess = true;
        });

        _showSuccessDialog(successMsg);
        _clearForm();

        // Auto navigate back to login after 2 seconds
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            Navigator.pop(context);
          }
        });
      } else {
        String errorMsg = 'Registration failed';
        if (responseData.containsKey('message')) {
          errorMsg = responseData['message'];
        } else if (responseData.containsKey('errors')) {
          final errors = responseData['errors'] as Map<String, dynamic>;
          final firstError = errors.values.first;
          if (firstError is List && firstError.isNotEmpty) {
            errorMsg = firstError.first;
          } else {
            errorMsg = errors.toString();
          }
        }

        setState(() {
          _isLoading = false;
          _statusMessage = '❌ $errorMsg';
          _isSuccess = false;
        });
      }
    } catch (e) {
      String errorMsg = _getErrorMessage(e);
      setState(() {
        _isLoading = false;
        _statusMessage = errorMsg;
        _isSuccess = false;
      });
    }
  }

  String _getErrorMessage(dynamic e) {
    if (e.toString().contains('TimeoutException')) {
      return '⏰ Request timeout. Please check your connection.';
    } else if (e.toString().contains('SocketException')) {
      return '🌐 Network error: Unable to connect to the server.';
    }
    return '⚠️ Error: ${e.toString()}';
  }

  void _showSuccessDialog(String message) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green, size: 28),
              SizedBox(width: 10),
              Text('Registration Success!'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(message),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.teal.shade50,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Registered Info:',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 5),
                    Text('Name: ${_nameController.text}'),
                    Text('Email: ${_emailController.text}'),
                    Text('Course: ${_courseNameController.text}'),
                    Text('Quiz Code: ${_quizCodeController.text}'),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              const Text('Redirecting to login screen...',
                  style: TextStyle(fontSize: 12)),
            ],
          ),
        );
      },
    );
  }

  void _clearForm() {
    _nameController.clear();
    _emailController.clear();
    _passwordController.clear();
    _confirmPasswordController.clear();
    _courseNameController.clear();
    _quizCodeController.clear();
  }

  // Validation methods
  String? _validateName(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Please enter your full name';
    }
    if (value.trim().length < 3) {
      return 'Name must be at least 3 characters';
    }
    return null;
  }

  String? _validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Please enter your email';
    }
    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    if (!emailRegex.hasMatch(value.trim())) {
      return 'Enter a valid email';
    }
    return null;
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter a password';
    }
    if (value.length < 6) {
      return 'Password must be at least 6 characters';
    }
    return null;
  }

  String? _validateConfirmPassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please confirm your password';
    }
    if (value != _passwordController.text) {
      return 'Passwords do not match';
    }
    return null;
  }

  String? _validateCourseName(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Please enter the course name';
    }
    return null;
  }

  String? _validateQuizCode(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Please enter the quiz/exam code';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.teal.shade50,
              Colors.blue.shade50,
              Colors.grey.shade100
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: Card(
                elevation: 8,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(32)),
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 600),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Header
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: const BoxDecoration(
                          color: Colors.teal,
                          borderRadius: BorderRadius.only(
                            topLeft: Radius.circular(32),
                            topRight: Radius.circular(32),
                          ),
                        ),
                        child: const Column(
                          children: [
                            Icon(Icons.school, size: 50, color: Colors.white),
                            SizedBox(height: 12),
                            Text(
                              'Teacher Registration',
                              style: TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white),
                            ),
                            SizedBox(height: 6),
                            Text(
                              'Register for exam supervision & course management',
                              style: TextStyle(
                                  fontSize: 14, color: Colors.white70),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),

                      // Form Body
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              // Full Name
                              TextFormField(
                                controller: _nameController,
                                decoration: InputDecoration(
                                  labelText: 'Full Name',
                                  hintText: 'e.g., Dr. Sarah Johnson',
                                  prefixIcon: const Icon(Icons.person_outline),
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16)),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide:
                                        BorderSide(color: Colors.grey.shade300),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide: const BorderSide(
                                        color: Colors.teal, width: 2),
                                  ),
                                ),
                                validator: _validateName,
                              ),
                              const SizedBox(height: 16),

                              // Email
                              TextFormField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                decoration: InputDecoration(
                                  labelText: 'Email Address',
                                  hintText: 'teacher@institution.edu',
                                  prefixIcon: const Icon(Icons.email_outlined),
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16)),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide:
                                        BorderSide(color: Colors.grey.shade300),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide: const BorderSide(
                                        color: Colors.teal, width: 2),
                                  ),
                                ),
                                validator: _validateEmail,
                              ),
                              const SizedBox(height: 16),

                              // Password Row
                              Row(
                                children: [
                                  Expanded(
                                    child: TextFormField(
                                      controller: _passwordController,
                                      obscureText: _obscurePassword,
                                      decoration: InputDecoration(
                                        labelText: 'Password',
                                        hintText: '••••••••',
                                        prefixIcon:
                                            const Icon(Icons.lock_outline),
                                        suffixIcon: IconButton(
                                          icon: Icon(_obscurePassword
                                              ? Icons.visibility_off
                                              : Icons.visibility),
                                          onPressed: () => setState(() =>
                                              _obscurePassword =
                                                  !_obscurePassword),
                                        ),
                                        border: OutlineInputBorder(
                                            borderRadius:
                                                BorderRadius.circular(16)),
                                        enabledBorder: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(16),
                                          borderSide: BorderSide(
                                              color: Colors.grey.shade300),
                                        ),
                                        focusedBorder: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(16),
                                          borderSide: const BorderSide(
                                              color: Colors.teal, width: 2),
                                        ),
                                      ),
                                      validator: _validatePassword,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextFormField(
                                      controller: _confirmPasswordController,
                                      obscureText: _obscureConfirmPassword,
                                      decoration: InputDecoration(
                                        labelText: 'Confirm',
                                        hintText: '••••••••',
                                        prefixIcon:
                                            const Icon(Icons.lock_outline),
                                        suffixIcon: IconButton(
                                          icon: Icon(_obscureConfirmPassword
                                              ? Icons.visibility_off
                                              : Icons.visibility),
                                          onPressed: () => setState(() =>
                                              _obscureConfirmPassword =
                                                  !_obscureConfirmPassword),
                                        ),
                                        border: OutlineInputBorder(
                                            borderRadius:
                                                BorderRadius.circular(16)),
                                        enabledBorder: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(16),
                                          borderSide: BorderSide(
                                              color: Colors.grey.shade300),
                                        ),
                                        focusedBorder: OutlineInputBorder(
                                          borderRadius:
                                              BorderRadius.circular(16),
                                          borderSide: const BorderSide(
                                              color: Colors.teal, width: 2),
                                        ),
                                      ),
                                      validator: _validateConfirmPassword,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 16),

                              // Course Name (Highlighted)
                              Container(
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: [
                                      Colors.amber.shade50,
                                      Colors.yellow.shade50
                                    ],
                                  ),
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: TextFormField(
                                  controller: _courseNameController,
                                  decoration: InputDecoration(
                                    labelText: 'Course Name',
                                    hintText:
                                        'e.g., Calculus I, Linear Algebra, Physics',
                                    prefixIcon: const Icon(Icons.book_outlined,
                                        color: Colors.amber),
                                    border: OutlineInputBorder(
                                        borderRadius:
                                            BorderRadius.circular(16)),
                                    enabledBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16),
                                      borderSide: BorderSide(
                                          color: Colors.amber.shade300),
                                    ),
                                    focusedBorder: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16),
                                      borderSide: const BorderSide(
                                          color: Colors.amber, width: 2),
                                    ),
                                    helperText:
                                        'The academic course you\'re teaching',
                                    helperStyle: TextStyle(
                                        fontSize: 12,
                                        color: Colors.amber.shade800),
                                  ),
                                  validator: _validateCourseName,
                                ),
                              ),
                              const SizedBox(height: 16),

                              // Quiz Code
                              TextFormField(
                                controller: _quizCodeController,
                                decoration: InputDecoration(
                                  labelText: 'Quiz / Exam Code',
                                  hintText: 'e.g., MATH101, CS50-FINAL',
                                  prefixIcon: const Icon(Icons.qr_code),
                                  border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(16)),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide:
                                        BorderSide(color: Colors.grey.shade300),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(16),
                                    borderSide: const BorderSide(
                                        color: Colors.teal, width: 2),
                                  ),
                                  helperText:
                                      'Unique code for proctoring session',
                                  helperStyle: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey.shade600),
                                ),
                                validator: _validateQuizCode,
                              ),
                              const SizedBox(height: 24),

                              // Register Button
                              SizedBox(
                                width: double.infinity,
                                height: 52,
                                child: ElevatedButton(
                                  onPressed:
                                      _isLoading ? null : _registerTeacher,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.teal.shade700,
                                    shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(28)),
                                    elevation: 3,
                                  ),
                                  child: _isLoading
                                      ? const SizedBox(
                                          height: 20,
                                          width: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            valueColor:
                                                AlwaysStoppedAnimation<Color>(
                                                    Colors.white),
                                          ),
                                        )
                                      : const Text('Register',
                                          style: TextStyle(
                                              fontSize: 16,
                                              fontWeight: FontWeight.bold)),
                                ),
                              ),

                              // Status Message
                              if (_statusMessage.isNotEmpty) ...[
                                const SizedBox(height: 16),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: _isSuccess
                                        ? Colors.green.shade50
                                        : Colors.red.shade50,
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(
                                        color: _isSuccess
                                            ? Colors.green.shade200
                                            : Colors.red.shade200),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(
                                          _isSuccess
                                              ? Icons.check_circle
                                              : Icons.error_outline,
                                          color: _isSuccess
                                              ? Colors.green
                                              : Colors.red,
                                          size: 20),
                                      const SizedBox(width: 10),
                                      Expanded(
                                          child: Text(_statusMessage,
                                              style: TextStyle(
                                                  color: _isSuccess
                                                      ? Colors.green.shade800
                                                      : Colors.red.shade800,
                                                  fontSize: 13))),
                                    ],
                                  ),
                                ),
                              ],

                              const SizedBox(height: 20),
                              // Login Link
                              Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Text("Already have an account? "),
                                  TextButton(
                                    onPressed: () {
                                      Navigator.pop(context);
                                    },
                                    style: TextButton.styleFrom(
                                        foregroundColor: Colors.teal.shade700),
                                    child: const Text('Login Here',
                                        style: TextStyle(
                                            fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
