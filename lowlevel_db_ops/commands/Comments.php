<?php

require_once(__DIR__ . '/BaseCommand.php');
require_once(__DIR__ . '/helpers.php');


class Comments extends BaseCommand
{
	public function getText($id)
	{
		$res = [ 'text' =>  trim($this->getCommentText($id)) ];
		echo json_encode($res, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
	}
}
