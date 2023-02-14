#!/usr/bin/env python3

#
# Plagiarism detection manager handles soltuion downloads, invoation of external comparator, and upload of the results
# back to the ReCodEx. It relies on solution-downloader and recodex CLI tools.
#

import argparse
import logging
from config import load_config
from detected_similarity import load_similarities_from_csv, save_similarities
from downloader import Downloader
from files import FilesManager
from comparator import Comparator


def str_to_logging_level(level):
    '''
    Helper function that gets logging level as string and translates it into a constant from logging module.
    '''
    if level is None:
        return None
    if type(logging.__dict__[level]) != int:
        raise RuntimeError("Invalid logging level {}".format(level))
    return logging.__dict__[level]


def setup_logger(logger_config, file_manager):
    '''
    Initialize logging based on the configuration. The logger typically writes output to console as well as to a file.
    '''
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


def process_results(comparator):
    '''
    Parse the comparator output, aggregate similarity records, and upload them as a batch to ReCodEx.
    '''
    logging.getLogger().debug("Parsing comparator output {}".format(comparator.get_output_file()))
    similarities = load_similarities_from_csv(
        comparator.get_output_file(), comparator.get_output_columns(), **comparator.get_output_csv_params())
    comparator_args = " ".join(comparator.get_args())
    batch_id = save_similarities(comparator.get_name(), comparator_args, similarities)
    logging.getLogger().info("Similarities saved to ReCodEx as batch {}".format(batch_id))


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

    downloader = Downloader(config, file_manager, args.exercise)
    comparator = Comparator(config.get("comparator", {}), file_manager, args.exercise)

    # Download, compare, upload ...
    try:
        file_manager.prepare_working_dir()

        logging.getLogger().info("Starting the download process...")
        downloader.run()

        if downloader.has_new_solutions():
            logging.getLogger().info("Starting the external comparator...")
            logging.getLogger().debug(' '.join(comparator.get_args()))
            comparator.run()

            logging.getLogger().info("Uploading results to ReCodEx...")
            process_results(comparator)

            logging.getLogger().info("Updating solution archive...")
            downloader.merge_new_solutions()
            file_manager.update_solution_dirs()
        else:
            logging.getLogger().info("No new solutions detected.")
            file_manager.clear_working_dir()

    except Exception as e:
        logging.getLogger().exception(e)
        exit(2)

    logging.getLogger().info("Detection process completed.")
