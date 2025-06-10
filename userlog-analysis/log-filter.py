#!/usr/bin/env python3

import argparse
import glob
import os.path
import sys
import gzip
import csv
import re
from datetime import datetime
from dateutil import parser as dateparser


def get_files(prefix):
    files = []
    files += glob.glob(prefix + '*.gz')
    files = list(map(lambda s: s.replace('\\', '/'), files))
    files.sort()
    if os.path.isfile(prefix):
        files.append(prefix)
    return files


def _text_max_ts(r, max_ts):
    if r:
        if int(r[1]) > max_ts:
            exit(0)
        return r
    else:
        return None


def _anon_uuids(str):
    return re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '<anon-id>', str)


def make_filters(min_time, max_time, seconds, convert_time, anonymize):
    filters = []

    if min_time:
        min_dt = dateparser.parse(min_time)
        min_ts = int(min_dt.timestamp())
        filters.append(lambda r: r if r and int(r[1]) >= min_ts else None)
        if seconds:
            max_ts = min_ts + int(seconds)
            filters.append(lambda r: _text_max_ts(r, max_ts))

    if max_time:
        max_dt = dateparser.parse(max_time)
        max_ts = int(max_dt.timestamp())
        filters.append(lambda r: _text_max_ts(r, max_ts))

    if convert_time:
        filters.append(lambda r: [r[0], datetime.fromtimestamp(
            int(r[1])).strftime('%Y-%m-%d %H:%M:%S')] + r[2:] if r else None)

    if anonymize:
        filters.append(lambda r: ['<anon-user>', r[1], '<anon-ip>', r[3],
                                  _anon_uuids(r[4])] + r[5:] if r else None)

    return filters


def process_file(file, filters, writer):
    if file.endswith('.gz'):
        fp = gzip.open(file, 'rt', encoding='utf-8')
    else:
        fp = open(file, 'r', encoding='utf-8')

    reader = csv.reader(fp, delimiter=',')
    for row in reader:
        for filter in filters:
            row = filter(row)
            if not row:
                continue
        if row:
            writer.writerow(row)

    fp.close()


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    # Process program arguments...
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=str, help="Prefix path to user actions log ('./user_actions.log' is default)")
    parser.add_argument('--after', type=str, help="Show records after given time.")
    parser.add_argument('--before', type=str, help="Show records before given time.")
    parser.add_argument('--seconds', type=str, help="If 'after' is set, then time window of given seconds is listed.")
    parser.add_argument('--convert-time', action='store_true',
                        help="If set, unix ts will be converted to readable format.")
    parser.add_argument('--anonymize', action='store_true',
                        help="Replace IDs and IPs with anon str.")
    args = parser.parse_args()

    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    filters = make_filters(args.after, args.before, args.seconds or 0,
                           args.convert_time, args.anonymize)
    files = get_files(args.log or './user_actions.log')
    for file in files:
        process_file(file, filters, writer)
