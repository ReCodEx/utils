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
			if (empty($supFiles[$file])) $missingFiles[] = $file;
		}
		return $missingFiles;
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
			}
			else
				echo '.';
		}
		echo "\n\n";

		foreach ($failed as $exercise) {
			echo "Integrity failed in exercise ", $exercise->id, ": ", $this->getExerciseName($exercise->id), "\n";
			echo "Author:", $this->getUserName($exercise->author_id), "\n";
			echo "Files missing: ", join(", ", $missingFiles[$exercise->id]), "\n";
			echo "-----------------------\n\n";
		}
	}
}
