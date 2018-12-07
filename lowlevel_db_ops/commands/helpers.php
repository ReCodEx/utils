<?php

function getLocaleSafe(array $localizedText, $locale = 'en')
{
	if (!$localizedText) return '??';
	return empty($localizedText[$locale]) ? reset($localizedText) : $localizedText[$locale];
}

function harvestConfigVariables($config)
{
	$res = [];
	// Let's swine up some PHP...
	if (empty($config['tests']) || !is_array($config['tests'])) return [];
	foreach ($config['tests'] as $test) {
		if (empty($test['environments']) || !is_array($test['environments'])) continue;
		foreach ($test['environments'] as $environment) {
			if (empty($environment['pipelines']) || !is_array($environment['pipelines'])) continue;
			foreach ($environment['pipelines'] as $pipeline) {
				if (!empty($pipeline['variables']) && is_array($pipeline['variables'])) {
					$res = array_merge($res, $pipeline['variables']);
				}
			}
		}
	}
	return $res;
}


function harvestRemoteFilesFromVariables($variables)
{
	$files = [];
	foreach ($variables as $variable) {
		$value = $variable['value'];
		if (!$value) continue;

		if ($variable['type'] === 'remote-file') {
			$files[$value] = true;
		} elseif ($variable['type'] === 'remote-file[]') {
			foreach ($value as $v) $files[$v] = true;
		}
	}
	return array_keys($files);
}

