#!/usr/bin/env python3

#
# Plagiarism detection manager handles soltuion downloads, invoation of external comparator, and upload of the results
# back to the ReCodEx. It relies on solution-downloader and recodex CLI tools.
#

import argparse
import logging
from config import load_config
# from detected_similarity import load_similarities_from_csv, save_similarities
import downloader
from files import FilesManager
from comparator import Comparator


def str_to_logging_level(level):
    if level is None:
        return None
    if type(logging.__dict__[level]) != int:
        raise Exception("Invalid logging level {}".format(level))
    return logging.__dict__[level]


def setup_logger(logger_config, file_manager):
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)

    console_level = str_to_logging_level(logger_config.get('console_level', None))
    if console_level is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter("PDM (%(asctime)s): %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    file_level = str_to_logging_level(logger_config.get('file_level', None))
    if file_level is not None:
        file_handler = logging.FileHandler(file_manager.get_log_file())
        file_handler.setLevel(file_level)
        file_formatter = logging.Formatter("[%(asctime)s][%(levelname)-5.5s]: %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def download_solutions(config, file_manager, exercise):
    '''
    '''
    file_manager.prepare_working_dir()
    config_file = file_manager.get_working_dir() + '/config.yaml'
    downloader.prepare_config(config, 0, config_file)
    downloader.run_downloader(config, config_file, file_manager.get_working_dir(), exercise)
    return downloader.has_new_solutions(file_manager.get_working_dir(), file_manager.get_last_dir())


def process_results(config):
    # similarities = load_similarities_from_csv(
    #    './output.csv', config['comparator']['output']['columns'], **config['comparator']['output'].get('csv', {}))
    # batch_id = save_similarities(config['comparator']['name'], '', similarities)
    # print(batch_id)
    pass


if __name__ == "__main__":
    # Process program arguments...
    parser = argparse.ArgumentParser()
    parser.add_argument("exercise", type=str, help="Identifier of the exercise.")
    parser.add_argument("--config", type=str,
                        help="Path to yaml file with simulation configuration (./config.yaml is default).")
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    if args.exercise not in config.get('exercises', {}):
        print("Invalid exercise identifier '{}'. Config holds exercises '{}'.".format(
            args.exercise, "', '".join(config['exercises'].keys())))
    exercise_id = config['exercises'][args.exercise]

    # Initialization
    print("Initialization for evaluation of exercise {} ({}) ...".format(args.exercise, exercise_id))
    file_manager = FilesManager(config['dirs'], args.exercise)
    if file_manager.working_dir_exists():
        print("Working directory {} exists, probably since the last execution failed. Please, remove the working directory safely before executing the detection manager.".format(
            file_manager.get_working_dir()))
        exit(1)

    setup_logger(config.get('logger', {}), file_manager)

    comparator = Comparator(config.get("comparator", {}), args.exercise)

    try:
        logging.getLogger().info("Starting the download process...")
        any_new = download_solutions(config, file_manager, args.exercise)

        if any_new:
            logging.getLogger().info("Starting the external comparator...")
            comparator.run()

            logging.getLogger().info("Uploading results to ReCodEx...")

            logging.getLogger().info("Updating solution archive...")
            file_manager.update_solution_dirs()
        else:
            logging.getLogger().info("No new solutions detected.")
            file_manager.clear_working_dir()

    except Exception as e:
        logging.getLogger().exception(e)
        exit(2)

    logging.getLogger().info("Detection process completed.")
