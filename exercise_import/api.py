import requests

class ApiClient:
    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.headers = {"Authorization": "Bearer " + api_token}

    def post(self, url, files={}, data={}):
        response = requests.post(self.api_url + "/v1/" + url, files=files, data=self.formdata_encode(data), headers=self.headers)
        return self.extract_payload(response)

    def get(self, url):
        response = requests.get(self.api_url + "/v1/" + url, headers=self.headers)
        return self.extract_payload(response)

    def get_runtime_environments(self):
        return self.get("/runtime-environments")

    def get_pipelines(self):
        return self.get("/pipelines")

    def upload_file(self, filename, stream):
        return self.post("/uploaded-files", files={filename: stream})

    def get_uploaded_file_data(self, file_id):
        return self.get("/uploaded-files/{}".format(file_id))

    def create_exercise(self, group_id):
        return self.post("/exercises", {
            "groupId": group_id
        })

    def add_exercise_attachments(self, exercise_id, file_ids):
        self.post("/exercises/{}/additional-files".format(exercise_id), data={"files": file_ids})

    def add_exercise_files(self, exercise_id, file_ids):
        self.post("/exercises/{}/supplementary-files".format(exercise_id), data={"files": file_ids})

    def get_exercise_files(self, exercise_id):
        return self.get("/exercises/{}/supplementary-files".format(exercise_id))

    def update_exercise(self, exercise_id, details):
        self.post('/exercises/{}'.format(exercise_id), data=details)

    def create_reference_solution(self, exercise_id, data):
        return self.post('/reference-solutions/exercise/{}'.format(exercise_id), data=data)

    def update_environment_configs(self, exercise_id, configs):
        self.post("/exercises/{}/environment-configs".format(exercise_id), data={
            "environmentConfigs": configs
        })

    def update_exercise_config(self, exercise_id, config):
        self.post("/exercises/{}/config".format(exercise_id), data={"config": config})

    @staticmethod
    def extract_payload(response):
        json = response.json()
        if not json["success"]:
            raise RuntimeError("Received error from API: " + json["msg"])

        return json["payload"]

    @staticmethod
    def formdata_encode(data):
        """
        >>> ApiClient.formdata_encode({})
        {}
        >>> ApiClient.formdata_encode({"hello": 2, "world": 42})
        {'hello': 2, 'world': 42}
        >>> ApiClient.formdata_encode({"data": [{"hello": 2, "world": 42}, {"how": 10, "are": 20, "you": 30}]})
        {'data[0][hello]': 2, 'data[0][world]': 42, 'data[1][how]': 10, 'data[1][are]': 20, 'data[1][you]': 30}
        """

        def inner(prefix, data, wrap_key=False):
            if isinstance(data, list) or isinstance(data, set):
                data = dict(enumerate(data))

            if not isinstance(data, dict):
               yield prefix, data
               return

            for key, value in data.items():
                if wrap_key:
                    key = "[{}]".format(key)
                yield from inner(prefix + key, value, True)

        return dict(inner("", data))

