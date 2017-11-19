<?php

/*
 * This is not a ready-to-use script. Just a concept, which may become basis for other script(s).
 */


class ReCodEx_API
{
	private $base_url;
	private $jwt;

	private $last_response = null;
	private $last_response_headers = null;
	private $last_info = null;
	private $last_errno = null;
	private $last_error = null;

	public function __get($name)
	{
		if (isset($this->$name))
			return $this->$name;
		else
			return null;
	}

	
	public function __construct(string $base_url, string $jwt = '')
	{
		if (!$base_url)
			throw new Exception("Base URL cannot be empty.");
		if (substr($base_url, -1, 1) != '/') $base_url .= '/';
		$this->base_url = $base_url;

		$this->set_jwt($jwt);
	}

	public function set_jwt(string $jwt = '')
	{
		if (!preg_match('#^[-A-Za-z0-9+/=._]*$#', $jwt))
			throw new Exception("Given JWT token is not valid.");

		$this->jwt = $jwt;
	}


	public function get_last_header($header)
	{
		$header = strtolower($header);
	}

	private function process_response()
	{
		$this->last_response_headers = null;

		if ($this->last_errno == 0 && $this->last_info && $this->last_info['header_size']) {
			$size = $this->last_info['header_size'];
			if (strlen($this->last_response) < $size)
				throw new Exception("Header size is expected to be larger than the whole size of the response.");
			
			$this->last_response_headers = [];
			foreach (explode("\n", substr($this->last_response, 0, $size)) as $header) {
				$header = trim($header);
				$header = explode(':', $header, 2);
				if (!$header || count($header) != 2) continue;
				list($name, $value) = $header;
				$this->last_response_headers[strtolower(trim($name))] = trim($value);
			}

			$this->last_response = substr($this->last_response, $size);
			if (strpos(strtolower($this->last_response_headers['content-type']), 'application/json') !== false)
				$this->last_response = json_decode($this->last_response);

		}

		if ($this->last_errno == 0 && $this->last_info && $this->last_info['http_code'] == 403) {
			// Unauthorized
			$this->jwt = null;
		}

		if ($this->last_errno == 0 && $this->last_info && $this->last_info['http_code'] == 200)
			return $this->last_response;
		else
			return false;
	}

	public function query(string $endpoint, string $method = 'GET', array $data = [], bool $jsonBody = false)
	{
		$ch = curl_init();	
		curl_setopt($ch, CURLOPT_URL, $this->base_url . $endpoint);
		curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
		curl_setopt($ch, CURLOPT_HEADER, true);
		curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
//		curl_setopt($ch, CURLINFO_HEADER_OUT, true);	

		$headers = [];

		/**
		 * Set selected method and possibly the body data. 
		 */
		$method = strtoupper($method);
		switch ($method) {
			case 'DELETE':
				curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
				// fall througt to GET req ...
			case 'GET':
				if ($data)
					throw new Exception("$method requests does not have any additional data.");				
				break;

			case 'POST':
				if ($jsonBody)
					throw new Exception("JSON body not implemented yet.");
				curl_setopt($ch, CURLOPT_POST, 1);
				curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
				$headers[] = "Content-Type: multipart/form-data";
				break;
		}
		
		/**
		 * Include JWT security token, if provided.
		 */
		if ($this->jwt) {
			$headers[] = "Authorization: Bearer $this->jwt";
		}


		/**
		 * Run request, collect results ...
		 */
		curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

		$this->last_response = curl_exec($ch);
		$this->last_errno = curl_errno($ch);
		$this->last_error = curl_error($ch);
		$this->last_info = curl_getinfo($ch);

//		echo curl_getinfo($ch, CURLINFO_HEADER_OUT), "\n\n";

		curl_close($ch);

		return $this->process_response();
	}


	public function resubmit_assignment_solution($id, $debug = false)
	{
		return $this->query("assignment-solutions/$id/resubmit", "POST", [
			'debug' => (bool)$debug,
			'private' => false,
		]);
	}
}


exit; // prevent accidental usage


$api = new ReCodEx_API("https://recodex.mff.cuni.cz/api/v1/","placeyourJWThere");


// example of utilization
$counter = 0;
foreach (file('./solutions.txt', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $id) {
	$id = trim($id);
	if (!preg_match('/^[-0-9a-fA-F]{36}$/', $id)) continue;

	++$counter;
	echo "Resubmitting #$counter: $id ... ";
	$res = $api->resubmit_assignment_solution($id);
	$code = (int)$api->last_info['http_code'];
	echo $code, "\n";

	if ($code != 200 || empty($res->success)) {
		if ($code == 404) continue;
		var_dump($res);
		var_dump($api);
		exit(1);
	}
}
