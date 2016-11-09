#!/usr/bin/python3

import sys
import argparse
import re
import os

import print_yml


class TestLimits:
    def __init__(self):
        self.time_limit = ''
        self.mem_limit = ''


class JobTest:
    def __init__(self, number):
        self.number = number
        self.points = ''
        self.in_type = ''
        self.out_type = ''
        self.limits = dict()
        self.out_filter = ''
        self.judge = ''
        self.in_file = None
        self.out_file = None

    def __str__(self):
        output = "TEST {} -- points: {}, in_type: {}, out_type: {}, filter: {}, judge: {}"\
            .format(self.number, self.points, self.in_type, self.out_type, self.out_filter, self.judge)

        if self.in_file:
            output += ", in_file: {}".format(self.in_file)
        if self.out_file:
            output += ", out_file: {}".format(self.out_file)

        for limit_group in self.limits:
            output += "\n\t{}\t- time_limit: {}, mem_limit: {}"\
                .format(limit_group, self.limits[limit_group].time_limit, self.limits[limit_group].mem_limit)
        return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert old Codex config to some new ReCodEx one')
    parser.add_argument('-i', '--input', type=str, nargs=1, required=True, help='input file with old config')
    parser.add_argument('-o', '--output', nargs=1, required=False, help='output file (default stdout)')
    parser.add_argument('-d', '--data', type=str, nargs=1, required=True, help='data folder with all test files')
    args = parser.parse_args()

    if args.output:
        out_stream = open(args.output[0], mode='w', encoding='utf-8')
    else:
        out_stream = sys.stdout

    with open(args.input[0], mode='r', encoding='utf-8') as in_file:
        lines = list()
        for line in in_file:
            line_arr = line.rstrip().split(sep='=')
            line_arr[1] = line_arr[1][1:-1]  # Remove leading and trailing ' symbol in value field (not present in key)
            lines.append(line_arr)

    config = dict(lines)

    tests = [JobTest(num) for num in config['TESTS'].split(sep=' ')]
    for test in tests:
        # Set defaults
        test.points = config['POINTS_PER_TEST']
        test.in_type = config['IN_TYPE']
        test.out_type = config['OUT_TYPE']
        test.out_filter = config['OUTPUT_FILTER'].split(sep=' ')[0][4:]  # Remove bin/ prefix
        test.judge = config['OUTPUT_CHECK'].split(sep=' ')[0][4:]  # Remove bin/ prefix
        test.limits['default'] = TestLimits()
        test.limits['default'].time_limit = config['TIME_LIMIT']
        test.limits['default'].mem_limit = config['MEM_LIMIT']

        # Set file names if provided
        if test.in_type == 'file':
            test.in_file = config['IN_FILE']
        if test.out_type == 'file':
            test.out_file = config['OUT_FILE']

        # Set test specific values
        points_key = 'TEST_{}_POINTS_PER_TEST'.format(test.number)
        if points_key in config:
            test.points = config[points_key]

        time_limit_key = 'TEST_{}_TIME_LIMIT'.format(test.number)
        if time_limit_key in config:
            test.limits['default'].time_limit = config[time_limit_key]

        mem_limit_key = 'TEST_{}_MEM_LIMIT'.format(test.number)
        if mem_limit_key in config:
            test.limits['default'].mem_limit = config[mem_limit_key]

    # Extension based configs
    for config_key in config:
        # Handle global limits for extension
        m = re.search('EXT_([^_]*)_TIME_LIMIT', config_key)
        if m:
            extension = m.group(1)
            for test in tests:
                if extension not in test.limits:
                    test.limits[extension] = TestLimits()
                    test.limits[extension].time_limit = test.limits['default'].time_limit
                    test.limits[extension].mem_limit = test.limits['default'].mem_limit
                test.limits[extension].time_limit = config[config_key]

        m = re.search('EXT_([^_]*)_MEM_LIMIT', config_key)
        if m:
            extension = m.group(1)
            for test in tests:
                if extension not in test.limits:
                    test.limits[extension] = TestLimits()
                    test.limits[extension].time_limit = test.limits['default'].time_limit
                    test.limits[extension].mem_limit = test.limits['default'].mem_limit
                test.limits[extension].mem_limit = config[config_key]

        # Handle test specific limits for extension
        m = re.search('EXT_([^_]*)_TEST_([^_]*)_TIME_LIMIT', config_key)
        if m:
            extension = m.group(1)
            test_num = m.group(2)
            for test in tests:
                if test.number != test_num:
                    continue
                if extension not in test.limits:
                    test.limits[extension] = TestLimits()
                    test.limits[extension].time_limit = test.limits['default'].time_limit
                    test.limits[extension].mem_limit = test.limits['default'].mem_limit
                test.limits[extension].time_limit = config[config_key]

        m = re.search('EXT_([^_]*)_TEST_([^_]*)_MEM_LIMIT', config_key)
        if m:
            extension = m.group(1)
            test_num = m.group(2)
            for test in tests:
                if test.number != test_num:
                    continue
                if extension not in test.limits:
                    test.limits[extension] = TestLimits()
                    test.limits[extension].time_limit = test.limits['default'].time_limit
                    test.limits[extension].mem_limit = test.limits['default'].mem_limit
                test.limits[extension].mem_limit = config[config_key]

    # Useful printing for testing :-)
    # for i in tests:
    #    print(i, file=out_stream)

    # Print yaml
    print_yml.print_job(tests, args.data[0], out_stream)
