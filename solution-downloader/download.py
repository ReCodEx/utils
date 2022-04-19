#!/usr/bin/env python3

import argparse
import os
import glob
import pathlib
from ruamel import yaml
import recodex_api
from metadata import MetadataHandler


# Low level functions for calling ReCodEx CLI process


def find_file(file, fallback_wildcard):
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


def load_config(cfg_file):
    '''
    Load configuration yaml file and parse it.
    '''
    with open(cfg_file, "r") as fp:
        config = yaml.safe_load(fp)
    return config


def prepare_allowed_logins(id2login, allowed_arg):
    '''
    Create list of logins of students to download (based on --students arg).
    If arg is missing (empty), all logins in the translation table are allowed.
    '''
    res = {}
    logins = allowed_arg.split(',') if allowed_arg else None
    for id in id2login:
        login = id2login[id]
        if logins is None or login in logins:
            res[login] = True
    return res


def get_groups(config_groups):
    '''
    Assemble all relevant group objects.
    '''
    groups = []
    for root in config_groups:
        groups = groups + recodex_api.get_relevant_groups(root.get('id', None), root.get('recursive', False))
    return groups


if __name__ == "__main__":
    # Process program arguments...
    parser = argparse.ArgumentParser()
    parser.add_argument("exercise", type=str, help="Identifier of the exercise.")
    parser.add_argument("--dest_dir", type=str,
                        help="Destination directory where the solutions are downloaded.")
    parser.add_argument("--config", type=str,
                        help="Path to yaml file with simulation configuration (./config.yaml is default).")
    parser.add_argument("--manifest", type=str,
                        help="Path to csv file where the manifest will be saved (list of all downloaded solutions).")
#    TODO
#    parser.add_argument("--users", type=str,
#                        help="Comma separated list of logins (only solutions of these users will be downloaded).")
#    parser.add_argument("--late", default=False, action="store_true",
#                        help="Mark downloaded solutions as late.")
    args = parser.parse_args()

    # Load configuration
    config = load_config(find_file(args.config, './config.yaml'))
    if args.exercise not in config.get('exercises', {}):
        print("Invalid exercise identifier '{}'. Config holds exercises '{}'.".format(
            args.exercise, "', '".join(config['exercises'].keys())))

    # Prepare destination directory
    if args.dest_dir is not None:
        pathlib.Path(args.dest_dir).mkdir(parents=True, exist_ok=True)
        if not os.path.exists(args.dest_dir):
            raise RuntimeError("Unable to create destination directory '{}'.".format(args.dest_dir))

    # Prepare metadata handler which generates paths and saves manifest
    metadata = MetadataHandler(args.dest_dir, config)
    if args.manifest:
        metadata.open_mainfest(args.manifest)

    # Find assignment for selected exercise
    exercise_id = config['exercises'][args.exercise]

    # Iterate over all relevant groups, all their assignments, and all their solutions
    print("Loading groups ...")
    groups = get_groups(config.get('groups', []))
    group_counter = 0
    for group in groups:
        metadata.set_group(group)
        group_counter += 1
        print("Loading assignments in group {} ({} of {})...".format(group['id'], group_counter, len(groups)))

        assignments = recodex_api.get_assignments(group['id'], exercise_id)
        assignment_counter = 0
        for assignment in assignments:
            metadata.set_assignment(assignment)
            assignment_counter += 1
            print(" - Loading list of solutions of assignment {} ({} of {})...".format(
                assignment['id'], assignment_counter, len(assignments)))

            solutions = recodex_api.get_solutions(assignment['id'], config.get('solutions', {}))
            solution_counter = 0
            for solution in solutions:
                metadata.set_solution(solution)
                solution_counter += 1
                print("    - Processing solution {} ({} of {}) ..."
                      .format(solution['id'], solution_counter, len(solutions)))

                if args.dest_dir:  # Handle download
                    path = metadata.get_path()  # of current solution
                    recodex_api.download_solutions(solution['id'], path, args.dest_dir)
                metadata.write_manifest()  # of current solution

    metadata.close_manifest()
    print("And we're done here.")
