#!/usr/bin/env python3

import argparse
import csv
import time
from datetime import datetime


def get_active_users(file, duration):
    threshold = int(time.time()) - duration
    users = {}
    actions = {}
    with open(file, 'r', encoding='utf-8') as fp:
        reader = csv.reader(fp, delimiter=',')
        for row in reader:
            ts = int(row[1])
            if ts >= threshold:
                user = row[0]
                users[user] = ts
                actions[user] = actions.get(user, 0) + 1

    res = []
    for user in sorted(users.items(), key=lambda x: -x[1]):
        res.append([user[0], user[1], actions[user[0]]])
    return res


if __name__ == "__main__":
    # Process program arguments...
    parser = argparse.ArgumentParser()
    parser.add_argument("duration", type=int, help="Duration in seconds used as detection threshold")
    parser.add_argument("--log", type=str,
                        help="Path to user actions log (./user_actions.log by default).")
    args = parser.parse_args()

    users = get_active_users(args.log or './user_actions.log', args.duration)
    for user in users:
        print("{} {} {}".format(user[0], datetime.fromtimestamp(user[1]).strftime('%Y-%m-%d %H:%M:%S'), user[2]))
