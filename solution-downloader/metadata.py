import unicodedata
import csv
import glob
import os
import recodex_api
from translator import AttributeTranslator


def normalize_str(str):
    '''
    Helper that normalizes UTF-8 string by removing no-ASCII characters.
    '''
    return unicodedata.normalize('NFKD', str).encode('ascii', 'ignore').decode('utf-8')


class MetadataHandler:
    '''
    Wraps handling of all metadata based on the configuration.
    Primary function is to generate paths for given solutions and to save relevant metadata into manifest.

    The object remembers last set group, assignment, and solution (they can be updated by correspondnig set_* methods).
    When all three parameters are set, user can get a path or write corresponding metadata to a CSV file.
    '''

    def __init__(self, dest_dir, config, config_dir) -> None:
        '''
        The dest_dir is the directory where everything is downloaded, config a structure from parsed config.yaml.
        The config dir is the directory where config.yaml file was (used as a base dir for paths in the config)
        '''
        self.manifest_fp = None
        self.manifest_csv_writer = None
        self.manifest_per_file = None
        self.user_cache = {}  # caching ID => user (so that we load each user only once from ReCodEx)

        self.dest_dir = dest_dir
        self.manifest_config = config.get('manifest', {})
        self.path_config = config.get('path', [])
        if type(self.path_config) is not list or len(self.path_config) == 0:
            raise RuntimeError("Invalid path configuration.")

        # Initial defaults for metadata (augmented by set_ functions)
        self.metadata = {
            'group': None,
            'assignment': None,
            'solution': None,
            'author': None,  # entity of the user who submitted the solution
            'admin': None,  # entity of the first primary admin of the group
            'path': self.dest_dir,
        }

        self.translators = []
        for name, trans_config in config.get('translated_attributes', {}).items():
            self.translators.append(AttributeTranslator(name, trans_config, config_dir))

    def _fetch(self, parameter, safe=False):
        '''
        Retrieve a metadata attribute based on a string descriptor `parameter`.
        The descriptor uses '.' to separate individual keys in nested dictionaries.
        '''
        obj = self.metadata
        for token in parameter.split("."):
            if type(obj) is dict and token in obj:
                obj = obj[token]
            else:
                if safe:
                    return None
                else:
                    raise RuntimeError(
                        "Descriptor '{}' cannot be resolved in metadata structures (token '{}' failed).".format(parameter, token))
        return obj

    def _get_path(self):
        '''
        Computes path to target directory based on current configuration and last set solution, assignment, and group.
        '''

        def mapper(param):  # helper that transforms individual path values
            dir = self._fetch(param)
            if type(dir) == int:
                dir = str(dir)
            if type(dir) != str:
                raise RuntimeError("Metadata parameter {} does not translate into printable value.".format(param))
            return dir

        return "/".join(map(mapper, self.path_config))

    def _add_user_to_cache(self, user):
        '''
        Augments the user object with computed values (normalized name strings) and saves it into the cache.
        '''
        self.user_cache[user['id']] = user
        name = user.get('name', {})
        user['fullName'] = name.get('firstName') + " " + name.get('lastName')
        user['normFirstName'] = normalize_str(name.get('firstName')).lower()
        user['normLastName'] = normalize_str(name.get('lastName')).lower()
        user['normName'] = user['normLastName'] + " " + user['normFirstName']

    def _get_user(self, user_id):
        '''
        Retrieves user by ID. Uses/populates user cache in the process.
        '''
        if user_id not in self.user_cache:
            self._add_user_to_cache(recodex_api.get_user(user_id))

        return self.user_cache[user_id]

    def _use_metadata_translators(self):
        for translator in self.translators:  # erase all first
            self.metadata[translator.get_name()] = None

        for translator in self.translators:
            key = self._fetch(translator.get_key(), True)
            if key is not None:
                self.metadata[translator.get_name()] = translator.translate(key)

    def set_group(self, group):
        '''
        Update current metadata structure by setting current group (and related entities).
        '''
        for student in recodex_api.get_students(group['id']):
            self._add_user_to_cache(student)  # populate user cache (as an optimization)

        self.metadata['group'] = group
        admins = group.get('primaryAdminsIds', [])
        self.metadata['admin'] = self._get_user(admins[0]) if len(admins) > 0 else None
        self._use_metadata_translators()

    def set_assignment(self, assignment):
        '''
        Update current metadata structure by setting current assignment.
        '''
        self.metadata['assignment'] = assignment
        self._use_metadata_translators()

    def set_solution(self, solution):
        '''
        Update current metadata structure by setting current solution (and related entities).
        '''
        self.metadata['solution'] = solution
        self.metadata['author'] = self._get_user(solution['authorId'])
        self.metadata['path'] = None  # make sure path config does not reference itself
        self.metadata['path'] = self._get_path()
        self._use_metadata_translators()

    def open_mainfest(self, file, per_file=False):
        '''
        Open the manifest file and write in the header line.
        All subsequent calls to write_manifest() will write here.
        '''
        if type(self.manifest_config) is not dict or len(self.manifest_config) == 0:
            raise RuntimeError("Invalid manifest configuration.")

        self.manifest_fp = open(file, 'w', newline='', encoding='utf-8')
        self.manifest_csv_writer = csv.writer(self.manifest_fp)
        self.manifest_csv_writer.writerow(self.manifest_config.keys())
        self.manifest_per_file = per_file

    def close_manifest(self):
        '''
        Close manifest file (no more writes).
        '''
        if self.manifest_fp is not None:
            self.manifest_fp.close()
            self.manifest_fp = None
            self.manifest_csv_writer = None

    def get_path(self):
        '''
        Retrieve path for given solution (based on the configuration, and last set solution, group, and assignment).
        '''
        path = self.metadata['path']
        if self.dest_dir:
            path = self.dest_dir + "/" + path
        return path

    def _write_manifest_row(self):
        row = map(lambda p: self._fetch(p), self.manifest_config.values())
        self.manifest_csv_writer.writerow(row)

    def write_manifest(self):
        '''
        If the manifest is being saved, write solution metadata into CSV as one line
        (based on the configuration and last set solution, group, and assignment).
        If the manifest_per_file, one line per each downloaded file is written.
        '''
        if self.manifest_fp is not None:
            if self.manifest_per_file:
                pwd = os.getcwd()
                os.chdir(self.get_path())
                path = self.metadata['path']  # save solution path

                for file in glob.glob('**/*', recursive=True):
                    self.metadata['path'] = path + '/' + file
                    self.metadata['file'] = file
                    self._write_manifest_row()

                self.metadata['path'] = path  # restore the path
                self.metadata.pop('file', None)
                os.chdir(pwd)
            else:
                self._write_manifest_row()
