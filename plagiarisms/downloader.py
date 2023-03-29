import os
import shutil
import csv
from ruamel import yaml
import subprocess
import logging

CONFIG_FILE = 'config.yaml'  # generated for the downloader tool


def get_csv_header(file):
    '''
    Return field names of given CSV file.
    '''
    with open(file, 'r', encoding="utf8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames)


def load_manifest_solutions(manifest_file, solution_id_col='solution_id'):
    '''
    Parse given manifest file and return a dictionary, where keys are solution IDs.
    '''
    solutions = {}
    if not os.path.exists(manifest_file):
        return solutions

    with open(manifest_file, 'r', encoding="utf8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            solutions[row[solution_id_col]] = True
    return solutions


class Downloader:
    '''
    Wraps operations of the downloader tool and related to download manipulation.
    That includes config creation, download verification, and merging new downloads with archive.
    '''

    def __init__(self, config, files, exercise):
        '''
        Initialize this component by injecting dependencies.
        '''
        self.config = config
        self.files = files
        self.exercise = exercise

    def _get_config_file(self):
        return self.files.get_working_dir() + '/' + CONFIG_FILE

    def _prepare_config(self):
        '''
        Creates a yaml config file for the downloader (mostly copying relevant parts of the given config).
        The solutions_created_at is timestamp used to filter solutions (only newer solutions are downloaded).
        The file is saved to save_as path.
        '''
        new_config = {key: self.config[key] for key in ['exercises', 'groups', 'manifest', 'solutions']}
        new_config['path'] = ['solution.id']
        new_config['manifest']['solution_id'] = 'solution.id'

        with open(self._get_config_file(), 'w') as fp:
            yaml.dump(new_config, fp)

    def _verify_download(self):
        '''
        Verify the target dir contains the manifest file and corresponding solutions.
        '''
        manifest_file = self.files.get_working_manifest_file()
        if not os.path.exists(manifest_file):
            raise Exception("Download failed -- manifest file {} does not exist".format(manifest_file))

        wd = self.files.get_working_dir()
        solutions = load_manifest_solutions(manifest_file)
        for solution in solutions:
            path = wd + '/' + solution
            if not os.path.exists(path) or not os.path.isdir(path):
                raise Exception("Solution {} does not have any downloaded files".format(solution))

    def run(self):
        '''
        Invoke the downloader tool. The config should have been prepared.
        '''
        self._prepare_config()

        args = [
            self.config['downloader']['python'],
            self.config['downloader']['exec'],
            '--config', self._get_config_file(),
            '--dest-dir', self.files.get_working_dir(),
            '--manifest', self.files.get_working_manifest_file(),
            '--manifest-per-file',
            self.exercise
        ]
        res = subprocess.run(args, capture_output=True)
        if res.returncode != 0:
            logging.getLogger().error(res.stderr.decode('utf8'))
            raise RuntimeError("The downloader tool failed.")

        self._verify_download()

    def has_new_solutions(self):
        '''
        Check whether a newly downloaded batch has some new solutions (compared to the last batch).
        '''
        last_solutions = load_manifest_solutions(self.files.get_last_manifest_file())
        new_solutions = load_manifest_solutions(self.files.get_working_manifest_file())
        for solution in new_solutions:
            if not last_solutions.get(solution, False):
                return True  # new solution was found
        return False

    def merge_new_solutions(self):
        '''
        Add all new solutions from working dir to the archive. Manifests are merged as well
        (new lines are appended to archive manifest).
        '''
        if not os.path.exists(self.files.get_archive_manifest_file()):
            return  # no archive manifest -> archive does not exist or is corrupted

        archive_header = get_csv_header(self.files.get_archive_manifest_file())
        archive_solutions = load_manifest_solutions(self.files.get_archive_manifest_file())
        with open(self.files.get_working_manifest_file(), 'r', encoding="utf8") as fin:
            reader = csv.DictReader(fin)

            # Let's make sure the manifests are compatible (archive columns must be equal or subset of new manifest columns)
            archive_header_idx = dict.fromkeys(archive_header)
            for col in reader.fieldnames:
                if col not in archive_header_idx:
                    raise RuntimeError(
                        "Cannot merge solutions, manifests do not have the same headers (column '{}' is missing).".format(col))

            # newly found records will be added to the archive
            with open(self.files.get_archive_manifest_file(), 'a', encoding="utf8") as fout:
                writer = csv.DictWriter(fout, fieldnames=archive_header)
                for row in reader:
                    solution_id = row['solution_id']
                    if not archive_solutions.get(solution_id, False):
                        # a solutions is appended to the manifest and its dir is copied
                        writer.writerow(row)
                        if not os.path.exists(self.files.get_archive_dir() + '/' + solution_id):
                            shutil.copytree(self.files.get_working_dir() + '/' + solution_id,
                                            self.files.get_archive_dir() + '/' + solution_id)
