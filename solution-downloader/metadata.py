import unicodedata
import csv
import recodex_api


def normalize_str(str):
    return unicodedata.normalize('NFKD', str).encode('ascii', 'ignore').decode('utf-8')


class MetadataHandler:
    '''
    Wraps handling of all metadata based on the configuration.
    Primary function is to generate paths for given solutions and to save relevant metadata into manifest.
    '''

    def __init__(self, dest_dir, config) -> None:

        self.dest_dir = dest_dir
        self.manifest_config = config.get('manifest', {})
        self.path_config = config.get('path', [])
        if type(self.path_config) is not list or len(self.path_config) == 0:
            raise RuntimeError("Invalid path configuration.")

        self.metadata = {
            'group': None,
            'assignment': None,
            'solution': None,
            'author': None,  # entity of the user who submitted the solution
            'admin': None,  # entity of the first primary admin of the group
            'path': self.dest_dir,
        }

        self.manifest_fp = None
        self.manifest_csv_writer = None
        self.user_cache = {}

    def _fetch(self, parameter):
        obj = self.metadata
        for token in parameter.split("."):
            if type(obj) is dict and token in obj:
                obj = obj[token]
            else:
                raise RuntimeError("Parameter {} cannot be resolved in metadata structures.".format(parameter))
        return obj

    def _get_path(self):
        def mapper(param):
            dir = self._fetch(param)
            if type(dir) == int:
                dir = str(dir)
            if type(dir) != str:
                raise RuntimeError("Metadata parameter {} does not translate into printable value.".format(param))
            return dir

        path = "/".join(map(mapper, self.path_config))
        if self.dest_dir:
            path = self.dest_dir + "/" + path
        return path

    def _add_user_to_cache(self, user):
        self.user_cache[user['id']] = user
        user['fullName'] = user.get('name', {}).get('firstName') + " " + user.get('name', {}).get('lastName')
        user['normFirstName'] = normalize_str(user.get('name', {}).get('firstName')).lower()
        user['normLastName'] = normalize_str(user.get('name', {}).get('lastName')).lower()
        user['normName'] = user['normLastName'] + " " + user['normFirstName']

    def _get_user(self, user_id):
        if user_id not in self.user_cache:
            self._add_user_to_cache(recodex_api.get_user(user_id))

        return self.user_cache[user_id]

    def set_group(self, group):
        '''
        Update current metadata structure by setting current group (and related entities).
        '''
        for student in recodex_api.get_students(group['id']):
            self._add_user_to_cache(student)  # populate user cache (as an optimization)

        self.metadata['group'] = group
        admins = group.get('primaryAdminsIds', [])
        self.metadata['admin'] = self._get_user(admins[0]) if len(admins) > 0 else None

    def set_assignment(self, assignment):
        '''
        Update current metadata structure by setting current assignment.
        '''
        self.metadata['assignment'] = assignment

    def set_solution(self, solution):
        '''
        Update current metadata structure by setting current solution (and related entities).
        '''
        self.metadata['solution'] = solution
        self.metadata['author'] = self._get_user(solution['authorId'])
        self.metadata['path'] = None  # make sure path config does not reference itself
        self.metadata['path'] = self._get_path()

    def open_mainfest(self, file):
        '''
        Open the manifest file and write in the header line.
        All subsequent calls to write_manifest() will write here.
        '''
        if type(self.manifest_config) is not dict or len(self.manifest_config) == 0:
            raise RuntimeError("Invalid manifest configuration.")

        self.manifest_fp = open(file, 'w', newline='', encoding='utf-8')
        self.manifest_csv_writer = csv.writer(self.manifest_fp)
        self.manifest_csv_writer.writerow(self.manifest_config.keys())

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
        Retrieve path for given solution (based on the configuration, optionally using current group and assignment).
        '''
        return self.metadata['path']

    def write_manifest(self):
        '''
        If the manifest is being saved, write solution metadata into CSV
        (based on the configuration, optionally using current group and assignment).
        '''
        if self.manifest_fp is not None:
            row = map(lambda p: self._fetch(p), self.manifest_config.values())
            self.manifest_csv_writer.writerow(row)
