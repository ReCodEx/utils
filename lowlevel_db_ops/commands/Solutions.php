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

    public function migrateJobConfigs($newStorageRoot)
    {
        if (!is_dir($newStorageRoot)) {
            throw new Exception("Path $newStorageRoot is not an existing directory.");
        }

        $counter = 0;
        $notFound = 0;
        $types = ['student' => 'assignment_solution_submission', 'reference' => 'reference_solution_submission'];
        foreach ($types as $type => $table) {
            $submissions = $this->db->query("SELECT * FROM $table");
            foreach ($submissions as $submission) {
                ++$counter;
                echo $submission->id, " ";
                if (!file_exists($submission->job_config_path)) {
                    ++$notFound;
                    echo "FILE $submission->job_config_path NOT FOUND!\n";
                    continue;
                }

                $dst = "$newStorageRoot/job_configs/$submission->subdir/{$submission->id}_$type.yml";
                echo "copied to $dst ... ";
                @mkdir(dirname($dst), 0775, true);
                $res = is_dir(dirname($dst)) && copy($submission->job_config_path, $dst);
                echo $res ? "OK\n" : "FAILED\n";
            }
        }

        echo "Total $counter records processed, $notFound files were not found.\n";
    }


    public function migrateSubmissionResults($oldServerRoot, $newStorageRoot)
    {
        if (!is_dir($oldServerRoot)) {
            throw new Exception("Path $oldServerRoot is not an existing directory.");
        }

        if (!is_dir($newStorageRoot)) {
            throw new Exception("Path $newStorageRoot is not an existing directory.");
        }

        $counter = 0;
        $notFound = 0;
        $types = ['student' => 'assignment_solution_submission', 'reference' => 'reference_solution_submission'];
        foreach ($types as $type => $table) {
            $submissions = $this->db->query("SELECT * FROM $table");
            foreach ($submissions as $submission) {
                ++$counter;
                echo $submission->id, " ";
                $src = preg_replace('#^https?://[^/]+#', $oldServerRoot, $submission->results_url);

                if (!file_exists($src)) {
                    ++$notFound;
                    echo "FILE $src NOT FOUND!\n";
                    continue;
                }

                $dst = "$newStorageRoot/results/$submission->subdir/{$submission->id}_$type.zip";
                echo "copied to $dst ... ";
                @mkdir(dirname($dst), 0775, true);
                $res = is_dir(dirname($dst)) && copy($submission->job_config_path, $dst);
                echo $res ? "OK\n" : "FAILED\n";
            }
        }

        echo "Total $counter records processed, $notFound files were not found.\n";
    }


    public function migrateSolutionFiles($newStorageRoot)
    {
        if (!is_dir($newStorageRoot)) {
            throw new Exception("Path $newStorageRoot is not an existing directory.");
        }

        $counter = 0;
        $notFound = 0;

        $solutions = $this->db->fetchPairs("SELECT id, subdir FROM solution");
        foreach ($solutions as $id => $subdir) {
            $zipPath = "$newStorageRoot/solutions/$subdir/${id}.zip";
            @mkdir(dirname($zipPath), 0775, true);
            if (!is_dir(dirname($zipPath))) {
                echo "ERROR: Cannot make directory for $zipPath!\n";
                continue;
            }

            echo "$id  ($zipPath)\n";
            $files = $this->db->query("SELECT * FROM uploaded_file WHERE solution_id = ? AND discriminator == 'solutionfile'", $id);
            if (!$files) {
                touch($zipPath);
                continue;
            }

            $zip = new ZipArchive();
            $res = $zip->open($zipPath, ZipArchive::OVERWRITE | ZipArchive::CREATE);
            if ($res !== true) {
                throw new Exception("Cannot open ZIP ($res) $zipPath");
            }

            foreach ($files as $file) {
                echo "\t$file->name ";
                ++$counter;
                if (!file_exists($file->local_file_path)) {
                    ++$notFound;
                    echo "FILE $file->local_file_path NOT FOUND!\n";
                    continue;
                }

                if (!$zip->addFile($file->local_file_path, $file->name)) {
                    throw new Exception("Unable to add file $file->name to $zipPath");
                }

                echo "OK\n";
            }

            if (!$zip->close()) {
                throw new Exception("Cannot close zip $zipPath");
            }
        }

        echo "Total $counter records processed, $notFound files were not found.\n";
    }
}
