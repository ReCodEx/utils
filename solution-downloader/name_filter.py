import re


def _force_regex_list(regs):
    '''
    Convert a string or list of strings into a list of regexes.
    '''
    if type(regs) != list:
        regs = [regs]
    
    return list(map(lambda r: re.compile(r), regs))


def _match_regs(regs, name):
    '''
    Return true if the name fully matches one of the regexes on the list.
    '''
    for reg in regs:
        if reg.fullmatch(name) is not None:
            return True
    return False


class NameFilter:
    '''
    Holds the name filter configuration and performs the filtering.
    '''
    def __init__(self, config) -> None:
        self._include = _force_regex_list(config.get('include_files', '.*') or '.*')
        self._exclude = _force_regex_list(config.get('exclude_files', []) or [])

    def _is_included(self, name):
        return _match_regs(self._include, name)

    def _is_excluded(self, name):
        return _match_regs(self._exclude, name)

    def valid_name(self, name):
        return self._is_included(name) and not self._is_excluded(name)