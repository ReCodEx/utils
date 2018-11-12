<?php
/*
pro dany seznam exercises:
uz to dobehlo?
porovnej posledni 2 evaluations
*/

//$exercises = shell_exec("recodex exercises list_all --yaml");
//echo $exercises;

define('UUID_REGEX', '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}');

function action_request($query)
{
	$res = trim(shell_exec("recodex exercises $query"));
	if ($res) {
		echo "$res\n";
		exit(1);
	}
}

function get_json_request($query)
{
	$text = shell_exec("recodex exercises $query --json");
	$json = json_decode($text, false);
	if ($json === null) {
		echo $text;
		exit(1);
	}
	return $json;
}


/*
 * API calls via recodex-cli...
 */
function get_ref_solutions($exerciseId)
{
	return get_json_request("get_ref_solutions $exerciseId");
}


function get_ref_solution_evaluations($solutionId)
{
	return get_json_request("get_ref_solution_evaluations $solutionId");
}


function delete_ref_solution_evaluation($evaluationId)
{
	echo "Removing evaluation $evaluationId...\n";
	action_request("delete_ref_solution_evaluation $evaluationId");
}


function resubmit_ref_solution($solutionId)
{
	echo "Re-submitting solution $solutionId...\n";
	action_request("resubmit_ref_solution $solutionId");
}


/*
 * Processing Functions
 */

function loadSolutions($exerciseIds)
{
	echo "Loading ref. solutions..";
	$solutions = [];
	foreach ($exerciseIds as $exerciseId) {
		$exerciseSolutions = get_ref_solutions($exerciseId);
		foreach ($exerciseSolutions as $s)
			$solutions[$s->id] = $s;
		echo ".";
	}
	echo ' ', count($solutions), " loaded.\n";
	return $solutions;
}


function loadEvaluations($solutions)
{
	echo "Loading evaluations..";
	$evaluations = [];
	foreach ($solutions as $solutionId => $solution) {
		$solutionEvaluations = get_ref_solution_evaluations($solutionId);
		foreach ($solutionEvaluations as $e)
			$evaluations[$e->id] = $e;
		echo ".";
	}
	echo ' ', count($evaluations), " loaded.\n";
	return $evaluations;
}

function sortEvaluations(&$evaluations)
{
	usort($evaluations, function ($a, $b) {
		return $b->submittedAt - $a->submittedAt;
	});
}


function sortTests(&$tests)
{
	usort($tests, function ($a, $b) {
		if ($a->testName == $b->testName) return 0;
		return $a->testName > $b->testName ? 1 : -1;
	});
}


function compareTestResults($olderTest, $latestTest)
{
	// Time limits
	if ($olderTest->wallTimeExceeded || $olderTest->cpuTimeExceeded || $latestTest->wallTimeExceeded || $latestTest->cpuTimeExceeded) {
		if ($olderTest->wallTimeExceeded == $latestTest->wallTimeExceeded && $olderTest->cpuTimeExceeded == $latestTest->cpuTimeExceeded)
			return '';
		
			if (($olderTest->cpuTimeRatio == 0 || $olderTest->cpuTimeRatio > 0.9)
				&& ($olderTest->wallTimeRatio == 0 || $olderTest->wallTimeRatio > 0.9)
				&& ($latestTest->cpuTimeRatio == 0 || $latestTest->cpuTimeRatio > 0.9)
				&& ($latestTest->wallTimeRatio == 0 || $latestTest->wallTimeRatio > 0.9))
				return '';
			
			return "time limit exceeded";
	}

	// Memory limits
	if ($olderTest->memoryExceeded || $latestTest->memoryExceeded) {
		if ($olderTest->memoryExceeded == $latestTest->memoryExceeded)
			return '';
		
			if ($olderTest->memoryRatio > 0.9 && $latestTest->memoryRatio > 0.9)
				return '';
			
			return "memory limit exceeded";
	}

	// Correctness
	$simpleChecks = [	// property name => error message (if it does not match)
		'testName' => "test names mismatch",
		'exitCode' => "exit codes mismatch",
		'score' => "scores mismatch",
		'judgeLog' => "judge logs mismatch",
	];

	foreach ($simpleChecks as $prop => $error) {
		if ($olderTest->$prop != $latestTest->$prop) {
			return $error;
		}
	}
	
	return '';
}


function compareEvaluations($older, $latest)
{
	if (empty($older->evaluation) || empty($latest->evaluation)) {
		return "evaluation missing";
	}

	if ($older->evaluation->initFailed || $latest->evaluation->initFailed) {
		return ($older->evaluation->initFailed == $latest->evaluation->initFailed) ? 'OK' : 'init failed';
	}

	$olderTests = $older->evaluation->testResults;
	$latestTests = $latest->evaluation->testResults;
	sortTests($olderTests);
	sortTests($latestTests);

	if (count($olderTests) != count($latestTests)) {
		return "tests-count mismatch";
	}

	foreach ($olderTests as $idx => $olderTest) {
		$res = compareTestResults($olderTest, $latestTests[$idx]);
		if ($res) {
			echo "#$idx " . $olderTest->testName . " - ";
			return $res;
		}
	}

	return "OK";
}



/*
 * CLI Actions
 */
function cli_help()
{
	echo "Usage: php evaluation.php <exerciseIdsFile> <action> [ action specific params ]\n";
	echo "Actions:\n";
	echo "  resubmit_all   - resubmit all solutions\n";
	echo "  wait           - wait for all submissions to complete\n";
	echo "  remove_all     - remove all evaluations except for the latest\n";
	echo "  remove_latest  - remove latest evaluation for each solution (if any exists)\n";
	echo "  grand_check    - check last two evaluations of each solution that they have the same results\n";
	echo "  stats          - compute basic statistics of solutions and evaluations\n";
}


