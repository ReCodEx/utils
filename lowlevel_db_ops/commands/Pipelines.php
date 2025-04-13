<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Pipelines extends BaseCommand
{
	public function boxesStats()
	{
		$pipelines = $this->getPipelineConfigs();
		$stats = [];
		foreach ($pipelines as $id => $pipeline) {
			$config = yaml_parse($pipeline);
			if ($config === false) {
				echo $config, "\n";
				return;
			}

			$boxes = $config['boxes'] ?? [];
			foreach ($boxes as $box) {
				$type = $box['type'] ?? null;
				$name = $box['name'] ?? null;
				if (!$type || !$name) {
					echo "Warning: pipeline config $id has box without name or type\n";
					echo json_encode($box), "\n";
				}
				if (!array_key_exists($type, $stats)) {
					$stats[$type] = [];
				}
				$stats[$type][$name] = ($stats[$type][$name] ?? 0) + 1;
			}
		}

		$types = array_keys($stats);
		sort($types);
		foreach ($types as $type) {
			echo $type, "\t", array_sum($stats[$type]), "\t", join(', ', array_keys($stats[$type])), "\n";
		}
	}
}
