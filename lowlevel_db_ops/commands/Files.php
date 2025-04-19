<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Files extends BaseCommand
{
    public function checkMissingAttachments($dir, $maxCount = null)
    {
		$files = $this->db->query('SELECT * FROM uploaded_file
			WHERE discriminator = ? ORDER BY uploaded_at DESC', 'attachmentfile');

		if (!$maxCount) {
			$maxCount = '32';
		}
		$maxCount = (int)$maxCount;
		$maxCount = max(1, $maxCount);

		$count = 0;
		$skipped = 0;
		foreach ($files as $file) {
			$path = "$dir/local/attachments/user_" . $file['user_id'] . '/' . $file['id'] . '_' . $file['name'];
			if (!file_exists($path)) {
				if ($skipped > 0) {
					echo "... $skipped file skipped ...\n";
					$skipped = 0;
				}
				echo "Missing file: $path\n";
				echo 'ID = ', $file['id'], "\tUser ID = ", $file['user_id'], "\tUploaded at: ", $file['uploaded_at'], "\n";
				if (++$count > $maxCount) {
					break;
				}
			} else {
				++$skipped;
			}
		}
    }

	private function fixSolutionsBatch($rows, $solutionIdx, &$fixedData)
	{
		if (!$rows) {
			return;
		}

		$solutionIds = array_map(function ($row) use ($solutionIdx) {
			return $row[$solutionIdx];
		}, $rows);
		$translation = $this->db->fetchPairs('SELECT id, assignment_id FROM assignment_solution WHERE id IN (?)', $solutionIds);
		foreach ($rows as $row) {
			$assignmentId = $translation[$row[$solutionIdx]];
			if (!$assignmentId) {
				echo "Unable to find assignment for solution ID {$row[$solutionIdx]}.\n";
				exit;
			}

			$row[] = $assignmentId;
			$fixedData[] = $row;
		}
	}

	public function fixSolutionsManifest($file, $separator = ',', $solutionCol = 'solution_id', $assignmentCol = 'assignment_id')
	{
		// load
		echo "Loading manifest file '$file'...\n";
		$fp = fopen($file, 'r');
		$header = fgetcsv($fp, 65536, $separator);
		$headerIndex = array_flip($header);
		if (array_key_exists($assignmentCol, $headerIndex)) {
			echo "Assignment column '$assignmentCol' already present in the manifest.\n";
			return;
		}
		if (!array_key_exists($solutionCol, $headerIndex)) {
			echo "Solution column '$solutionCol' not found in the manifest, unable to proceed.\n";
			return;
		}

		$data = [];
		$counter = 1;
		while (($row = fgetcsv($fp, 65536, $separator)) !== false) {
			++$counter;
			if (count($row) !== count($header)) {
				echo "Row #$counter has different number of columns than the header!\n";
				return;
			}
			$data[] = $row;
		}
		fclose($fp);

		// fix
		echo "Fixing data...\n";
		$fixedData = [];
		$solutionIdx = $headerIndex[$solutionCol];

		$batch = [];
		foreach ($data as $row) {
			$batch[] = $row;
			if (count($batch) >= 20) {
				$this->fixSolutionsBatch($batch, $solutionIdx, $fixedData);
				$batch = [];
			}
		}
		$this->fixSolutionsBatch($batch, $solutionIdx, $fixedData);

		// save
		echo "Saving fixed data back to $file ...\n";
		$fp = fopen($file, 'w');
		$header[] = $assignmentCol;
		fputcsv($fp, $header, $separator);
		foreach ($fixedData as $row) {
			fputcsv($fp, $row, $separator);
		}
		fclose($fp);
	}
}