function cli_resubmit_all($exerciseIds, $argv)
{
	$solutions = loadSolutions($exerciseIds);
	foreach ($solutions as $solutionId => $solution)
		resubmit_ref_solution($solutionId);
}


function cli_wait($exerciseIds, $argv)
{
	$solutions = loadSolutions($exerciseIds);

	while ($solutions) {
		$pending = 0;
		$solutions = array_filter($solutions, function($solution) use (&$pending) {
			$evaluations = array_filter(get_ref_solution_evaluations($solution->id), function ($evaluation) {
				return $evaluation->evaluationStatus == 'work-in-progress';
			});
			$pending += count($evaluations);
			return count($evaluations) > 0;
		});
		echo "Still pending: $pending\n";
		sleep(min($pending, 10));
	}
}


function cli_remove_all($exerciseIds, $argv)
{
	$solutions = loadSolutions($exerciseIds);
	foreach ($solutions as $solution) {
		$evaluations = get_ref_solution_evaluations($solution->id);
		if (count($evaluations) > 1) {
			sortEvaluations($evaluations);
			array_shift($evaluations);	// spare the first (latest) one
			foreach ($evaluations as $evaluation)
				delete_ref_solution_evaluation($evaluation->id);
		}
	}
}


function cli_remove_latest($exerciseIds, $argv)
{
	$solutions = loadSolutions($exerciseIds);
	$evaluations = loadEvaluations($solutions);
	foreach ($solutions as $solution) {
		$evaluations = get_ref_solution_evaluations($solution->id);
		if (count($evaluations) > 1) {
			sortEvaluations($evaluations);
			$evaluation = reset($evaluations);
			delete_ref_solution_evaluation($evaluation->id);
		}
	}
}


function cli_grand_check($exerciseIds, $argv)
{
	$solutions = loadSolutions($exerciseIds);
	$results = [];
	foreach ($solutions as $solution) {
		$evaluations = get_ref_solution_evaluations($solution->id);
		if (count($evaluations) > 1) {
			sortEvaluations($evaluations);
			$latest = array_shift($evaluations);
			$older = array_shift($evaluations);

			echo "Checking $solution->id of $solution->exerciseId ... ";
			$res = compareEvaluations($older, $latest);
			echo "$res\n";

			if (empty($results[$res])) $results[$res] = 0;
			$results[$res] += 1;
		}
		else
			echo "$solution->id has less than two evaluations\n";

	}

	echo "\nFinished\n";
	foreach ($results as $res => $count)
		echo "  $res: $count\n";
}


function cli_stats($exerciseIds, $argv)
{
	$solutions = loadSolutions($exerciseIds);
	$evaluations = loadEvaluations($solutions);

	$rts = [];
	foreach ($solutions as $solution) {
		@$rts[$solution->runtimeEnvironmentId] += 1;
	}

	$correct = 0;
	$partiallyCorrect = 0;
	$partiallyCorrectScoreSum = 0.0;
	$wrong = 0;
	$notAvailable = [];
	$statuses = [];
	$oldest = time() + 86400;
	$newest = 0;
	
	foreach ($evaluations as $evaluation) {
		if (!empty($evaluation->evaluation)) {
			if ($evaluation->evaluation->score >= 1.0) {
				++$correct;
			} elseif ($evaluation->evaluation->score <= 0.0) {
				++$wrong;
			} else {
				++$partiallyCorrect;
				$partiallyCorrectScoreSum += $evaluation->evaluation->score;
			}
		} else {
			$notAvailable[] = $evaluation;
		}

		@$statuses[$evaluation->evaluationStatus] += 1;
		$oldest = min($oldest, (int)$evaluation->submittedAt);
		$newest = max($newest, (int)$evaluation->submittedAt);
	}

	echo "\nSolutions: ", count($solutions), "\n";
	echo "Runtime environments:\n";
	foreach ($rts as $rt => $count) echo " |- $rt: $count\n";
	echo "\n";
	echo "Evaluations: ", count($evaluations), "\n";
	echo "Correct: ", $correct, "\n";
	if ($partiallyCorrect > 0)
		echo "Partially correct: ", $partiallyCorrect, " with avg. correctness ", round($partiallyCorrectScoreSum*100/$partiallyCorrect, 1), "%\n";
	echo "Wrong: ", $wrong, "\n";
	echo "Not available (yet): ", count($notAvailable), "\n";
	foreach ($notAvailable as $na) {
		$solution = $solutions[$na->referenceSolutionId];
		echo "  exercise $solution->exerciseId, ref. solution $solution->id\n";
	}
	echo "Oldest submit: ", date('d.m.Y H:i:s', $oldest), "\n";
	echo "Newest submit: ", date('d.m.Y H:i:s', $newest), "\n";
	echo "Statuses:\n";
	foreach ($statuses as $status => $count) echo " |- $status: $count\n";
}





/*
 * Main Script
 */
try {
	array_shift($argv);
	$exerciseIdsFile = array_shift($argv);
	$action = array_shift($argv);

	echo "Loading '$exerciseIdsFile'... ";
	$exerciseIds = file($exerciseIdsFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
	if (!$exerciseIds) throw new Exception("Unable to load exercise IDs file '$exerciseIdsFile'.");
	$exerciseIds = array_filter($exerciseIds, function($id) {
		return preg_match('/^' . UUID_REGEX . '$/', $id);
	});
	echo count($exerciseIds), " exercise IDs loaded.\n";

	$fncName = "cli_$action";
	if (function_exists($fncName)) {
		$fncName($exerciseIds, $argv);
	} else {
		echo "Unknown action '$action'!\n";
		cli_help();
	}
}
catch (Exception $e) {
	echo "Error: ", $e->getMessage(), "\n";
	exit(1);
}
