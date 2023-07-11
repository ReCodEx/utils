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
}
