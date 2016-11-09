#!/usr/bin/env python3
import requests
import sys
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("address", help = "File server address")
parser.add_argument("port", help = "File server port")
parser.add_argument("source_directory", help = "The directory to be stored")
parser.add_argument("--fs_user", help = "File server user", default = None)
parser.add_argument("--fs_pass", help = "File server password", default = None)

if __name__ == "__main__":
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
    try:
        auth_info = dict(auth=(args.fs_user, args.fs_pass)) if args.fs_user else {}
        reply = requests.post(tasks_url, files = data, **auth_info)
    except:
        sys.exit("Error sending files to the file server")

    print(reply.text)
