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


    public function migrateAttachmentFiles($newStorageRoot)
    {
        if (!is_dir($newStorageRoot)) {
            throw new Exception("Path $newStorageRoot is not an existing directory.");
        }

        $counter = 0;
        $notFound = 0;

        $files = $this->db->query("SELECT * FROM uploaded_file WHERE discriminator = 'attachmentfile'");
        foreach ($files as $file) {
            ++$counter;
            echo "$counter: $file->id ";

            if (!$file->local_file_path || !file_exists($file->local_file_path)) {
                ++$notFound;
                echo "FILE $file->local_file_path NOT FOUND!\n";
                continue;
            }

            $dst = "$newStorageRoot/attachments/user_$file->user_id/{$file->id}_$file->name";
            echo "copied to $dst ... ";
            @mkdir(dirname($dst), 0775, true);
            $res = is_dir(dirname($dst)) && copy($file->local_file_path, $dst);
            echo $res ? "OK\n" : "FAILED\n";
        }

        echo "Total $counter records processed, $notFound files were not found.\n";
    }
}
