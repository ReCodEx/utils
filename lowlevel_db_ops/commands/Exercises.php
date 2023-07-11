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
}
