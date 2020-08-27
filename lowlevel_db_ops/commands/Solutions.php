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
}
