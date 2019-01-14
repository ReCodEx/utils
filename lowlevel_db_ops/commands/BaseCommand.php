<?php


class BaseCommand
{
	protected $db;

	public function __construct($db)
	{
		$this->db = $db;
	}

	protected function getExerciseName($exerciseId, $locale = 'en')
	{
		return getLocaleSafe( $this->db->fetchPairs('SELECT le.locale, le.name FROM exercise_localized_exercise AS ele
			JOIN localized_exercise AS le ON le.id = ele.localized_exercise_id
			WHERE ele.exercise_id = ?', $exerciseId),
			$locale
		);
	}

	
	protected function getAssignmentName($assignmentId, $locale = 'en')
	{
		return getLocaleSafe( $this->db->fetchPairs('SELECT le.locale, le.name FROM assignment_localized_exercise AS ale
			JOIN localized_exercise AS le ON le.id = ale.localized_exercise_id
			WHERE ale.assignment_id = ?', $assignmentId),
			$locale
		);
	}

	
	protected function getGroupName($groupId, $locale = 'en')
	{
		return getLocaleSafe(
			$this->db->fetchPairs('SELECT locale, name FROM localized_group WHERE group_id = ?', $groupId),
			$locale);
	}

	protected function getUserName($userId)
	{
		return $this->db->fetchSingle("SELECT CONCAT(first_name, ' ', last_name) FROM user WHERE id = ?", $userId);
	}


	protected function getExercises()
	{
		return $this->db->query("SELECT * FROM exercise WHERE deleted_at IS NULL");
	}
	
	
	protected function getAssignments()
	{
		return $this->db->query("SELECT * FROM assignment WHERE deleted_at IS NULL");
	}
	
	
	protected function getExerciseConfig($configId)
	{
		$configYaml = $this->db->fetchSingle('SELECT config FROM exercise_config WHERE id = ?', $configId);
		return yaml_parse($configYaml);
	}

	
	protected function getAssignmentSupplementaryFiles($assignmentId)
	{
		return $this->db->fetchPairs('SELECT f.name, f.id FROM assignment_supplementary_exercise_file AS af
			JOIN uploaded_file AS f ON f.id = af.supplementary_exercise_file_id
			WHERE af.assignment_id = ?', $assignmentId);
	}

	protected function getExerciseSupplementaryFiles($exerciseId)
	{
		return $this->db->fetchPairs('SELECT f.name, f.id FROM exercise_supplementary_exercise_file AS ef
			JOIN uploaded_file AS f ON f.id = ef.supplementary_exercise_file_id
			WHERE ef.exercise_id = ?', $exerciseId);
	}


	protected function getGroupAdmins($groupId)
	{
		return $this->db->fetchPairs('SELECT u.id AS id, CONCAT(u.first_name, \' \', u.last_name) AS username
			FROM group_user AS gu JOIN user AS u ON gu.user_id = u.id WHERE gu.group_id = ?', $groupId);
	}
}
