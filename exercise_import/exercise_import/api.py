import requests
from json import JSONDecodeError
import logging

class ApiClient:
    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.headers = {"Authorization": "Bearer " + api_token}

    def post(self, url, files={}, data={}):
        response = requests.post(self.api_url + "/v1/" + url, files=files, json=data, headers=self.headers)
        return self.extract_payload(response)

    def get(self, url):
        response = requests.get(self.api_url + "/v1/" + url, headers=self.headers)
        return self.extract_payload(response)

    def get_runtime_environments(self):
        return self.get("/runtime-environments")

    def get_pipelines(self):
        return self.get("/pipelines")

    def get_exercise(self, exercise_id):
        return self.get("/exercises/{}".format(exercise_id))

    def get_exercises(self):
        return self.get("/exercises")

    def get_reference_solutions(self, exercise_id):
        return self.get("/reference-solutions/exercise/{}".format(exercise_id))

    def get_reference_solution_evaluations(self, solution_id):
        return self.get("/reference-solutions/{}/evaluations".format(solution_id))

    def upload_file(self, filename, stream):
        return self.post("/uploaded-files", files={"file": (filename, stream)})

    def get_uploaded_file_data(self, file_id):
        return self.get("/uploaded-files/{}".format(file_id))

    def create_exercise(self, group_id):
        return self.post("/exercises", data={
            "groupId": group_id
        })

    def add_exercise_attachments(self, exercise_id, file_ids):
        self.post("/exercises/{}/attachment-files".format(exercise_id), data={"files": file_ids})

    def get_exercise_attachments(self, exercise_id):
        return self.get("/exercises/{}/attachment-files".format(exercise_id))

    def add_exercise_files(self, exercise_id, file_ids):
        self.post("/exercises/{}/supplementary-files".format(exercise_id), data={"files": file_ids})

    def get_exercise_files(self, exercise_id):
        return self.get("/exercises/{}/supplementary-files".format(exercise_id))

    def set_exercise_score_config(self, exercise_id, score_config: str):
        return self.post("/exercises/{}/score-config".format(exercise_id), data={"scoreConfig": score_config})

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

    def set_exercise_tests(self, exercise_id, tests):
        self.post("/exercises/{}/tests".format(exercise_id), data={"tests": tests})

    def get_exercise_tests(self, exercise_id):
        return self.get("/exercises/{}/tests".format(exercise_id))

    def update_limits(self, exercise_id, environment_id, limits):
        self.post("/exercises/{}/environment/{}/limits".format(exercise_id, environment_id), data={"limits": limits})

    def evaluate_reference_solutions(self, exercise_id):
        self.post("/reference-solutions/exercise/{}/evaluate".format(exercise_id), data={})

    @staticmethod
    def extract_payload(response):
        try:
            json = response.json()
        except JSONDecodeError:
            logging.error("Loading JSON response failed, see full response below:")
            logging.error(response.text)
            raise RuntimeError("Loading JSON response failed")

        if not json["success"]:
            raise RuntimeError("Received error from API: " + json["msg"])

        return json["payload"]

