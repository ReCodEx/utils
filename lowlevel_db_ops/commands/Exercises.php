<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Exercises extends BaseCommand
{
    private function verifyExerciseFiles($exercise)
    {
        $config = $this->getExerciseConfig($exercise->exercise_config_id);
        $variables = harvestConfigVariables($config);
        $varFiles = harvestRemoteFilesFromVariables($variables);
        $supFiles = $this->getExerciseSupplementaryFiles($exercise->id);
        $missingFiles = [];
        foreach ($varFiles as $file) {
            if (empty($supFiles[$file])) {
                $missingFiles[] = $file;
            }
        }
        return $missingFiles;
    }


    private function verifyExerciseTestsScore($exercise)
    {
        $score = yaml_parse($exercise->score_config);
        if (!array_key_exists('testWeights', $score)) {
            return [ 'TestWeights not specified at all.' ];
        }

        $tests = $this->getExerciseTestsByName($exercise->id);

        $errors = [];
        foreach ($score['testWeights'] as $name => $weight) {
            if (!$weight) $errors[] = "'$name' has zero weight.";
            if (!array_key_exists($name, $tests)) $errors[] = "'$name' is present in the score, but not present in the tests.";
            else unset($tests[$name]);
        }

        foreach ($tests as $name => $id) {
            $errors[] = "'$name' is present in the tests, but not in the score config.";
        }

        return $errors;
    }

    private static function sameYaml($y1, $y2)
    {
        if ($y1 === $y2) {
            return true;
        }

        if ($y1 === null || $y2 === null) {
            return false;
        }

        $yaml1 = yaml_parse($y1);
        $yaml2 = yaml_parse($y2);
        return $yaml1 == $yaml2;
    }

    // cache
    private $exerciseConfigs = null;

    private function sameExerciseConfig($e1, $e2)
    {
        if ($e1->exercise_config_id === $e2->exercise_config_id) {
            return true;
        }

        if ($this->exerciseConfigs === null) {
            $this->exerciseConfigs = $this->getExercisesConfigs(true);
        }

        $c1 = $this->exerciseConfigs[$e1->exercise_config_id] ?? null;
        $c2 = $this->exerciseConfigs[$e2->exercise_config_id] ?? null;
        return self::sameYaml($c1, $c2);
    }


    // cache
    private $scoreConfigs = null;

    private function sameScoreConfig($e1, $e2)
    {
        if ($e1->score_config_id === $e2->score_config_id) {
            return true;
        }

        if ($this->scoreConfigs === null) {
            $configs = $this->db->query("SELECT esc.* FROM exercise_score_config AS esc WHERE EXISTS
                (SELECT * FROM exercise AS e WHERE e.score_config_id = esc.id)");
            $this->scoreConfigs = [];
            foreach ($configs as $config) {
                $this->scoreConfigs[$config->id] = $config;
            }
        }

        $c1 = $this->scoreConfigs[$e1->score_config_id] ?? null;
        $c2 = $this->scoreConfigs[$e2->score_config_id] ?? null;
        if ($c1 === null || $c2 === null || $c1->calculator !== $c2->calculator) {
            return false;
        }

        return self::sameYaml($c1->config, $c2->config);
    }

    // cache
    private $runtimeConfigs = null;

    // that includes hw groups and runtime configs
    private function sameRuntimes($e1, $e2)
    {
        if ($e1->hardware_groups_str !== $e2->hardware_groups_str || $e1->runtimes_str !== $e2->runtimes_str) {
            return false;
        }

        if ($e1->runtime_configs_str === $e2->runtime_configs_str) {
            return true;
        }
        
        if ($this->runtimeConfigs === null) {
            $configs = $this->db->query("SELECT eec.* FROM exercise_environment_config AS eec WHERE EXISTS
                (SELECT * FROM exercise AS e JOIN exercise_exercise_environment_config AS eeec ON eeec.exercise_id = e.id
                WHERE e.deleted_at IS NULL AND eeec.exercise_environment_config_id = eec.id)");
            $this->runtimeConfigs = [];
            foreach ($configs as $config) {
                $this->runtimeConfigs[$config->id] = $config;
            }
        }

        $c1 = [];
        foreach ($e1->runtime_configs as $rcid) {
            if (empty($this->runtimeConfigs[$rcid])) {
                return false;
            }
            $c1[$this->runtimeConfigs[$rcid]->runtime_environment_id] = $this->runtimeConfigs[$rcid]->variables_table;
        }
        
        $c2 = [];
        foreach ($e2->runtime_configs as $rcid) {
            if (empty($this->runtimeConfigs[$rcid])) {
                return false;
            }
            $c2[$this->runtimeConfigs[$rcid]->runtime_environment_id] = $this->runtimeConfigs[$rcid]->variables_table;
        }

        foreach ($e1->runtimes as $rte) {
            if (!array_key_exists($rte, $c1) || !array_key_exists($rte, $c2) || !self::sameYaml($c1[$rte], $c2[$rte])) {
                return false;
            }
        }

        return true;
    }

    private $tests = null;

    private function sameTests($e1, $e2)
    {
        if ($e1->tests_str === $e2->tests_str) {
            return true;
        }

        if (count($e1->tests) !== count($e2->tests)) {
            return false;
        }

        if ($this->tests === null) {
            $tests = $this->db->query("SELECT t.* FROM exercise_test AS t WHERE EXISTS
                (SELECT * FROM exercise AS e JOIN exercise_exercise_test AS eet ON eet.exercise_id = e.id
                WHERE e.deleted_at IS NULL AND eet.exercise_test_id = t.id)");
            $this->tests = [];
            foreach ($tests as $test) {
                $this->tests[$test->id] = $test;
            }
        }

        $tests1 = $tests2 = [];
        for ($i = 0; $i < count($e1->tests); ++$i) {
            if ($e1->tests[$i] !== $e2->tests[$i]) {
                $t1 = $this->tests[$e1->tests[$i]] ?? null;
                $t2 = $this->tests[$e2->tests[$i]] ?? null;
                if (!$t1 || !$t2) {
                    return false;
                }
                $tests1[$t1->name] = $t1->description;
                $tests2[$t2->name] = $t2->description;
            }
        }

        return $tests1 == $tests2;
    }

    // cache
    private $supplementaryFiles = null;

    // supplementary files
    private function sameFiles($e1, $e2)
    {
        if ($e1->supplementary_files_str === $e2->supplementary_files_str) {
            return true;
        }

        if (count($e1->supplementary_files) !== count($e2->supplementary_files)) {
            return false;
        }

        if ($this->supplementaryFiles === null) {
            $this->supplementaryFiles = $this->db->fetchPairs("SELECT uf.id, uf.hash_name FROM uploaded_file AS uf
            WHERE uf.discriminator = 'supplementaryexercisefile' AND uf.hash_name IS NOT NULL AND EXISTS
            (SELECT * FROM exercise AS e JOIN exercise_supplementary_exercise_file AS esef ON esef.exercise_id = e.id
            WHERE esef.supplementary_exercise_file_id = uf.id AND e.deleted_at IS NOT NULL)");
        }

        $files1 = $files2 = [];
        for ($i = 0; $i < count($e1->supplementary_files); ++$i) {
            $f1 = $this->supplementaryFiles[$e1->supplementary_files[$i]] ?? null;
            $f2 = $this->supplementaryFiles[$e2->supplementary_files[$i]] ?? null;
            if (!$f1 || !$f2) {
                return false;
            }
            $files1[$f1] = true;
            $files2[$f2] = true;
        }

        return $files1 == $files2;
    }

    // cache
    private $limits = null;

    private function sameLimits($e1, $e2)
    {
        if ($e1->limits_str === $e2->limits_str) {
            return true;
        }

        if (count($e1->limits) !== count($e2->limits) || $e1->runtimes_str !== $e2->runtimes_str) {
            return false;
        }

        if ($this->limits === null) {
            $limits = $this->db->query("SELECT el.* FROM exercise_limits AS el WHERE EXISTS
                (SELECT * FROM exercise AS e JOIN exercise_exercise_limits AS eel ON eel.exercise_id = e.id
                WHERE e.deleted_at IS NULL AND eel.exercise_limits_id = el.id)");
            $this->limits = [];
            foreach ($limits as $limit) {
                $this->limits[$limit->id] = $limit;
            }
        }

        $limits1 = $limits2 = [];
        for ($i = 0; $i < count($e1->limits); ++$i) {
            $l1 = $this->limits[$e1->limits[$i]] ?? null;
            $l2 = $this->limits[$e2->limits[$i]] ?? null;
            if (!$l1 || !$l2) {
                return false;
            }
            $limits1[$l1->runtime_environment_id] = $l1->limits;
            $limits2[$l2->runtime_environment_id] = $l2->limits;
        }

        foreach ($e1->runtimes as $rte) {
            if (!self::sameYaml($limits1[$rte], $limits2[$rte])) {
                return false;
            }
        }

        return true;
    }

    private $texts = null;
    
    private function sameTexts($e1, $e2)
    {
        if ($e1->localized_exercises_str === $e2->localized_exercises_str) {
            return true;
        }

        if (count($e1->localized_exercises) !== count($e2->localized_exercises)) {
            return false;
        }

        if ($this->texts === null) {
            $this->texts = $this->getLocalizedExercises();
        }

        $texts1 = $texts2 = [];
        for ($i = 0; $i < count($e1->localized_exercises); ++$i) {
            $t1 = $this->texts[$e1->localized_exercises[$i]] ?? null;
            $t2 = $this->texts[$e2->localized_exercises[$i]] ?? null;
            if (!$t1 || !$t2) {
                return false;
            }
            $texts1[$t1->locale] = $t1;
            $texts2[$t2->locale] = $t2;
        }

        foreach ($texts1 as $locale => $t1) {
            if (empty($texts2[$locale])) {
                return false;
            }
            $t2 = $texts2[$locale];
            if ($t1->name !== $t2->name
                || $t1->description !== $t2->description
                || $t1->external_assignment_link !== $t2->external_assignment_link
            ) {
                return false;
            }
        }

        return true;
    }

    private function sameOtherConfig($e1, $e2)
    {
        return $e1->difficulty === $e2->difficulty
            && $e1->configuration_type === $e2->configuration_type
            && $e1->solution_files_limit === $e2->solution_files_limit
            && $e1->solution_size_limit === $e2->solution_size_limit
            && $e1->merge_judge_logs === $e2->merge_judge_logs
            && $e1->tags_str === $e2->tags_str;
    }

    private function getExerciseNames($e)
    {
        if ($this->texts === null) {
            $this->texts = $this->getLocalizedExercises();
        }

        $texts = [];
        foreach ($e->localized_exercises ?? [] as $id) {
            $texts[$this->texts[$id]->locale] = $this->texts[$id]->name;
        }
        return $texts;
    }

    /*
     * Public interface
     */

    public function verifyFilesIntegrity()
    {
        $exercises = $this->getExercises();
        echo "Checking ", $exercises->getRowCount(), " exercises..";
        $failed = [];
        $missingFiles = [];
        foreach ($exercises as $exercise) {
            $res = $this->verifyExerciseFiles($exercise);
            if ($res) {
                $failed[] = $exercise;
                $missingFiles[$exercise->id] = $res;
                echo 'X';
            } else {
                echo '.';
            }
        }
        echo "\n\n";

        foreach ($failed as $exercise) {
            echo "Integrity failed in exercise ", $exercise->id, ": ", $this->getExerciseName($exercise->id), "\n";
            echo "Author:", $this->getUserName($exercise->author_id), "\n";
            echo "Files missing: ", join(", ", $missingFiles[$exercise->id]), "\n";
            echo "-----------------------\n\n";
        }
    }


    public function verifyTestsScores()
    {
        $exercises = $this->getExercises();
        echo "Checking ", $exercises->getRowCount(), " exercises..";

        $failed = [];
        $errors = [];
        foreach ($exercises as $exercise) {
            $e = $this->verifyExerciseTestsScore($exercise);
            if ($e) {
                $failed[] = $exercise;
                $errors[$exercise->id] = $e;
                echo 'X';
            } else {
                echo '.';
            }
        }
        echo "\n\n";

        foreach ($failed as $exercise) {
            echo "Integrity failed in exercise ", $exercise->id, ": ", $this->getExerciseName($exercise->id), "\n";
            echo "Author:", $this->getUserName($exercise->author_id), "\n";
            foreach ($errors[$exercise->id] as $e) {
                echo "\t$e\n";
            }
            echo "-----------------------\n\n";
        }
    }


    public function verifyYamlConfigs()
    {
        $categories = [
            'getPipelineConfigs' => 'Pipeline configs',
            'getRuntimeConfigs' => 'Runtime default variables',
            'getExercisesConfigs' => 'Exercise configs',
            'getExercisesScoreConfigs' => 'Exercise score configs',
        ];

        foreach ($categories as $method => $caption) {
            echo "$caption:\n";
            $data = $this->$method();
            $okCount = 0;
            foreach ($data as $id => $yaml) {
                if (@yaml_parse($yaml) === false) {
                    echo "$id\tWRONG!!!\n";
                } else {
                    ++$okCount;
                }
            }
            echo "Total $okCount OK.\n\n";
        }
    }


    public function getSusForks()
    {
        $exercises = $this->getExercisesWithRefs();

        $checks = [ 'sameScoreConfig', 'sameFiles', 'sameLimits', 'sameTexts', 'sameOtherConfig' ];
        $header = array_merge([ 'id', 'author', 'name_cs', 'name_en', 'updated_at', 'is_broken', 'active_groups', 'url' ], $checks);
        fputcsv(STDOUT, $header);

        foreach ($exercises as $exercise) {
            if (!$exercise->exercise_id || !array_key_exists($exercise->exercise_id, $exercises)) continue;
            $original = $exercises[$exercise->exercise_id];
            
            if (!$this->sameExerciseConfig($exercise, $original)
                || !$this->sameRuntimes($exercise, $original)
                || !$this->sameTests($exercise, $original))
            {
                continue;
            }

            $names = $this->getExerciseNames($exercise);
            $row = [
                'id' => $exercise->id,
                'author' => $exercise->author,
                'name_cs' => $names['cs'] ?? null,
                'name_en' => $names['en'] ?? null,
                'updated_at' => $exercise->updated_at->format("Y-m-d H:i:s"),
                'is_broken' => $exercise->is_broken,
                'active_groups' => count($exercise->groups),
                'url' => 'https://recodex.mff.cuni.cz/app/exercises/' . $exercise->id,
            ];
            foreach ($checks as $check) {
                $row[$check] = (int)$this->$check($exercise, $original);
            }
            fputcsv(STDOUT, $row);
        }
    }

    public function getGPTCandidates($locale, $onlyRuntime = null)
    {
        if ($locale !== 'cs' && $locale !== 'en') {
            echo "Locale must be cs or en.\n";
            return;
        }

        $manifestFile = "manifest.csv";

        $creationLimit = '2021-10-01 00:00:00';

        $minTextLength = 150;
        $minSolutions = 1;
        $minSolvers = 1;
        $rteRestriction = '';
        $cols = [ 'id', 'name', 'text_length', 'locale', 'created_at', 'forked_from', 'assignments_count', 'solvers_count', 'solutions_count', 'attachments_count', 'runtime' ];

        $rteRestriction = empty($onlyRuntime) ? '' :
            "AND EXISTS (SELECT * FROM exercise_runtime_environment WHERE exercise_id = e.id AND runtime_environment_id = '$onlyRuntime')";
        $exercises = $this->db->query("SELECT e.id, le.name, le.assignment_text, LENGTH(le.assignment_text) AS text_length, le.locale AS locale,
                UNIX_TIMESTAMP(e.created_at) AS created_at, e.exercise_id AS forked_from,
                COUNT(ass.id) AS assignments_count, SUM(ass.solvers_count) AS solvers_count, SUM(ass.solutions_count) AS solutions_count,
                (SELECT COUNT(*) FROM exercise_attachment_file WHERE exercise_id = e.id) AS attachments_count
            FROM (
                SELECT ass.*,
                    (SELECT COUNT(*) FROM assignment_solver AS slv WHERE slv.assignment_id = ass.id) AS solvers_count,
                    (SELECT COUNT(*) FROM solution_evaluation AS se
                        JOIN assignment_solution_submission AS asub ON asub.evaluation_id = se.id
                        JOIN assignment_solution AS asol ON asub.assignment_solution_id = asol.id 
                        WHERE asol.assignment_id = ass.id AND se.score >= 1.0
                    ) AS solutions_count
                FROM assignment AS ass
                WHERE ass.created_at > '$creationLimit' AND ass.deleted_at IS NULL
            ) AS ass
            JOIN exercise AS e ON ass.exercise_id = e.id
            JOIN exercise_localized_exercise AS ele ON ele.exercise_id = e.id
            JOIN localized_exercise AS le ON ele.localized_exercise_id = le.id
            WHERE e.deleted_at IS NULL AND e.archived_at IS NULL AND le.locale = '$locale' AND le.external_assignment_link IS NULL
                AND NOT EXISTS (SELECT * FROM exercise_runtime_environment WHERE exercise_id = e.id
                    AND runtime_environment_id IN ('data-linux', 'java-maven', 'rust-cargo'))
                $rteRestriction
            GROUP BY e.id, le.name, le.description
            HAVING solutions_count >= ? AND solvers_count >= ? AND text_length > ?", $minSolutions, $minSolvers, $minTextLength);
        
        $counter = 0;
        $rteStats = [];
        
        $fp = $manifestFile ? fopen($manifestFile, "w") : null;
        if ($fp) fputcsv($fp, $cols);

        foreach ($exercises as $e) {
            $runtime = $this->db->fetchSingle("SELECT sol.runtime_environment_id FROM solution AS sol
                JOIN assignment_solution AS asol ON sol.id = asol.solution_id JOIN assignment AS ass ON ass.id = asol.assignment_id
                WHERE ass.created_at > '$creationLimit' AND ass.deleted_at IS NULL AND ass.exercise_id = ?
                GROUP BY runtime_environment_id
                ORDER BY COUNT(*) DESC LIMIT 1", $e->id);

            if (!empty($onlyRuntime) && $runtime !== $onlyRuntime) continue;

            ++$counter;
            $rteStats[$runtime] = ($rteStats[$runtime] ?? 0) + 1;

            if ($fp) {
                $data = [];
                foreach ($cols as $col) {
                    $data[] = $col === 'runtime' ? $runtime : $e->$col;
                }
                fputcsv($fp, $data);
            }

            if ($manifestFile) {
                file_put_contents("$e->id.md", $e->assignment_text);
            
                $attachments = $this->db->fetchAll("SELECT uf.* FROM uploaded_file AS uf JOIN exercise_attachment_file AS eaf ON eaf.attachment_file_id = uf.id
                    WHERE eaf.exercise_id = ?", $e->id);
                if ($attachments) {
                    echo "mkdir $e->id\n";
                    foreach ($attachments as $a) {
                        echo "wget --no-check-certificate https://recodex.mff.cuni.cz/api/v1/uploaded-files/$a->id/download -O \"$e->id/$a->name\"\n";
                    }
                }
            }
        }

        if ($fp) fclose($fp);

        if (!$manifestFile) {
            echo "Exercises: $counter\n";
            foreach ($rteStats as $runtime => $cnt) {
                echo "\t$runtime\t$cnt\n";
            }
        }
    }

    public function getGPTCandidatesExternal($locale, $onlyRuntime = null)
    {
        if ($locale !== 'cs' && $locale !== 'en') {
            echo "Locale must be cs or en.\n";
            return;
        }

        $manifestFile = "manifest.csv";

        $creationLimit = '2021-10-01 00:00:00';

        $minSolutions = 1;
        $minSolvers = 1;
        $rteRestriction = '';
        $cols = [ 'id', 'name', 'text_length', 'locale', 'created_at', 'forked_from', 'assignments_count', 'solvers_count', 'solutions_count', 'attachments_count', 'runtime' ];

        $rteRestriction = empty($onlyRuntime) ? '' :
            "AND EXISTS (SELECT * FROM exercise_runtime_environment WHERE exercise_id = e.id AND runtime_environment_id = '$onlyRuntime')";
        $exercises = $this->db->query("SELECT e.id, le.name, le.external_assignment_link, -1 AS text_length, le.locale AS locale,
                UNIX_TIMESTAMP(e.created_at) AS created_at, e.exercise_id AS forked_from,
                COUNT(ass.id) AS assignments_count, SUM(ass.solvers_count) AS solvers_count, SUM(ass.solutions_count) AS solutions_count,
                (SELECT COUNT(*) FROM exercise_attachment_file WHERE exercise_id = e.id) AS attachments_count
            FROM (
                SELECT ass.*,
                    (SELECT COUNT(*) FROM assignment_solver AS slv WHERE slv.assignment_id = ass.id) AS solvers_count,
                    (SELECT COUNT(*) FROM solution_evaluation AS se
                        JOIN assignment_solution_submission AS asub ON asub.evaluation_id = se.id
                        JOIN assignment_solution AS asol ON asub.assignment_solution_id = asol.id 
                        WHERE asol.assignment_id = ass.id AND se.score >= 1.0
                    ) AS solutions_count
                FROM assignment AS ass
                WHERE ass.created_at > '$creationLimit' AND ass.deleted_at IS NULL
            ) AS ass
            JOIN exercise AS e ON ass.exercise_id = e.id
            JOIN exercise_localized_exercise AS ele ON ele.exercise_id = e.id
            JOIN localized_exercise AS le ON ele.localized_exercise_id = le.id
            WHERE e.deleted_at IS NULL AND e.archived_at IS NULL AND le.locale = '$locale' AND le.external_assignment_link IS NOT NULL
                AND NOT EXISTS (SELECT * FROM exercise_runtime_environment WHERE exercise_id = e.id
                    AND runtime_environment_id IN ('data-linux', 'java-maven', 'rust-cargo'))
                $rteRestriction
            GROUP BY e.id, le.name, le.description
            HAVING solutions_count >= ? AND solvers_count >= ? AND external_assignment_link LIKE '%.md'", $minSolutions, $minSolvers);
        
        $counter = 0;
        $rteStats = [];
        
        $fp = $manifestFile ? fopen($manifestFile, "w") : null;
        if ($fp) fputcsv($fp, $cols);

        foreach ($exercises as $e) {
            $runtime = $this->db->fetchSingle("SELECT sol.runtime_environment_id FROM solution AS sol
                JOIN assignment_solution AS asol ON sol.id = asol.solution_id JOIN assignment AS ass ON ass.id = asol.assignment_id
                WHERE ass.created_at > '$creationLimit' AND ass.deleted_at IS NULL AND ass.exercise_id = ?
                GROUP BY runtime_environment_id
                ORDER BY COUNT(*) DESC LIMIT 1", $e->id);

            if (!empty($onlyRuntime) && $runtime !== $onlyRuntime) continue;

            ++$counter;
            $rteStats[$runtime] = ($rteStats[$runtime] ?? 0) + 1;

            if ($fp) {
                $data = [];
                foreach ($cols as $col) {
                    $data[] = $col === 'runtime' ? $runtime : $e->$col;
                }
                fputcsv($fp, $data);
            }

            if ($manifestFile) {
                $url = $e->external_assignment_link;
                echo "$e->id $url\n";
                $url = str_replace('/introai/blob/', '/introai/-/blob/', $url);
                $url = str_replace('/blob/', '/raw/', $url);
                $text = file_get_contents($url);
                file_put_contents("$e->id.md", $text);
            }
        }

        if ($fp) fclose($fp);

        if (!$manifestFile) {
            echo "Exercises: $counter\n";
            foreach ($rteStats as $runtime => $cnt) {
                echo "\t$runtime\t$cnt\n";
            }
        }
    }

    public function getExerciseTopGroups()
    {
        $ignoreList = [
            '58a749a7-cde2-11e7-a937-00505601122b' => 'Demo',
            'd4eea7e6-723e-11eb-a1a9-005056ad4f31' => 'CZV',
            '06ce12a9-64ab-11e8-9b58-00505601122b' => 'Skola ucitelu informatiky',
            'cc2c6207-a6ee-11e7-a937-00505601122b' => 'Testing',
        ];

        $egs = $this->db->query("SELECT eg.* FROM exercise_group AS eg
            JOIN exercise AS e ON e.id = eg.exercise_id JOIN `group` AS g ON g.id = eg.group_id
            WHERE e.deleted_at IS NULL AND g.deleted_at IS NULL ORDER BY eg.exercise_id");

        $groups = [];
        $res = [];
        foreach ($egs as $eg) {
            $tlg = $this->getTopLevelGroup($eg['group_id']);
            if (!empty($ignoreList[$tlg])) {
                continue;
            }

            $id = $eg['exercise_id'];
            $res[$id] = $res[$id] ?? [];
            $res[$id][$tlg] = true;
            $groups[$tlg] = null;
        }

        foreach ($groups as $id => &$name) {
            $name = $this->getGroupName($id);
        }
        unset($name);

        foreach ($res as $eid => $gids) {
            $gids = array_keys($gids);
            sort($gids);
            $row = [$eid];
            foreach ($gids as $gid) {
                $row[] = $gid;
                $row[] = $groups[$gid];
            }

            while (count($row) < 5) {
                $row[] = null;
            }
            fputcsv(STDOUT, $row);
        }
    }

    private function getLocs($content)
    {
        $lines = explode("\n", $content);
        $lines = array_filter($lines, function ($line) {
            return trim($line) !== '';
        });
        return count($lines);
    }

    public function getSolutionsLocs($type = 'assignment', $solutionsDir = '/var/recodex-filestorage/local/solutions')
    {
        $from = '2021-10-01 00:00:00';
        $to = '2023-10-01 00:00:00';
        if ($type === 'assignment') {
            $solutions = $this->db->query("SELECT e.id AS exercise_id, sol.subdir, sol.id, sol.runtime_environment_id, rt.extensions
                FROM assignment_solution AS asol
                JOIN solution AS sol ON sol.id = asol.solution_id
                JOIN assignment_solution_submission AS asub ON asub.id = asol.last_submission_id
                JOIN solution_evaluation AS se ON se.id = asub.evaluation_id
                JOIN assignment AS ass ON ass.id = asol.assignment_id
                JOIN exercise AS e ON e.id = ass.exercise_id
                JOIN runtime_environment AS rt ON sol.runtime_environment_id = rt.id
                WHERE e.deleted_at IS NULL AND ass.deleted_at IS NULL AND sol.created_at >= '$from' AND sol.created_at < '$to'
                    AND se.score >= 1.0");
        } elseif ($type === 'reference') {
            $solutions = $this->db->query("SELECT e.id AS exercise_id, sol.subdir, sol.id, sol.runtime_environment_id, rt.extensions
                FROM reference_exercise_solution AS rsol
                JOIN solution AS sol ON sol.id = rsol.solution_id
                JOIN reference_solution_submission AS rsub ON rsub.id = rsol.last_submission_id
                JOIN solution_evaluation AS se ON se.id = rsub.evaluation_id
                JOIN exercise AS e ON e.id = rsol.exercise_id
                JOIN runtime_environment AS rt ON sol.runtime_environment_id = rt.id
                WHERE e.deleted_at IS NULL AND se.score >= 1.0 AND rsol.visibility > 0");
        } else {
            echo "Invalid type $type (assignment or reference expected).\n";
            return;
        }

        $res = [];
        foreach ($solutions as $solution) {
            $zipFile = $solutionsDir . '/' . $solution->subdir . '/' . $solution->id . '.zip';
            if (!file_exists($zipFile)) {
                echo "File $zipFile does not exist!\n";
                continue;
            }

            $extensions = yaml_parse($solution->extensions);
            $zip = new ZipArchive();
            if (!$zip->open($zipFile, ZipArchive::RDONLY)) {
                echo "Unable to open $zipFile archive!\n";
                continue;
            }

            $count = $zip->count();
            $pattern = $extensions[0] === '*' ? null : '/[.](' . join('|', $extensions) . ')$/';
            for ($i = 0; $i < $count; ++$i) {
                $name = $zip->getNameIndex($i);
                if ($pattern) {
                    $regres = preg_match($pattern, $name);
                    if ($regres === false) {
                        echo "$pattern !~ $name\n";
                    }
                    if (!$regres) continue;
                }

                $content = $zip->getFromIndex($i);
                $locs = $this->getLocs($content ? $content : '');
                if ($content) {
                    $res[$solution->exercise_id] = $res[$solution->exercise_id] ?? [];
                    $res[$solution->exercise_id][$solution->runtime_environment_id] = $res[$solution->exercise_id][$solution->runtime_environment_id]
                        ?? [0, 0, 0, PHP_INT_MAX];
                    $res[$solution->exercise_id][$solution->runtime_environment_id][0] += 1;
                    $res[$solution->exercise_id][$solution->runtime_environment_id][1] += $locs;
                    $res[$solution->exercise_id][$solution->runtime_environment_id][2] += ($locs * $locs);
                    $res[$solution->exercise_id][$solution->runtime_environment_id][3] = min($locs, $res[$solution->exercise_id][$solution->runtime_environment_id][3]);
                }
            }
            $zip->close();
        }

        if ($type === 'assignment') {
            echo "id,runtime,solution_files,solution_min_locs,solution_avg_locs,solution_locs_stdev\n";
        } else {
            echo "id,runtime,refs_files,refs_min_locs,refs_avg_locs,refs_locs_stdev\n";
        }
        foreach ($res as $eid => $exercise) {
            foreach ($exercise as $rte => $stats) {
                if ($stats[0] > 0) {
                    $min = $stats[3];
                    $mean = (float)$stats[1] / (float)$stats[0];
                    $mean2 = (float)$stats[2] / (float)$stats[0];
                    $stdev = sqrt($mean2 - ($mean * $mean));
                    echo "$eid,$rte,$stats[0],$min,$mean,$stdev\n";
                }
            }
        }
    }
}
