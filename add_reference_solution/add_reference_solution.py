#!/usr/bin/env python3

import requests
import argparse
import os
import json

API_BASE = "https://recodex.projekty.ms.mff.cuni.cz:4040/v1"
UPLOAD_FILE_ENDPOINT = API_BASE + "/uploaded-files"
ADD_REFERENCE_ENDPOINT = API_BASE + "/reference-solutions/{id}"
EVALUATE_REFERENCE_ENDPOINT = API_BASE + "/reference-solutions/{exerciseId}/evaluate/{id}"


parser = argparse.ArgumentParser()
parser.add_argument('-t', '--token', help="Token used for authorization", default="")
parser.add_argument('-f', '--file', help="Path to file to upload", default="")
parser.add_argument('-e', '--exercise', help="ID of exercise this file belongs to", default="")
parser.add_argument('-n', '--note', help="Note for the reference solution", default="")
parser.add_argument('-r', '--runtime', help="ID of exercise runtime", default="")
parser.add_argument('-g', '--hwgroup', help="Hardware group for evaluation", default="group1")


def upload_file(headers, file):
    filename = os.path.basename(file)
    files = {filename: open(file, 'rb')}
    response = requests.post(UPLOAD_FILE_ENDPOINT, headers=headers, files=files)
    parsed_response = json.loads(response.text)
    # print(parsed_response)
    if not parsed_response["success"]:
        raise RuntimeError("File upload was not successful")
    return parsed_response["payload"]["id"]


def create_reference_solution(headers, fileId, exerciseId, note, runtimeId):
    data = {"note": note, "files": fileId, "runtime": runtimeId}
    response = requests.post(ADD_REFERENCE_ENDPOINT.format(id=exerciseId), headers=headers, data=data)
    parsed_response = json.loads(response.text)
    # print(parsed_response)
    if not parsed_response["success"]:
        raise RuntimeError("Creating reference submission was not successful")
    return parsed_response["payload"]["id"]


def evaluate_reference_solution(headers, exerciseId, solutionId, hwgroup):
    data = {"hwGroup": hwgroup}
    response = requests.post(EVALUATE_REFERENCE_ENDPOINT.format(exerciseId=exerciseId, id=solutionId),
                             headers=headers, data=data)
    parsed_response = json.loads(response.text)
    # print(parsed_response)
    if not parsed_response["success"]:
        raise RuntimeError("Evaluating reference submission failed")


def main():
    args = parser.parse_args()
    headers = {"Authorization": "Bearer " + args.token}

    file_id = upload_file(headers, args.file)
    solution_id = create_reference_solution(headers, file_id, args.exercise, args.note, args.runtime)
    evaluate_reference_solution(headers, args.exercise, solution_id, args.hwgroup)
    print("OK")


if __name__ == "__main__":
    main()
