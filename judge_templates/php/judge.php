#!/usr/bin/php -c/usr/etc
<?php

array_shift($argv);
list($referenceFile, $resultFile) = $argv;

$errors = [];

/*
 * Check the results....
 */


// Print the judgement.
if ($errors) {
	echo "0.0\n";
	echo join("\n", $errors), "\n";
	exit(1);
}
else {
	echo "1.0\n";
	exit(0);
}
