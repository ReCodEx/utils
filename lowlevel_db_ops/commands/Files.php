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
}
