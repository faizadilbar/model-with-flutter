<?php

use App\Http\Controllers\Web\AuthController;
use App\Http\Controllers\Web\AdminController;
use App\Http\Controllers\Web\TeacherController;
use App\Http\Controllers\Web\StudentController;
use App\Http\Controllers\Api\ApiProxyController;
use App\Http\Controllers\Web\ProctorController;
use Illuminate\Support\Facades\Route;

// ─── AUTH ───────────────────────────────────────────────────────────
Route::get('/', function () { return view('welcome'); })->name('home.landing');
Route::get('/login',  [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login'])->name('login.post');
Route::post('/logout',[AuthController::class, 'logout'])->name('logout');

// ─── ADMIN ──────────────────────────────────────────────────────────
Route::prefix('admin')->name('admin.')->middleware('role:admin')->group(function () {
    Route::get('/dashboard',                    [AdminController::class, 'dashboard'])->name('dashboard');
    Route::get('/teachers',                     [AdminController::class, 'teachers'])->name('teachers');
    Route::post('/teachers',                    [AdminController::class, 'addTeacher'])->name('teachers.add');
    Route::get('/students',                     [AdminController::class, 'students'])->name('students');
    Route::post('/students',                    [AdminController::class, 'addStudent'])->name('students.add');
    Route::get('/courses',                      [AdminController::class, 'courses'])->name('courses');
    Route::post('/courses/add',                 [AdminController::class, 'addCourse'])->name('courses.add');
    Route::post('/courses/assign-teacher',      [AdminController::class, 'assignTeacher'])->name('courses.assign-teacher');
    Route::post('/courses/remove-teacher',      [AdminController::class, 'removeTeacher'])->name('courses.remove-teacher');
    Route::get('/students/{id}/courses',        [AdminController::class, 'studentCourses'])->name('student.courses');
    Route::post('/students/assign-course',      [AdminController::class, 'assignCourse'])->name('student.assign-course');
    Route::post('/students/remove-course',      [AdminController::class, 'removeCourse'])->name('student.remove-course');
});

use App\Http\Controllers\Web\ProctoringReportController;

// ─── TEACHER ────────────────────────────────────────────────────────
Route::prefix('teacher')->name('teacher.')->middleware('role:teacher')->group(function () {
    Route::get('/dashboard',                    [TeacherController::class, 'dashboard'])->name('dashboard');
    Route::get('/courses/{courseId}/quizzes',   [TeacherController::class, 'courseQuizzes'])->name('course.quizzes');
    Route::get('/quiz/create/{courseId}',       [TeacherController::class, 'createQuiz'])->name('quiz.create');
    Route::post('/quiz/generate-ai',            [TeacherController::class, 'generateAI'])->name('quiz.generate-ai');
    Route::get('/quiz/generation-status/{id}',  [TeacherController::class, 'generationStatus'])->name('quiz.generation-status');
    Route::post('/quiz/save',                   [TeacherController::class, 'saveQuiz'])->name('quiz.save');
    Route::get('/quiz/{code}/monitor',          [TeacherController::class, 'monitorQuiz'])->name('quiz.monitor');
    Route::get('/quiz/{code}/attempts-json',    [TeacherController::class, 'monitorAttemptsJson'])->name('quiz.attempts-json');
    Route::post('/quiz/unlock-attempt',         [TeacherController::class, 'unlockAttempt'])->name('quiz.unlock');
    Route::get('/quiz/{code}/view',             [TeacherController::class, 'viewQuiz'])->name('quiz.view');
    Route::get('/past-quizzes',                 [TeacherController::class, 'pastQuizzes'])->name('past-quizzes');
    Route::get('/past-quiz/{code}/questions',   [TeacherController::class, 'pastQuizQuestions'])->name('past-quiz.questions');
    // ─── PROCTORING REPORTS (Teacher) ───────────────────────
    Route::get('/proctor/reports',          [ProctorController::class, 'reports'])->name('proctor.reports');
    Route::get('/proctor/reports/{id}',     [ProctorController::class, 'reportDetail'])->name('proctor.report-detail');
    Route::get('/proctor/aggregated',       [ProctoringReportController::class, 'getCumulativeReport'])->name('proctor.aggregated');
});

// ─── STUDENT ────────────────────────────────────────────────────────
Route::prefix('student')->name('student.')->middleware('role:student')->group(function () {
    Route::get('/dashboard',                    [StudentController::class, 'dashboard'])->name('dashboard');
    Route::get('/courses/{courseId}',           [StudentController::class, 'courseDetail'])->name('course.detail');
    Route::get('/quiz/enter',                   [StudentController::class, 'enterQuiz'])->name('quiz.enter');
    Route::post('/quiz/confirm',                [StudentController::class, 'confirmQuiz'])->name('quiz.confirm');
    Route::post('/quiz/start',                  [StudentController::class, 'startQuiz'])->name('quiz.start');
    Route::get('/quiz/{quizId}/take',           [StudentController::class, 'takeQuiz'])->name('quiz.take');
    Route::post('/quiz/submit',                 [StudentController::class, 'submitQuiz'])->name('quiz.submit');
    Route::post('/quiz/heartbeat',              [StudentController::class, 'heartbeat'])->name('quiz.heartbeat');
    Route::post('/quiz/tab-switch',             [StudentController::class, 'tabSwitch'])->name('quiz.tab-switch');
    Route::post('/quiz/screen-close',           [StudentController::class, 'screenClose'])->name('quiz.screen-close');
    Route::post('/quiz/mark-submitted',         [StudentController::class, 'markSubmitted'])->name('quiz.mark-submitted');
    Route::get('/results',                      [StudentController::class, 'results'])->name('results');
    Route::get('/results/{quizId}',             [StudentController::class, 'resultDetail'])->name('result.detail');
    Route::post('/quiz/clear-lock',             [StudentController::class, 'clearLock'])->name('quiz.clear-lock');

    // ─── PROCTORING (Student) ────────────────────────────────
    Route::post('/proctor/start',   [ProctorController::class, 'startExam'])->name('proctor.start');
    Route::post('/proctor/frame',   [ProctorController::class, 'uploadFrame'])->name('proctor.frame');
    Route::get('/proctor/metrics',  [ProctorController::class, 'metrics'])->name('proctor.metrics');
    Route::post('/proctor/stop',    [ProctorController::class, 'stopExam'])->name('proctor.stop');
});
