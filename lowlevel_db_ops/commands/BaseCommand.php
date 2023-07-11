<?php


class BaseCommand
{
    protected $db;

    public function __construct($db)
    {
        $this->db = $db;
    }

    protected function getExerciseName($exerciseId, $locale = 'en')
    {
        return getLocaleSafe( $this->db->fetchPairs('SELECT le.locale, le.name FROM exercise_localized_exercise AS ele
            JOIN localized_exercise AS le ON le.id = ele.localized_exercise_id
            WHERE ele.exercise_id = ?', $exerciseId),
            $locale
        );
    }

    
    protected function getAssignmentName($assignmentId, $locale = 'en')
    {
        return getLocaleSafe( $this->db->fetchPairs('SELECT le.locale, le.name FROM assignment_localized_exercise AS ale
            JOIN localized_exercise AS le ON le.id = ale.localized_exercise_id
            WHERE ale.assignment_id = ?', $assignmentId),
            $locale
        );
    }

    protected function getGroups($archived = false)
    {
        $archivedClause = $archived ? '' : 'AND g.archived_at IS NULL';
        return $this->db->query("SELECT g.*,
            (SELECT name FROM localized_group AS lg WHERE lg.group_id = g.id AND locale = 'en' LIMIT 1) AS name_en,
            (SELECT description FROM localized_group AS lg WHERE lg.group_id = g.id AND locale = 'en' LIMIT 1) AS description_en,
            (SELECT name FROM localized_group AS lg WHERE lg.group_id = g.id AND locale = 'cs' LIMIT 1) AS name_cs,
            (SELECT description FROM localized_group AS lg WHERE lg.group_id = g.id AND locale = 'cs' LIMIT 1) AS description_cs
            FROM [group] AS g WHERE g.deleted_at IS NULL $archivedClause")
            ->fetchAssoc('id');
    }

    protected function getAssignmentSolversGroupStats($groups)
    {
        $ids = array_map(function ($g) { return $g->id; }, $groups);
        return $this->db->fetch("SELECT COUNT(DISTINCT asol.solver_id) AS solvers, SUM(asol.last_attempt_index) AS solutions, SUM(asol.evaluations_count) AS evaluations,
            (SELECT COUNT(DISTINCT gm.user_id) FROM group_membership AS gm WHERE gm.group_id IN (?) AND gm.type = 'student') AS students,
            (SELECT COUNT(DISTINCT gm.user_id) FROM group_membership AS gm WHERE gm.group_id IN (?) AND gm.type = 'admin') AS admins
            FROM [group] AS g LEFT JOIN assignment AS ass ON ass.group_id = g.id JOIN assignment_solver AS asol ON asol.assignment_id = ass.id
            WHERE g.id IN (?)", $ids, $ids, $ids);
    }

    protected function getGroupName($groupId, $locale = 'en')
    {
        return getLocaleSafe(
            $this->db->fetchPairs('SELECT locale, name FROM localized_group WHERE group_id = ?', $groupId),
            $locale);
    }

    protected function getUserName($userId)
    {
        return $this->db->fetchSingle("SELECT CONCAT(first_name, ' ', last_name) FROM user WHERE id = ?", $userId);
    }


    protected function getExercises()
    {
        return $this->db->query("SELECT * FROM exercise WHERE deleted_at IS NULL");
    }
    
    protected function getExercisesWithRefs()
    {
        $res = [];
        $exercises = $this->db->query("SELECT e.*,
            (SELECT CONCAT(u.first_name, ' ', u.last_name) FROM user AS u WHERE u.id = e.author_id) AS author,
            (SELECT GROUP_CONCAT(t.name ORDER BY 1 SEPARATOR ',') FROM exercise_tag AS t WHERE t.exercise_id = e.id) AS tags_str,
            (SELECT GROUP_CONCAT(g.id ORDER BY 1 SEPARATOR ',') FROM exercise_group AS eg JOIN `group` g ON g.id = eg.group_id WHERE eg.exercise_id = e.id AND g.deleted_at IS NULL AND g.archived_at IS NULL) AS groups_str,
            (SELECT GROUP_CONCAT(ele.localized_exercise_id ORDER BY 1 SEPARATOR ',') FROM exercise_localized_exercise AS ele WHERE ele.exercise_id = e.id) AS localized_exercises_str,
            (SELECT GROUP_CONCAT(ere.runtime_environment_id ORDER BY 1 SEPARATOR ',') FROM exercise_runtime_environment AS ere WHERE ere.exercise_id = e.id) AS runtimes_str,
            (SELECT GROUP_CONCAT(eeec.exercise_environment_config_id ORDER BY 1 SEPARATOR ',') FROM exercise_exercise_environment_config AS eeec WHERE eeec.exercise_id = e.id) AS runtime_configs_str,
            (SELECT GROUP_CONCAT(ehg.hardware_group_id ORDER BY 1 SEPARATOR ',') FROM exercise_hardware_group AS ehg WHERE ehg.exercise_id = e.id) AS hardware_groups_str,
            (SELECT GROUP_CONCAT(eet.exercise_test_id ORDER BY 1 SEPARATOR ',') FROM exercise_exercise_test AS eet WHERE eet.exercise_id = e.id) AS tests_str,
            (SELECT GROUP_CONCAT(eel.exercise_limits_id ORDER BY 1 SEPARATOR ',') FROM exercise_exercise_limits AS eel WHERE eel.exercise_id = e.id) AS limits_str,
            (SELECT GROUP_CONCAT(eaf.attachment_file_id ORDER BY 1 SEPARATOR ',') FROM exercise_attachment_file AS eaf WHERE eaf.exercise_id = e.id) AS attachment_files_str,
            (SELECT GROUP_CONCAT(esef.supplementary_exercise_file_id ORDER BY 1 SEPARATOR ',') FROM exercise_supplementary_exercise_file AS esef WHERE esef.exercise_id = e.id) AS supplementary_files_str
            FROM exercise AS e WHERE e.deleted_at IS NULL");
        
        $parseCols = [
            'tags_str' => 'tags',
            'groups_str' => 'groups',
            'localized_exercises_str' => 'localized_exercises',
            'runtimes_str' => 'runtimes',
            'runtime_configs_str' => 'runtime_configs',
            'hardware_groups_str' => 'hardware_groups',
            'tests_str' => 'tests',
            'limits_str' => 'limits',
            'attachment_files_str' => 'attachment_files',
            'supplementary_files_str' => 'supplementary_files',
        ];

        foreach ($exercises as $exercise) {
            foreach ($parseCols as $col => $newCol) {
                $str = $exercise[$col];
                $exercise[$newCol] = $str ? explode(',', $str) : [];
            }
            $res[$exercise['id']] = $exercise;
        }

        return $res;
    }

    protected function getLocalizedExercises()
    {
        $texts = $this->db->query("SELECT le.* FROM localized_exercise AS le WHERE EXISTS
            (SELECT * FROM exercise AS e JOIN exercise_localized_exercise AS ele ON ele.exercise_id = e.id
            WHERE e.deleted_at IS NULL AND ele.localized_exercise_id = le.id)");
        
        $res = [];
        foreach ($texts as $text) {
            $res[$text->id] = $text;
        }
        return $res;
    }

    protected function getAssignments()
    {
        return $this->db->query("SELECT * FROM assignment WHERE deleted_at IS NULL");
    }
    
    
    protected function getExerciseConfig($configId)
    {
        $configYaml = $this->db->fetchSingle('SELECT config FROM exercise_config WHERE id = ?', $configId);
        return yaml_parse($configYaml);
    }

    protected function getExercisesConfigs($onlyUsed = false)
    {
        $where = $onlyUsed ? 'WHERE EXISTS (SELECT * FROM exercise AS e WHERE e.exercise_config_id = ec.id AND e.deleted_at IS NULL)' : '';
        return $this->db->fetchPairs("SELECT ec.id, ec.config FROM exercise_config AS ec $where");
    }

    protected function getExercisesScoreConfigs()
    {
        return $this->db->fetchPairs('SELECT id, score_config FROM exercise WHERE deleted_at IS NULL');
    }

    protected function getExerciseTestsByName($exerciseId)
    {
        return $this->db->fetchPairs('SELECT et.name, et.id FROM exercise_test AS et
            JOIN exercise_exercise_test AS eet ON eet.exercise_test_id = et.id
            WHERE eet.exercise_id = ?', $exerciseId);
    }

    
    protected function getAssignmentSupplementaryFiles($assignmentId)
    {
        return $this->db->fetchPairs('SELECT f.name, f.id FROM assignment_supplementary_exercise_file AS af
            JOIN uploaded_file AS f ON f.id = af.supplementary_exercise_file_id
            WHERE af.assignment_id = ?', $assignmentId);
    }

    protected function getExerciseSupplementaryFiles($exerciseId)
    {
        return $this->db->fetchPairs('SELECT f.name, f.id FROM exercise_supplementary_exercise_file AS ef
            JOIN uploaded_file AS f ON f.id = ef.supplementary_exercise_file_id
            WHERE ef.exercise_id = ?', $exerciseId);
    }


    protected function getGroupAdmins($groupId)
    {
        return $this->db->fetchPairs('SELECT u.id AS id, CONCAT(u.first_name, \' \', u.last_name) AS username
            FROM group_user AS gu JOIN user AS u ON gu.user_id = u.id WHERE gu.group_id = ?', $groupId);
    }


    protected function getCommentText($id)
    {
        return $this->db->fetchSingle("SELECT `text` FROM comment WHERE id = ?", $id);
    }

    protected function getPipeline($id)
    {
        return $this->db->fetch('SELECT * FROM pipeline WHERE id = ?', $id);
    }

    protected function getPipelineConfigs()
    {
        return $this->db->fetchPairs('SELECT p.id, pc.pipeline_config FROM pipeline AS p JOIN pipeline_config AS pc ON p.pipeline_config_id = pc.id');
    }

    protected function getRuntimePipelinesIds($rte)
    {
        return $this->db->fetchPairs('SELECT pipeline_id AS k, pipeline_id AS v FROM pipeline_runtime_environment WHERE runtime_environment_id = ?', $rte);
    }

    protected function getPipelineBoolParameters($id)
    {
        return $this->db->fetchPairs('SELECT name, boolean_value FROM pipeline_parameter WHERE pipeline_id = ? AND discriminator = "booleanpipelineparameter"', $id);
    }

    protected function getRuntimeConfigs()
    {
        return $this->db->fetchPairs('SELECT id, default_variables FROM runtime_environment');
    }

    protected function getAssignmentSolutionsEvaluations($id)
    {
        return $this->db->query("SELECT sol.*, se.*
            FROM assignment_solution AS asol
            JOIN solution AS sol ON asol.solution_id = sol.id
            JOIN assignment_solution_submission AS asub ON asol.last_submission_id = asub.id
            JOIN solution_evaluation AS se ON asub.evaluation_id = se.id
            WHERE asol.assignment_id = ?", $id);
    }

    protected function getAllSolutionsOfEnvironment($env)
    {
        return $this->db->query("SELECT ass.id AS id, a.id AS assignment_id, s.author_id AS author_id, a.group_id AS group_id,
            a.exercise_id AS exercise_id, s.created_at AS created_at,
            (SELECT le.name FROM localized_exercise AS le JOIN exercise_localized_exercise AS ele ON ele.localized_exercise_id = le.id
                WHERE le.locale = 'en' AND ele.exercise_id = a.exercise_id) AS name_en,
            (SELECT le.name FROM localized_exercise AS le JOIN exercise_localized_exercise AS ele ON ele.localized_exercise_id = le.id
                WHERE le.locale = 'cs' AND ele.exercise_id = a.exercise_id) AS name_cs
            FROM assignment_solution AS ass JOIN solution AS s ON s.id = ass.solution_id JOIN assignment AS a ON ass.assignment_id = a.id
            WHERE runtime_environment_id = ? ORDER BY s.created_at", $env);
    }
}
