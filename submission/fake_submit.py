#!/usr/bin/env python3

# Send a fake submit to the ReCodEx broker

import zmq
import os
import sys
import requests
import uuid
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--fs_address", help = "File server address", default = "localhost")
parser.add_argument("--fs_port", help = "File server port", default = 9999)
parser.add_argument("--broker_address", help = "Broker address", default = "localhost")
parser.add_argument("--broker_port", help = "Broker port", default = 9658)
parser.add_argument("--header", help = "Specify a header value for the submission (any number of values is permitted)",
                    action = "append", nargs = 2, metavar = ("KEY", "VALUE"), default = [])
parser.add_argument("submit_dir", help = "The directory to be submitted")
parser.add_argument("--id", help = "An identifier of the submission", default = "")

if __name__ == "__main__":
    args = parser.parse_args()

    # Collect submitted files
    submission_files = {}
    for root, dirs, files in os.walk(args.submit_dir):
        for name in files:
            f = os.path.relpath(os.path.join(root, name), args.submit_dir)

            submission_files[f] = (
                os.path.basename(f),
                open(os.path.join(args.submit_dir, f), "rb")
            )

    # Make up a job ID and hope for the best
    job_id = args.id or uuid.uuid4()

    # Send the submission to our fake file server
    fsrv_url = "http://{address}:{port}".format(address = args.fs_address, port = args.fs_port)

    try:
        reply = requests.post(
            "{url}/submissions/{id}".format(url = fsrv_url, id = job_id),
            files = submission_files
        )
    except:
        sys.exit("Error sending files to the file server")

    # Parse the JSON data in the reply
    reply_data = json.loads(reply.text)
    print(reply_data["result_path"])

    # Connect to the broker
    context = zmq.Context()
    broker = context.socket(zmq.REQ)

    try:
        broker.connect("tcp://{address}:{port}".format(address = args.broker_address, port = args.broker_port))
    except:
        sys.exit("Error connecting to the broker")

    # Send the request
    broker.send_multipart(
        [b"eval"] +
        [str(job_id).encode()] +
        ["{}={}".format(k, v).encode() for k, v in args.header] +
        [b""] +
        ["{url}{path}".format(url = fsrv_url, path = reply_data["archive_path"]).encode()] +
        ["{url}{path}".format(url = fsrv_url, path = reply_data["result_path"]).encode()]
    )

    result = broker.recv()
    print(result)
