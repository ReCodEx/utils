import sys
import subprocess
import os
import zipfile
import shutil
from ruamel import yaml

group_cache = None


def _recodex_call(args):
    res = subprocess.run(['recodex'] + args, capture_output=True)
    if res.returncode == 0:
        return res.stdout
    else:
        sys.stderr.write("Error calling recodex CLI:\n")
        sys.stderr.buffer.write(res.stderr)
        return None


def _get_all_groups():
    '''
    Load all groups and return them in a dictionary indexed by group IDs.
    '''

    payload = _recodex_call(['groups', 'all'])
    if payload is None:
        raise Exception("Error reading groups list.")
    groups = yaml.safe_load(payload)

    res = {}
    for group in groups:
        res[group.get('id')] = group

    return res


def get_relevant_groups(group_id, recursive):
    global group_cache
    if group_cache is None:
        group_cache = _get_all_groups()

    res = []
    group = group_cache.get(group_id, None)
    if group is None or group.get('archived'):
        return res

    if len(group.get('privateData', {}).get('assignments', [])) != 0:
        res.append(group)

    if recursive:
        for child in group.get('childGroups', []):
            res = res + get_relevant_groups(child, recursive)

    return res


def get_user(user_id):
    '''
    Load data of one user of particular ID.
    '''
    payload = _recodex_call(['users', 'get', user_id, '--yaml'])
    if payload is None:
        raise Exception("Error loading user {}.".format(user_id))

    return yaml.safe_load(payload)


def get_students(group_id):
    '''
    Return students of a particular group.
    '''
    payload = _recodex_call(['groups', 'students', group_id, '--yaml'])
    if payload is None:
        raise Exception("Error reading students of group {}.".format(group_id))

    return yaml.safe_load(payload)


def get_assignments(group_id, exercise_id):
    '''
    Load all assignments of given group and return id of the first one that matches given exercise.
    '''
    payload = _recodex_call(['groups', 'assignments', group_id, '--yaml'])
    if payload is None:
        raise Exception("Error reading assignments of group.")

    res = []
    assignments = yaml.safe_load(payload)
    for assignment in assignments:
        if assignment.get('exerciseId', None) == exercise_id:
            res.append(assignment)

    return res


def _filter_solution(solution, config):
    accepted = config.get('accepted', None)
    if accepted is not None and solution.get('accepted', False) != accepted:
        return False

    best = config.get('best', None)
    if best is not None and solution.get('isBestSolution', False) != best:
        return False

    reviewed = config.get('reviewed', None)
    if reviewed is not None and solution.get('reviewed', False) != reviewed:
        return False

    correctness = config.get('correctness', None)
    score = solution.get('lastSubmission', {}).get('evaluation', {}).get('score', 0.0) * 100.0
    if correctness is not None and correctness > score:
        return False

    return True


def get_solutions(assignment_id, config):
    '''
    Load all solutions of given assignment and filter only accepted ones.
    Returns a dictionary user ID => solution ID.
    '''
    payload = _recodex_call(['assignments', 'get-solutions', assignment_id, '--yaml'])
    if payload is None:
        raise Exception("Error reading solutions of an assignment.")

    solutions = yaml.safe_load(payload)
    result = []
    for solution in solutions:
        if _filter_solution(solution, config):
            result.append(solution)

    return result


def download_solutions(solution_id, dir, dest_dir):
    '''
    Download a solution and extract it into target dir.
    The downloaded zip is deleted after extraction.
    '''
    zip_file = "{}/{}.zip".format(dest_dir, solution_id)
    _recodex_call(['solutions', 'download', solution_id, zip_file])
    if not os.path.exists(zip_file):
        raise RuntimeError("Download of {} failed!".format(zip_file))

    # unzip
    if os.path.exists(dir):
        shutil.rmtree(dir)
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(dir)

    os.unlink(zip_file)
