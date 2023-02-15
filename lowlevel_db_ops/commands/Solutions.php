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
}
