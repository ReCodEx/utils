<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Groups extends BaseCommand
{

	private static function getGroupDepth($group, $groups)
	{
		$depth = 0;
		while ($group->parent_group_id && !empty($groups[$group->parent_group_id])) {
			$depth++;
			$group = $groups[$group->parent_group_id];
		}
		return $depth;
	}

	private static function parseExternalId($external_id)
	{
		$tokens = preg_split('/\s+/', $external_id);
		$courses = [];
		$years = [];
		$unknown = [];
		foreach ($tokens as $token) {
			$token = trim($token);
			if (empty($token)) {
				continue;
			}

			if (preg_match('/^[a-zA-Z]{3,5}[0-9]{2,3}$/', $token)) {
				$courses[] = $token;
			} elseif (preg_match('/^[0-9]{4}-[12]$/', $token)) {
				$years[] = $token;
			}
		}

		return [
			'course' => $courses,
			'year' => $years,
		];
	}

	private static function removeMatching($attributes, &$externalData)
	{
		foreach ($attributes as &$attribute) {
			if (!array_key_exists($attribute->key, $externalData)) {
				$attribute = null;  // unknown attribute, let's ignore it
				continue;
			}
			$index = array_search($attribute->value, $externalData[$attribute->key], true);
			if ($index !== false) {
				array_splice($externalData[$attribute->key], $index, 1);
				$attribute = null;
			}
		}
		return array_filter($attributes);
	}

    /*
     * Public interface
     */

    public function fillAttributes()
    {
		$service = 'sis-cuni';

		$groups = $this->getGroups(true);
		$counter = 0;
		$total = count($groups);
		foreach ($groups as $group) {
			++$counter;
			$name = $group->name_en ? $group->name_en : $group->name_cs;
			$depth = self::getGroupDepth($group, $groups);
			echo "$counter/$total: Processing group {$group->id} [$depth] ({$name}) ", ($group->is_organizational ? 'O' : ''), ($group->archived_at ? 'A' : ''), "\n";
			$externalData = self::parseExternalId($group->external_id);
			$bindings = array_values($this->getGroupSisBindings($group->id));
			$externalData['group'] = array_values($bindings);

			if ($externalData['course'] && (!$group->is_organizational || $bindings)) {
				echo "\tUnexpected course IDs: " . implode(", ", $externalData['course']) . " (will be ignored)\n";
				$externalData['course'] = [];

			}
			if ($bindings && $group->is_organizational) {
				echo "\tUnexpected group bindings: " . implode(", ", $bindings) . " (will be ignored)\n";
				$bindings = [];
			}

			$attributes = self::removeMatching($this->getGroupAttributes($group->id, $service), $externalData);

			// whatever's left in attributes needs to be removed
			foreach ($attributes as $attribute) {
				echo "\tRemoving attribute {$attribute->key} = {$attribute->value}\n";
				$this->db->query('DELETE FROM group_external_attribute WHERE id = ?', $attribute->id);
			}

			// whatever's left in externalData needs to be added
			foreach ($externalData as $key => $values) {
				foreach ($values as $value) {
					echo "\tAdding attribute $key = $value\n";
					$this->db->query('INSERT INTO `group_external_attribute` (`id`, `group_id`, `service`, `key`, `value`, `created_at`) VALUES (uuid(), ?, ?, ?, ?, ?)',
						$group->id, $service, $key, $value, new DateTime());
				}
			}
		}
    }
}
