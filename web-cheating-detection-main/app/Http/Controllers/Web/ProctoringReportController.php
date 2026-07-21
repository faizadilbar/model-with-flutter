<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class ProctoringReportController extends Controller
{
    private string $reportApi = 'https://bgnuf22eight.com/cheating/proctoring-backend/public/api';

    private array $curlOpts = [
        'force_ip_resolve' => 'v4',
        'verify'           => false,
    ];

    /**
     * GET /api/exam-sessions/aggregated
     * Aggregates metrics across all sessions for a specific student and quiz_code.
     * Prevents metric erasure on quiz re-entry and returns the consolidated max result.
     */
    public function getCumulativeReport(Request $request)
    {
        $studentId = $request->query('student_id');
        $quizCode  = $request->query('quiz_code');

        if (!$studentId || !$quizCode) {
            return response()->json([
                'status'  => false,
                'message' => 'student_id and quiz_code query parameters are required'
            ], 400);
        }

        try {
            $res = Http::withOptions($this->curlOpts)
                ->timeout(15)
                ->withHeaders(['Accept' => 'application/json'])
                ->get("{$this->reportApi}/exam-sessions");

            $data     = $res->json();
            $sessions = $data['data'] ?? $data['sessions'] ?? $data ?? [];

            // Filter sessions for this student and quiz_code
            $matchingSessions = array_filter($sessions, function ($s) use ($studentId, $quizCode) {
                $codeMatch = strcasecmp((string)($s['quiz_code'] ?? ''), $quizCode) === 0;
                $idMatch   = strcasecmp((string)($s['student_id'] ?? ''), $studentId) === 0 ||
                             strcasecmp((string)($s['student_name'] ?? ''), $studentId) === 0;
                return $codeMatch && $idMatch;
            });

            if (empty($matchingSessions)) {
                return response()->json([
                    'status'  => false,
                    'message' => 'No session data found for specified student and quiz'
                ], 44);
            }

            // Cumulative Counters & Maximum Risk Score Selection
            $totalHeadTurns = 0;
            $totalGazeAways = 0;
            $totalNoFace    = 0;
            $totalMultiFace = 0;
            $totalBlinks    = 0;
            $maxRiskScore   = 0.0;
            $totalAvgRisk   = 0.0;
            $maxLevel       = 'NONE';

            $levelPriority = ['CRITICAL' => 4, 'HIGH' => 3, 'MEDIUM' => 2, 'LOW' => 1, 'NONE' => 0];

            foreach ($matchingSessions as $s) {
                $totalHeadTurns += (int)($s['head_turn_count'] ?? 0);
                $totalGazeAways += (int)($s['gaze_away_count'] ?? 0);
                $totalNoFace    += (int)($s['no_face_count'] ?? 0);
                $totalMultiFace += (int)($s['multiple_face_count'] ?? 0);
                $totalBlinks    += (int)($s['blink_count'] ?? $s['total_blinks'] ?? 0);

                $risk = (float)($s['max_risk_score'] ?? $s['risk_score'] ?? $s['avg_risk_score'] ?? 0.0);
                if ($risk > $maxRiskScore) {
                    $maxRiskScore = $risk;
                }

                $lvl = strtoupper($s['alarm_level'] ?? 'NONE');
                if (($levelPriority[$lvl] ?? 0) > ($levelPriority[$maxLevel] ?? 0)) {
                    $maxLevel = $lvl;
                }

                $totalAvgRisk += (float)($s['avg_risk_score'] ?? $s['risk_score'] ?? 0.0);
            }

            $count = count($matchingSessions);
            $latest = end($matchingSessions);

            return response()->json([
                'status' => true,
                'data'   => [
                    'session_id'          => $latest['id'] ?? $latest['session_id'] ?? null,
                    'student_id'          => $studentId,
                    'student_name'        => $latest['student_name'] ?? 'Student',
                    'quiz_code'           => $quizCode,
                    'head_turn_count'     => $totalHeadTurns,
                    'gaze_away_count'     => $totalGazeAways,
                    'no_face_count'       => $totalNoFace,
                    'multiple_face_count' => $totalMultiFace,
                    'total_blinks'        => $totalBlinks,
                    'max_risk_score'      => round($maxRiskScore),
                    'alarm_level'         => $maxLevel,
                    'avg_risk_score'      => round($totalAvgRisk / $count, 2),
                    'total_attempts_cnt'  => $count
                ]
            ]);
        } catch (\Exception $e) {
            Log::error('ProctoringReportController getCumulativeReport error: ' . $e->getMessage());
            return response()->json([
                'status'  => false,
                'message' => 'Error aggregating session report: ' . $e->getMessage()
            ], 500);
        }
    }
}
