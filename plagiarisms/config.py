import os
import glob
from ruamel.yaml import YAML


def _find_file(file, fallback_wildcard):
    '''
    Return file (name) if it exists or evaluate fallback wildcard and return its name (if it results in only one record).
    '''
    if file is not None:
        if not os.path.exists(file):
            raise RuntimeError("File '{}' not found.".format(file))
        return file

    candidates = list(glob.glob(fallback_wildcard))
    if len(candidates) == 0:
        raise RuntimeError("There are no files matching '{}'.".format(fallback_wildcard))
    if len(candidates) > 1:
        raise RuntimeError(
            "Wildcard '{}' returned multiple results, file search is ambiguous.".format(fallback_wildcard))
    return candidates[0]


def _fix_config_path(path, base):
    if not path.startswith('/'):
        return base + '/' + path
    return path


def load_config(cfg_file):
    '''
    Find and load configuration yaml file and parse it.
    '''
    cfg_file = _find_file(cfg_file, './config.yaml')
    with open(cfg_file, "r", encoding="utf8") as fp:
        yaml = YAML(typ="safe")
        config = yaml.load(fp)

    # fix relative paths
    base = os.path.dirname(cfg_file)
    for dir in config['dirs']:
        config['dirs'][dir] = config['dirs'][dir].format(base)
    config['downloader']['exec'] = config['downloader']['exec'].format(base)
    config['comparator']['exec'] = config['comparator']['exec'].format(base)

    return config
