<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Stats extends BaseCommand
{
    private function getRoot($groups)
    {
        $rootCandidates = array_filter($groups, function ($g) { return $g->parent_group_id === null; });
        if (count($rootCandidates) !== 1) {
            echo "Ambiguous root!\n";
            var_dump($rootCandidates);
            return;
        }
        return reset($rootCandidates);
    }

    private function getCourses($groups, $root = null)
    {
        if (!$root) {
            $root = $this->getRoot($groups);
        }

        $courseGroups = [];
        do {
            $changed = false;
            foreach ($groups as $group) {
                if (array_key_exists($group->id, $courseGroups)) {
                    continue;
                }
                if (!$group->external_id || preg_match('/^20[0-9]{2}-[12]$/', $group->external_id)) {
                    continue;
                }
                if ($group->parent_group_id === $root->id || array_key_exists($group->parent_group_id, $courseGroups)) {
                    $courseGroups[$group->id] = $group;
                    $changed = true;
                }
            }
        } while ($changed);
        return $courseGroups;
    }

    private function associateGroupsToParents(array $groups, array $selected, array $parents): array
    {
        $res = [];
        foreach ($parents as $parent) {
            $res[$parent->id] = [ $parent ];
        }

        foreach ($selected as $group) {
            $pid = $group->parent_group_id;
            while ($pid && !array_key_exists($pid, $parents)) {
                $pid = array_key_exists($pid, $groups) ? $groups[$pid]->parent_group_id : null;
            }

            if ($pid) {
                $res[$pid][] = $group;
            }
        }
        return $res;
    }

    public function groups()
    {
        $groups = $this->getGroups(true);
        $root = $this->getRoot($groups);
        unset($groups[$root->id]);

        $courseGroups = $this->getCourses($groups, $root);

        $semesterGroups = [];
        $allSemesterGroups = [];
        $otherGroups = [];
        foreach ($groups as $group) {
            if (array_key_exists($group->id, $courseGroups)) {
                continue;
            }

            if (preg_match('/^20[0-9]{2}-[12]$/', $group->external_id) && array_key_exists($group->parent_group_id, $courseGroups)) {
                $semesterGroups[$group->parent_group_id][] = $group;
                $allSemesterGroups[$group->id] = $group;
            } else {
                $otherGroups[] = $group;
            }
        }

        $semesterSubgroups = $this->associateGroupsToParents($groups, $otherGroups, $allSemesterGroups);

        usort($courseGroups, function ($a, $b) {
            return strcmp($a->name_en ?? $a->name_cs, $b->name_en ?? $b->name_cs);
        });
        foreach ($semesterGroups as &$sg) {
            usort($sg, function ($a, $b) {
                return strcmp($a->external_id, $b->external_id);
            });
        }
        unset($sg);

        $courses = [];
        foreach ($courseGroups as $group) {
            $ids = preg_split('/\\s+/', $group->external_id);
            foreach ($ids as $eid) {
                if (array_key_exists($eid, $courses)) {
                    echo "Two groups for $eid!\n";
                    exit;
                }
                $courses[$eid] = $group;
            }
            
            echo ($group->name_en ?? $group->name_cs), '  (', $group->external_id, ")\n";

            $solvers = $solutions = 0;
            foreach ($semesterGroups[$group->id] ?? [] as $sem) {
                if (empty($semesterSubgroups[$sem->id])) {
                    continue;
                }

                $stats = $this->getAssignmentSolversGroupStats($semesterSubgroups[$sem->id]);
                if ($stats && $stats->solvers) {
                    echo '    ', $sem->external_id, '    admins: ', str_pad($stats->admins, 4), ' students: ', str_pad($stats->students, 4),
                        ' solvers: ', str_pad($stats->solvers, 4), " solutions: $stats->solutions\n";
                    $solvers += $stats->solvers;
                    $solutions += $stats->solutions;
                }
            }

            echo "    total solvers: $solvers, solutions: $solutions\n\n";
        }

        echo "Total ", count($courses), " courses\n";
    }

    public function people()
    {
        foreach (['Active' => 'AND g.archived_at IS NULL', 'Total' => ''] as $caption => $clause) {
            foreach (['students' => ['student'], 'teachers' => ['admin', 'supervisor']] as $who => $types) {
                $res = $this->db->fetchSingle("SELECT COUNT(DISTINCT gm.user_id)
                    FROM [group] AS g JOIN group_membership AS gm ON gm.group_id = g.id
                    WHERE g.deleted_at IS NULL AND gm.type IN (?) $clause", $types);
                echo "$caption $who: $res\n";
            }
            $res = $this->db->fetchSingle("SELECT COUNT(DISTINCT asol.solver_id)
                FROM [group] AS g JOIN assignment AS ass ON ass.group_id = g.id JOIN assignment_solver AS asol ON asol.assignment_id = ass.id
                WHERE g.deleted_at IS NULL $clause");
            echo "$caption solvers: $res\n";
        }
    }

    public function exercises()
    {
        $groups = $this->getGroups(true);
        $courseGroups = $this->getCourses($groups);
        $otherGroups = array_filter($groups, function ($g) { return $g->parent_group_id && empty($courseGroups[$g->id]); });
        $associated = $this->associateGroupsToParents($groups, $otherGroups, $courseGroups);

        $assignments = 0;
        foreach ($courseGroups as $course) {
            $ids = array_map(function ($g) { return $g->id; }, $associated[$course->id]);
            $stats = $this->db->fetch("SELECT COUNT(DISTINCT e.id) AS exercises,
                COUNT(DISTINCT a.id) AS assignments
                FROM exercise AS e LEFT JOIN assignment AS a ON a.exercise_id = e.id
                WHERE e.deleted_at IS NULL AND a.deleted_at IS NULL AND
                EXISTS (SELECT * FROM exercise_group AS eg WHERE eg.exercise_id = e.id AND eg.group_id IN (?))", $ids);

            $assignments += $stats->assignments;
            $name = $course->name_en ?? $course->name_cs;
            $subgroups = count(array_filter($associated[$course->id], function ($g) { return $g->is_organizational; }));
            echo $name, str_pad('', 64 - mb_strlen($name)), str_pad($subgroups, 6), str_pad($stats->exercises, 6), $stats->assignments, "\n";
        }

        $exercises = $this->db->fetchSingle("SELECT COUNT(DISTINCT e.id) FROM exercise AS e JOIN exercise_group AS eg ON eg.exercise_id = e.id
            WHERE e.deleted_at IS NULL AND EXISTS (SELECT * FROM [group] AS g WHERE g.id = eg.group_id AND g.deleted_at IS NULL)");
        echo "\nTotal exercises: $exercises\nTotal assignments: $assignments\n";
    }

    public function runtimes()
    {
        $res = $this->db->query("SELECT re.id, re.long_name,
            (SELECT COUNT(*) FROM exercise AS e WHERE e.deleted_at IS NULL
                AND EXISTS (SELECT * FROM [group] AS g JOIN exercise_group AS eg ON eg.group_id = g.id
                    WHERE eg.exercise_id = e.id AND g.archived_at IS NULL AND g.deleted_at IS NULL)
                AND EXISTS (SELECT * FROM exercise_runtime_environment AS ere WHERE ere.exercise_id = e.id AND ere.runtime_environment_id = re.id)) AS exercises,
            (SELECT COUNT(*) FROM solution AS s WHERE s.runtime_environment_id = re.id) AS solutions
            FROM runtime_environment AS re");
        foreach ($res as $env) {
            echo str_pad($env->long_name, 32), str_pad($env->exercises, 6), $env->solutions, "\n";
        }
    }

    public function submits($year, $month)
    {
        $year = (int)$year;
        $month = (int)$month;
        $res = $this->db->query("SELECT YEAR(sol.created_at) AS cyear, MONTH(sol.created_at) AS cmonth, DAY(sol.created_at) AS cday, COUNT(*) AS solutions
            FROM assignment_solution AS asol JOIN solution AS sol ON sol.id = asol.solution_id
            WHERE YEAR(sol.created_at) >= ? AND MONTH(sol.created_at) >= ?
            GROUP BY YEAR(sol.created_at), MONTH(sol.created_at), DAY(sol.created_at)
            ORDER BY 1, 2, 3", $year, $month);
        
        foreach ($res as $day) {
            echo $day->cyear, '-', $day->cmonth, '-', $day->cday, ';', $day->solutions, "\n";
        }
    }

    public function solutions($year, ...$parentGroups)
    {
        // find right semestral groups
        $allGroups = $this->getGroups(true);
        $groups = [];
        foreach ($allGroups as $group) {
            if (str_starts_with($group->external_id, $year) && in_array($group->parent_group_id, $parentGroups)) {
                $groups[$group->id] = $group;
            }
        }

        // add all descendant groups
        do {
            $somethingAdded = false;
            foreach ($allGroups as $group) {
                if (!array_key_exists($group->id, $groups) && array_key_exists($group->parent_group_id, $groups)) {
                    $groups[$group->id] = $group;
                    $somethingAdded = true;
                }
            }
        } while ($somethingAdded);

        $solversData = $this->db->query("SELECT aslv.*
            FROM assignment_solver AS aslv JOIN assignment AS ass ON ass.id = aslv.assignment_id
            WHERE ass.group_id IN (?) AND ass.deleted_at IS NULL
            ORDER BY aslv.assignment_id, aslv.solver_id",
            array_keys($groups));
        
        $solvers = [];
        foreach ($solversData as $sd) {
            $solvers[$sd->assignment_id][$sd->solver_id] = (int)$sd->last_attempt_index;
        }

        $solutions = $this->db->query("SELECT ass.group_id AS group_id, ass.id AS assignment_id,
            sol.author_id AS user_id, asol.attempt_index AS attempt_index, se.score AS score
            FROM assignment_solution AS asol
            JOIN solution AS sol ON sol.id = asol.solution_id
            JOIN assignment AS ass ON ass.id = asol.assignment_id
            JOIN assignment_solution_submission AS asub ON asub.id = asol.last_submission_id
            LEFT JOIN solution_evaluation AS se ON se.id = asub.evaluation_id
            WHERE ass.group_id IN (?) AND ass.deleted_at IS NULL
            ORDER BY 1, 2, 3, 4",
            array_keys($groups));

        $comments = $this->db->fetch("SELECT AVG(review_comments) AS review_comments, AVG(comments) AS comments, AVG(commented_solutions / solutions) AS commented_solutions
            FROM (
            SELECT ass.id AS assignment_id, sol.author_id AS user_id, COUNT(rc.id) AS review_comments, COUNT(c.id) AS comments,
                COUNT(DISTINCT asol.id) AS solutions, (
                    SELECT COUNT(*) FROM assignment_solution AS asol2 JOIN solution AS sol2 ON sol2.id = asol2.solution_id
                    WHERE asol2.assignment_id = asol.assignment_id AND sol2.author_id = sol.author_id AND
                    (EXISTS (SELECT * FROM comment AS c2 WHERE c2.comment_thread_id = asol2.id) OR
                    EXISTS (SELECT * FROM review_comment AS rc2 WHERE rc2.solution_id = asol2.id))
                ) AS commented_solutions
            FROM assignment_solution AS asol
            JOIN solution AS sol ON sol.id = asol.solution_id
            JOIN assignment AS ass ON ass.id = asol.assignment_id
            LEFT JOIN review_comment AS rc ON rc.solution_id = asol.id
            LEFT JOIN comment AS c ON c.comment_thread_id = asol.id
            WHERE ass.group_id IN (?) AND ass.deleted_at IS NULL
            GROUP BY ass.id, sol.author_id) AS t",
            array_keys($groups));
            
        $data = [];
        foreach ($solutions as $s) {
            $data[$s->group_id][$s->assignment_id][$s->user_id][$s->attempt_index] = $s->score;
        }
        
        $assCount = [];
        $solverCount = [];
        $solutionsCount = [];
        $notCorrectCount = [];
        $bestScore = [];
        $studentTried = [];
        $studentSolved = [];
        foreach ($data as $gid => $gdata) {
            if (!$groups[$gid]->is_exam) {
                $assCount[] = count($gdata);
            }
            $studentTriedGrp = [];
            $studentSolvedGrp = [];
            foreach ($gdata as $aid => $gadata) {
                foreach ($gadata as $uid => $gaudata) {
                    if (!empty($solvers[$aid][$uid])) {
                        $solverCount[$uid] = true;

                        // fix data (fill in deleted solutions)
                        for ($i = 1; $i <= $solvers[$aid][$uid]; ++$i) {
                            if (!array_key_exists($i, $gaudata)) {
                                $gaudata[$i] = null;
                            }
                        }

                        $solutionsCount[] = count($gaudata);
                        $notNull = array_map(function($s) { return (float)$s; }, array_filter($gaudata, function ($score) { return $score !== null && $score !== ''; }));
                        $best = $notNull ? max($notNull) : 0;
                        $bestScore[] = $best;
                        $notCorrect = array_filter($notNull, function ($score) { return (float)$score < 1.0; });
                        $notCorrectCount[] = count($notCorrect);

                        if (count($gaudata) > 0) {
                            $studentTriedGrp[$uid] = ($studentTriedGrp[$uid] ?? 0) + 1;
                            if ($best >= 1.0) {
                                $studentSolvedGrp[$uid] = ($studentSolvedGrp[$uid] ?? 0) + 1;
                            }
                        }
                    }
                }
            }

            if (count($gdata) > 0) {
                foreach ($studentTriedGrp as $c) {
                    $studentTried[] = (float)$c / (float)count($gdata);
                }
                foreach ($studentSolvedGrp as $c) {
                    $studentSolved[] = (float)$c / (float)count($gdata);
                }
            }
        }

        $results = [
            'solvers' => count($solverCount),
            'avg_ass' => (float)array_sum($assCount) / (float)count($assCount),
            'sol_cnt' => (float)array_sum($solutionsCount),
            'avg_sol_cnt' => (float)array_sum($solutionsCount) / (float)count($solutionsCount),
            'avg_best' => (float)array_sum($bestScore) / (float)count($bestScore),
            'avg_wrong_cnt' => (float)array_sum($notCorrectCount) / (float)count($notCorrectCount),
            'avg_tried_ass' => (float)array_sum($studentTried) / (float)count($studentTried),
            'avg_solved_ass' => (float)array_sum($studentSolved) / (float)count($studentSolved),
            'comments' => $comments->comments,
            'review_comments' => $comments->review_comments,
            'commented_solutions' => $comments->commented_solutions,
        ];

        fputcsv(STDOUT, array_keys($results));
        fputcsv(STDOUT, array_values($results));
    }
}
