import os
import shutil
from datetime import datetime

MANIFEST_FILE = 'manifest.csv'
OUTPUT_FILE = 'output.csv'


def mkdir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
        if not os.path.exists(dir):
            raise RuntimeError("Unable to create directory {}".format(dir))


class FilesManager:
    '''
    Handles path assembling and basic fs operations required for managing solutions. There are 3 important dirs:
      - working_dir where current batch is downloaded
      - last_dir where last downloaded batch was stored (so we can compare it with current batch)
      - archive_dir where all solutions are accumulated continuously
    '''

    def __init__(self, config, exercise):
        '''
        Initialize the manager using directory configs and selected exercise identifier.
        The exercise identifier is used as part of paths, so the detector can handle multiple exercises.
        '''
        self.working_dir = config['working']
        self.last_dir = config['last_batch'] + '/' + exercise
        self.archive_dir = config['archive'] + '/' + exercise
        self.logs_dir = config['logs']
        self.exercise = exercise
        mkdir(self.last_dir)
        mkdir(self.archive_dir)

    def working_dir_exists(self):
        return os.path.exists(self.working_dir)

    def prepare_working_dir(self):
        mkdir(self.working_dir)

    def get_working_dir(self):
        return self.working_dir

    def get_working_manifest_file(self):
        return self.working_dir + '/' + MANIFEST_FILE

    def clear_working_dir(self):
        if self.working_dir_exists():
            shutil.rmtree(self.working_dir)

    def get_comparator_output_file(self):
        return self.working_dir + '/' + OUTPUT_FILE

    def get_last_dir(self):
        return self.last_dir

    def get_last_manifest_file(self):
        return self.last_dir + '/' + MANIFEST_FILE

    def get_archive_dir(self):
        return self.archive_dir

    def get_archive_manifest_file(self):
        return self.archive_dir + '/' + MANIFEST_FILE

    def get_log_file(self):
        '''
        Return new log file name composed from current time and selected exercise.
        The logs directory is created if necessary.
        '''
        mkdir(self.logs_dir)
        log_file = self.logs_dir + '/' + datetime.now().strftime("%Y-%m-%d-%H%M%S--") + self.exercise + '.log'
        if os.path.exists(log_file):
            raise RuntimeError("Log file {} already exists.".format(log_file))
        return log_file

    def update_solution_dirs(self):
        '''
        Lay foundation of archive if it does not exist and replace last dir with working dir.
        '''
        if not os.path.exists(self.get_archive_manifest_file()):
            shutil.rmtree(self.archive_dir)
            shutil.copytree(self.working_dir, self.archive_dir)

        shutil.rmtree(self.last_dir)
        shutil.move(self.working_dir, self.last_dir)
