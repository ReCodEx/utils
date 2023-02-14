import subprocess
import json
import logging

group_cache = None

# Low level functions for calling ReCodEx CLI process


def _recodex_call(args, **kwargs):
    '''
    Invoke recodex CLI process with given set of arguments.
    On success, stdout is returned as string. On error, None is returned and the message is printed out.
    '''
    res = subprocess.run(['recodex'] + args, capture_output=True, **kwargs)
    if res.returncode == 0:
        return res.stdout
    else:
        logging.getLogger().error("Error calling recodex CLI:\n" + res.stderr.decode('utf8'))
        return None


def create_batch(tool, tool_params):
    '''
    Create a new upload batch for detected plagiarisms and return its ID
    '''
    logging.getLogger().debug("ReCodEx API: creating new batch...")
    id = _recodex_call(['plagiarisms', 'create-batch', '--', tool, tool_params]).decode('ascii').strip()
    logging.getLogger().debug("ReCodEx API: new batch {} created".format(id))
    return id


def close_batch(id):
    '''
    Mark upload of given batch as completed.
    '''
    logging.getLogger().debug("ReCodEx API: closing batch {}".format(id))
    _recodex_call(['plagiarisms', 'update-batch', '--upload-completed', id])


def add_similarity(batch_id, solution_id, data):
    logging.getLogger().debug("ReCodEx API: adding similarity to batch {}, solution {}, author {}"
                              .format(batch_id, solution_id, data['authorId']))
    _recodex_call(['plagiarisms', 'add-similarity', '--json', batch_id, solution_id], input=json.dumps(data).encode())
