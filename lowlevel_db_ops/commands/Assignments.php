<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Assignments extends BaseCommand
{


	private function verifyAssignmentFiles($assignment)
	{
		$config = $this->getExerciseConfig($assignment->exercise_config_id);
		$variables = harvestConfigVariables($config);
		$varFiles = harvestRemoteFilesFromVariables($variables);
		$supFiles = $this->getAssignmentSupplementaryFiles($assignment->id);
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
		$assignments = $this->getAssignments();
		echo "Checking ", $assignments->getRowCount(), " assignments..";
		$failed = [];
		$missingFiles = [];
		foreach ($assignments as $assignment) {
			$res = $this->verifyAssignmentFiles($assignment);
			if ($res) {
				$failed[] = $assignment;
				$missingFiles[$assignment->id] = $res;
				echo 'X';
			}
			else
				echo '.';
		}
		echo $failed ? (" " . count($failed) . " failed") : "OK";
		echo "\n\n";
		if (!$failed) return;

		$relevant = 0;
		foreach ($failed as $assignment) {
			$deadline = $assignment->allow_second_deadline ? $assignment->second_deadline : $assignment->first_deadline;
			if ($deadline->diff(new DateTime())->days > 68) continue;	// too old
			
			++$relevant;
			echo "Integrity failed in assignment ", $assignment->id,
				" of exercise ", $assignment->exercise_id, ": ", $this->getAssignmentName($assignment->id), "\n";
			echo "Last deadline: ", $deadline->format('j.n.Y H:i'), "\n";
			echo "In group ", $assignment->group_id, ": ", $this->getGroupName($assignment->group_id), "\n";
			echo "Files missing: ", join(", ", $missingFiles[$assignment->id]), "\n";
			echo "-----------------------\n\n";
		}
		echo "$relevant relevant failures reported\n";
	}
}
