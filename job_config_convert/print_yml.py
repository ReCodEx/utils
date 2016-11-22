#!/usr/bin/python3

import sys
import hashlib
import os

'''
Prints ReCodEx backend evaluate chain for one testing case.
You need to add proper headers and first compilation task.
'''


def sha1_of_file(file):
    with open(file, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def parse_config_variables(job_test):
    job_test.executable = job_test.executable.replace("/usr/local/mono/bin/mono", "/usr/bin/mono")
    job_test.executable = job_test.executable.replace("$PROBLEM", "***binary***")
    for i in range(0, len(job_test.cmd_args)):
        job_test.cmd_args[i] = job_test.cmd_args[i].replace("$PROBLEM", "***binary***")

    job_test.out_filter = job_test.out_filter.replace("bin/codex_filter", "${JUDGES_DIR}/recodex-judge-filter")
    job_test.judge = job_test.judge.replace("bin/codex_judge", "${JUDGES_DIR}/recodex-judge-normal")
    job_test.judge = job_test.judge.replace("diff", "/usr/bin/diff")


def print_job(tests, data_folder, output, ext="cs"):
    print_header(output)
    output.write('tasks:\n')
    print_compilation(output)
    for i in tests:
        print_one_test(i, ext, data_folder, output)


def print_compilation(output):
    print_task("compilation", "", "", 1, True, None, "***compilation***", ["***arg1***", "***arg2***"], output)
    print_sandbox(None, "", output, False, False)


def print_header(output):
    output.write('submission:\n')
    output.write('    job-id: ***identification***\n')
    output.write('    language: ***language***\n')
    output.write('    file-collector: http://localhost:9999/exercises\n')
    output.write('    log: true\n')
    output.write('    hw-groups:\n')
    output.write('        - group1\n')


def print_task(identity, task_type, test_id, priority, fatal, dependencies, binary, args, output):
    output.write('    - task-id: "{}"\n'.format(identity))
    if task_type != "":
        output.write('      type: "{}"\n'.format(task_type))
    if test_id != "":
        output.write('      test-id: "{}"\n'.format(test_id))
    output.write('      priority: {}\n'.format(priority))
    if fatal:
        output.write('      fatal-failure: true\n')
    else:
        output.write('      fatal-failure: false\n')

    if dependencies:
        output.write('      dependencies:\n')
        for dep in dependencies:
            output.write('          - {}\n'.format(dep))

    if not binary:
        binary = '***binary***'
    output.write('      cmd:\n')
    output.write('          bin: "{}"\n'.format(binary))

    if args:
        output.write('          args:\n')
        for arg in args:
            output.write('              - "{}"\n'.format(arg))


def print_sandbox(test, ext, output=sys.stdout, judge=False, with_limits=True):
    output.write('      sandbox:\n')
    output.write('          name: "isolate"\n')
    if test is not None and test.in_type == "stdio":
        output.write('          stdin: ${{EVAL_DIR}}/{}\n'.format(test.in_file))
    if test is not None and test.out_type == "stdio":
        output.write('          stdout: ${{EVAL_DIR}}/{}\n'.format(test.out_file))
    output.write('          limits:\n')
    output.write('              - hw-group-id: group1\n')

    if with_limits:
        if judge:
            # Set reasonable defaults for judges
            time = '2.0'
            memory = '16384'
        elif ext in test.limits:
            # There are extension specific values
            time = test.limits[ext].time_limit
            memory = test.limits[ext].mem_limit
        else:
            # Use test 'default' values
            time = test.limits['default'].time_limit
            memory = test.limits['default'].mem_limit

    if with_limits:
        output.write('                time: {}\n'. format(time))
        output.write('                memory: {}\n'.format(memory))
    output.write('                chdir: ${EVAL_DIR}\n')
    output.write('                environ-variable:\n')
    output.write('                    PATH: "/usr/bin"\n')
    output.write('                bound-directories:\n')
    output.write('                    - src: ${SOURCE_DIR}\n')
    output.write('                      dst: ${EVAL_DIR}\n')
    output.write('                      mode: RW\n')


def print_one_test(test, ext, data_folder, output=sys.stdout):
    priority = 2

    if not test.in_file:
        test.in_file = "{}.stdin".format(test.number)
    if not test.out_file:
        test.out_file = "{}.stdout".format(test.number)

    # parse config variables which can be hidden in test
    parse_config_variables(test)

    # Fetch input
    if test.in_type == 'dir':
        # compute sha1 on input file and write it to configuration
        input_file = "{}.zip".format(test.number)
        input_sha = sha1_of_file(os.path.join(data_folder, input_file))

        # Fetch .zip file, extract it and remove downloaded .zip file
        args = [input_sha, "${{SOURCE_DIR}}/{}.zip".format(test.number)]
        fetch_input = "fetch_input_{}".format(test.number)
        print_task(fetch_input, "", test.number, priority, False, ["compilation"], "fetch", args, output)
        priority += 1

        args = ["${{SOURCE_DIR}}/{}.zip".format(test.number), "${SOURCE_DIR}"]
        extract_input = "extract_input_{}".format(test.number)
        print_task(extract_input, "", test.number, priority, False, [fetch_input], "extract", args, output)
        priority += 1

        args = ["${{SOURCE_DIR}}/{}.zip".format(test.number)]
        remove_archive = "remove_archive_{}".format(test.number)
        print_task(remove_archive, "", test.number, priority, False, [extract_input], "rm", args, output)
        priority += 1

        last_task = remove_archive
    else:
        # compute sha1 on input file and write it to configuration
        input_file = "{}.in".format(test.number)
        input_sha = sha1_of_file(os.path.join(data_folder, input_file))

        # Just fetch regular input file
        args = [input_sha, "${{SOURCE_DIR}}/{}".format(test.in_file)]
        fetch_input = "fetch_input_{}".format(test.number)
        print_task(fetch_input, "", test.number, priority, False, ["compilation"], "fetch", args, output)
        priority += 1

        last_task = fetch_input

    # Evaluate test
    eval_task = "eval_task_{}".format(test.number)
    print_task(eval_task, "execution", test.number, priority, False, [last_task], test.executable, test.cmd_args, output)
    print_sandbox(test, ext, output)
    priority += 1

    # Fetch sample output
    output_file = "{}.out".format(test.number)
    output_sha = sha1_of_file(os.path.join(data_folder, output_file))
    args = [output_sha, "${{SOURCE_DIR}}/{}.out".format(test.number)]
    fetch_output = "fetch_output_{}".format(test.number)
    print_task(fetch_output, "", test.number, priority, False, [eval_task], "fetch", args, output)
    priority += 1

    if test.out_filter:
        # Filter outputs (clean comments)
        args = [test.out_file, "{}_filtered".format(test.out_file)]
        judge_filter = "judge_filter_{}".format(test.number)
        print_task(judge_filter, "", test.number, priority, False, [fetch_output], test.out_filter, args, output)
        print_sandbox(test, ext, output, judge=True)
        priority += 1

    # Prepare for judging
    judge_input_file = "{}".format(test.out_file)
    if test.out_filter:
        judge_input_file = "{}_filtered".format(test.out_file)
    judge_dependencies = [fetch_output]
    if test.out_filter:
        judge_dependencies = [judge_filter]

    # Judging results
    args = ["{}.out".format(test.number), judge_input_file]
    judge_results = "judge_test_{}".format(test.number)
    print_task(judge_results, "evaluation", test.number, priority, False, judge_dependencies, test.judge, args, output)
    print_sandbox(test, ext, output, judge=True)
    priority += 1

    # Remove junk
    args = ["${{SOURCE_DIR}}/{}.out".format(test.number), "${{SOURCE_DIR}}/{}".format(test.in_file),
            "${{SOURCE_DIR}}/{}".format(test.out_file)]
    if test.out_filter:
        args.append("${{SOURCE_DIR}}/{}_filtered".format(test.out_file))
    remove_junk = "remove_junk_{}".format(test.number)
    print_task(remove_junk, "", test.number, priority, False, [judge_results], "rm", args, output)
