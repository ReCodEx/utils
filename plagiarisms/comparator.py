import logging
import subprocess

OUTPUT_FILE = 'output.csv'


class Comparator:
    '''
    Wraper for executing the comparator tool.
    '''

    def __init__(self, config, exercise):
        self.name = config['name']
        self.exec = config['exec']
        self.output_csv = config['output'].get('csv', {})
        self.output_columns = config['output']['columns']

        # prepare actual arguments
        self.args = config.get('args', []) + config.get('exercise_args', {}).get(exercise, [])

    def get_name(self):
        return self.name

    def get_args(self):
        return self.args

    def run(self, **kwargs):
        '''
        Execute the comparator.
        '''
        res = subprocess.run([self.exec] + self.args, capture_output=True, **kwargs)
        if res.returncode != 0:
            logging.getLogger().error("The comparator failed.\n" + res.stderr.decode('utf8'))
            return False
        return True
