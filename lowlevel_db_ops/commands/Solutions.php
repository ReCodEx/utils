<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Solutions extends BaseCommand
{
    /*
     * Public interface
     */

    public function allSolutionsInCSV($env)
    {
        $cols = [ 'id', 'assignment_id', 'author_id', 'group_id', 'exercise_id', 'created_ts', 'name' ];
        $solutions = $this->getAllSolutionsOfEnvironment($env);
        echo join(';', $cols), "\n";
        foreach ($solutions as $solution) {
            $solution->name = $solution->name_en ?? $solution->name_cs;
            $solution->created_ts = $solution->created_at->getTimestamp();
            $data = array_map(function($col) use($solution) { return $solution->$col; }, $cols);
            echo join(';', $data), "\n";
        }
    }


    private static function getAssignmentMaxPoints($assignment, $atTime)
    {
        if ($assignment->first_deadline > $atTime) {
            return $assignment->max_points_before_first_deadline;
        }

        if ($assignment->allow_second_deadline && $assignment->second_deadline > $atTime) {
            return $assignment->max_points_before_second_deadline;
        }

        return 0;
    }

    public function checkScoreErrors()
    {
        $assignments = $this->getAssignments();
        echo "Checking ", $assignments->getRowCount(), " assignments..";
        $counter = 0;
        foreach ($assignments as $assignment) {
            ++$counter;
            if ($counter % 10 === 0) echo '.';

            if ($assignment->max_points_deadline_interpolation) continue;
            $evaluations = $this->getAssignmentSolutionsEvaluations($assignment->id);
            foreach ($evaluations as $evaluation) {
                $correctness = (float)$evaluation->score;
                if ($assignment->points_percentual_threshold > $correctness) continue;

                $maxPoints = (int)self::getAssignmentMaxPoints($assignment, $evaluation->created_at);
                $points = (int)$evaluation->points;

                $computedPoints = (int)floor($correctness * $maxPoints + 1e-6);
                if ($computedPoints !== $points) {
                    echo "$assignment->id\t$evaluation->id\t$points != $computedPoints ($correctness, $maxPoints), $evaluation->created_at\n";
                }
            }
        }

        echo "\n";
    }

    public function fromLog()
    {
        // read CSV log from stdin
        $solutions = [];
        $fp = fopen('php://stdin', 'r');
        while (($row = fgetcsv($fp)) !== false) {
            list($user, $ts, $ip, $endpoint, $params) = $row;
            if (str_ends_with($endpoint, 'UploadedFiles:content') || str_ends_with($endpoint, 'UploadedFiles:download')) {
                $json = json_decode($params, true);
                if ($json && array_key_exists('id', $json)) {
                    $id = $json['id'];
                    $solutions[$id] = $solutions[$id] ?? [];
                    $solutions[$id][] = [
                        'ts' => $ts,
                        'ip' => $ip,
                        'endpoint' => $endpoint,
                        'entry' => $json['entry'] ?? null,
                        'user' => $user,
                    ];
                } else {
                    echo "Warning: unable to parse JSON params.\n";
                    echo implode(",", $row), "\n\n";
                }
            }
        }

        foreach ($solutions as $id => $entries) {
            $file = $this->getUploadedFile($id);
            if (!$file) {
                echo "Warning: uploaded file $id not found.\n";
                continue;
            }
            if ($file->solution_id === null) {
                echo "Warning: uploaded file $id not related to any solution.\n";
                continue;
            }
            
            $solution = $this->getAssignmentSolutionBySolutionId($file->solution_id);
            echo "https://recodex.mff.cuni.cz/app/assignment/{$solution->assignment_id}/solution/{$solution->id}\n";
            foreach ($entries as $entry) {
                echo "\t[{$entry['ts']}] ({$entry['ip']}): '{$entry['entry']}' by {$entry['user']}\n";
            }
            echo "\n";
        }

        fclose($fp);
    }
}
