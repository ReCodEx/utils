#!/usr/bin/env python3
import requests
import sys
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("address", help = "File server address")
parser.add_argument("port", help = "File server port")
parser.add_argument("source_directory", help = "The directory to be stored")

args = parser.parse_args()

data = {}

for root, dirs, files in os.walk(args.source_directory):
    for name in files:
        path = os.path.join(root, name)

        data[path] = (
            os.path.basename(path),
            open(path, "rb")
        )

tasks_url = "http://{address}:{port}/tasks".format(
    address = args.address,
    port = args.port
)
reply = requests.post(tasks_url, files = data)
print(reply.text)
