<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Users extends BaseCommand
{
	public function replaceInLog()
	{
		$users = [];
        // read CSV log from stdin
        $fp = fopen('php://stdin', 'r');
        while (($row = fgetcsv($fp)) !== false) {
            $userId = $row[0];
			if (!array_key_exists($userId, $users)) {
				$name = $this->getUserName($userId);
				$name .= str_pad('', 36 - mb_strlen($name, 'UTF-8'), ' ');
				$users[$userId] = $name;
			}
			$row[0] = $users[$userId];
            echo join(',', $row), "\n";
        }

        fclose($fp);

	}
}
