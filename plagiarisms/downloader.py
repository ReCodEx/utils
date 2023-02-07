import os
import shutil
import csv
from ruamel import yaml
import subprocess
import logging

MANIFEST_FILE = 'manifest.csv'


def prepare_config(config, solutions_created_at, save_as):
    '''
    Creates a yaml config file for the downloader (mostly copying relevant parts of the given config).
    The solutions_created_at is timestamp used to filter solutions (only newer solutions are downloaded).
    The file is saved to save_as path.
    '''
    new_config = {key: config[key] for key in ['exercises', 'groups', 'manifest', 'solutions']}
    new_config['path'] = ['solution.id']
    new_config['solutions']['createdAt'] = solutions_created_at
    new_config['manifest']['solution_id'] = 'solution.id'

    with open(save_as, 'w') as fp:
        yaml.dump(new_config, fp)


def run_downloader(config, downloader_config_file, dest_dir, exercise):
    '''
    Invoke the downloader tool. The config should have been prepared.
    '''
    args = [
        config['downloader']['python'],
        config['downloader']['exec'],
        '--config', downloader_config_file,
        '--dest-dir', dest_dir,
        '--manifest', dest_dir + '/' + MANIFEST_FILE,
        '--manifest-per-file',
        exercise
    ]
    res = subprocess.run(args, capture_output=True)
    if res.returncode != 0:
        logging.getLogger().error("The downloader tool failed.\n" + res.stderr.decode('utf8'))
        return False


def verify_download(dest_dir):
    '''
    Verify the target dir contains the manifest file and corresponding solutions.
    '''
    # TODO
    pass


def _load_manifest_solutions(manifest_file):
    solutions = {}
    if not os.path.exists(manifest_file):
        return solutions

    with open(manifest_file, 'r', encoding="utf8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            solutions[row['solution_id']] = True
    return solutions


def _get_csv_header(file):
    with open(file, 'r', encoding="utf8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames)


def has_new_solutions(new_dir, last_dir):
    '''
    Check whether a newly downloaded batch has some new solutions (compared to the last batch).
    '''
    last_solutions = _load_manifest_solutions(last_dir + '/' + MANIFEST_FILE)
    new_solutions = _load_manifest_solutions(new_dir + '/' + MANIFEST_FILE)
    for solution in new_solutions:
        if not last_solutions.get(solution, False):
            return True  # new solution was found
    return False


def merge_new_solutions(new_dir, archive_dir):
    '''
    Add all new solutions from new_dir to the archive_dir. Manifests are merged as well
    (new lines are appended to archive manifest).
    '''
    archive_header = _get_csv_header(archive_dir + '/' + MANIFEST_FILE)
    archive_solutions = _load_manifest_solutions(archive_dir + '/' + MANIFEST_FILE)
    with open(new_dir + '/' + MANIFEST_FILE, 'r', encoding="utf8") as fin:
        reader = csv.DictReader(fin)

        # Let's make sure the manifests are compatible (archive columns must be equal or subset of new manifest columns)
        archive_header_idx = dict.fromkeys(archive_header)
        for col in reader.fieldnames:
            if not archive_header_idx.get(col, False):
                raise Exception(
                    "Cannot merge solutions, manifests do not have the same headers (column '{}' is missing).".format(col))

        with open(archive_dir + '/' + MANIFEST_FILE, 'a', encoding="utf8") as fout:
            writer = csv.DictWriter(fout, fieldnames=archive_header)
            for row in reader:
                solution_id = row['solution_id']
                if not archive_solutions.get(solution_id, False):
                    # Newly found solutions are appended to manifest and their dirs are copied
                    writer.writerow(row)
                    if not os.path.exists(archive_dir + '/' + solution_id):
                        shutil.copytree(new_dir + '/' + solution_id, archive_dir + '/' + solution_id)
