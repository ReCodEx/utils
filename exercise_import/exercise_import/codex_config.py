import re

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
        self.judge_args = []
        self.in_file = None
        self.out_file = None
        self.executable = ''
        self.cmd_args = []

    @property
    def name(self):
        return "Test {}".format(self.number)

    @property
    def has_custom_judge(self):
        return self.judge.startswith("$PDIR/")

    @property
    def custom_judge_binary(self):
        return self._replace_vars(self.judge)

    @property
    def custom_judge_args(self):
        return list(map(self._replace_vars, self.judge_args))

    def _replace_vars(self, string):
        string = string.replace("$PDIR/", "")
        string = string.replace("$TDIR/", "" if self.out_type != "dir" else str(self.number) + "/")
        string = string.replace("$TEST", self.number)
        return string

    def __str__(self):
        output = "TEST {} -- points: {}, executable: {}, args: {}, in_type: {}, out_type: {}, filter: {}, judge: {}"\
            .format(self.number, self.points, self.executable, self.cmd_args, self.in_type, self.out_type, self.out_filter, self.judge)

        if self.in_file:
            output += ", in_file: {}".format(self.in_file)
        if self.out_file:
            output += ", out_file: {}".format(self.out_file)

        for limit_group in self.limits:
            output += "\n\t{}\t- time_limit: {}, mem_limit: {}"\
                .format(limit_group, self.limits[limit_group].time_limit, self.limits[limit_group].mem_limit)
        return output

def load_codex_test_config(path):
    lines = (line.strip().replace("'", "").split('=', 1) for line in path.open("r") if line.strip() and not line.startswith('#'))
    config = dict(lines)

    tests = [JobTest(num) for num in config['TESTS'].split(sep=' ')]
    for test in tests:
        # Set defaults
        test.points = config['POINTS_PER_TEST']
        test.in_type = config['IN_TYPE'] if 'IN_TYPE' in config else "stdio"
        test.out_type = config['OUT_TYPE'] if 'OUT_TYPE' in config else "stdio"
        test.out_filter = config['OUTPUT_FILTER'].split(sep=' ')[0] if 'OUTPUT_FILTER' in config else None

        if 'OUTPUT_CHECK' in config:
            parts = config['OUTPUT_CHECK'].split(sep=' ')
            test.judge = parts[0]
            test.judge_args = parts[1:] if len(parts) > 1 else []
        else:
            test.judge = "bin/codex_judge"

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

# Extension based global configs
    for config_key in config:
        # Handle global execution command
        m = re.search('EXT_([^_]*)_TEST_EXEC_CMD', config_key)
        if m:
            extension = m.group(1)
            for test in tests:
                exec_split = config[config_key].split(' ')
                test.executable = exec_split[0]
                if len(exec_split) > 1:
                    test.cmd_args = exec_split[slice(1, len(exec_split))]

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

# Extension based test local configs
    for config_key in config:
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

        # Handle test specific execution command
        m = re.search('EXT_([^_]*)_TEST_([^_]*)_TEST_EXEC_CMD', config_key)
        if m:
            extension = m.group(1)
            test_num = m.group(2)
            for test in tests:
                if test.number != test_num:
                    continue
                exec_split = config[config_key].split(' ')
                test.executable = exec_split[0]
                if len(exec_split) > 1:
                    test.cmd_args = exec_split[slice(1, len(exec_split))]

        # Handle test specific in and out types
        m = re.search('EXT_([^_]*)_TEST_([^_]*)_OUT_TYPE', config_key)
        if m:
            extension = m.group(1)
            test_num = m.group(2)
            for test in tests:
                if test.number != test_num:
                    continue
                test.out_type = config[config_key]

        m = re.search('EXT_([^_]*)_TEST_([^_]*)_IN_TYPE', config_key)
        if m:
            extension = m.group(1)
            test_num = m.group(2)
            for test in tests:
                if test.number != test_num:
                    continue
                test.in_type = config[config_key]

        # Handle test specific judge
        m = re.search('TEST_([^_]*)_OUTPUT_CHECK', config_key)
        if m:
            test_num = m.group(1)
            for test in tests:
                if test.number != test_num:
                    continue
                parts = config[config_key].split(' ')
                test.judge = parts[0]
                test.judge_args = parts[1:] if len(parts) > 1 else []

        m = re.search('EXT_([^_]*)_TEST_([^_]*)_OUTPUT_CHECK', config_key)
        if m:
            extension = m.group(1)
            test_num = m.group(2)
            for test in tests:
                if test.number != test_num:
                    continue
                test.judge = config[config_key].split(' ')[0]

    return tests

