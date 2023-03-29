import os
import logging
import subprocess


class Comparator:
    '''
    Wraper for executing the comparator tool.
    '''

    def __init__(self, config, files, exercise):
        '''
        Initialize the component -- load config and inject dependencies.
        '''
        self.files = files

        self.name = config['name']
        self.exec = config['exec']
        self.output_csv = config['output'].get('csv', {})
        self.output_columns = config['output']['columns']

        # prepare actual arguments
        self.args = config.get('args', {})
        exercise_args = config.get('exercise_args', {}).get(exercise, {})
        for key in exercise_args:
            self.args[key] = exercise_args[key]  # override base args

    def get_name(self):
        return self.name

    def get_args(self):
        '''
        Assemble the arguments and return them as a list of strings.
        '''
        references = {
            'manifest': self.files.get_working_manifest_file(),
            'output': self.get_output_file(),
        }
        if os.path.exists(self.files.get_archive_manifest_file()):
            references['archive'] = self.files.get_archive_manifest_file()

        args = self.args.get('other', []).copy()
        for name in references:
            args += [arg.format(references[name]) for arg in self.args.get(name, [])]

        return args

    def get_output_file(self):
        return self.files.get_comparator_output_file()

    def get_output_csv_params(self):
        return self.output_csv

    def get_output_columns(self):
        return self.output_columns

    def run(self, **kwargs):
        '''
        Execute the comparator.
        '''
        res = subprocess.run([self.exec] + self.get_args(), capture_output=True, **kwargs)
        if res.returncode != 0:
            logging.getLogger().error("The comparator failed.\n" + res.stderr.decode('utf8'))
            return False
        return True
