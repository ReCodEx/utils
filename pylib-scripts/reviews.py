from recodex import client_factory
import recodex.om as om
import sys
import argparse
from pathlib import Path

#
# The comments must be inserted into the downloaded files with the following format:
# One comment spans one or more lines, all the lines must be prefixed with ">>>".
# The comment is associated with the line of the original file that immediately precedes the first line of the comment.
# If the comment is an issue, the first line of the comment must start with ">>>!" instead of ">>>".
#
# No additional modifications of the original file are allowed
# (that includes adding empty lines, changing indentation, etc.).
#


def check_file(file: dict) -> bool:
    if file["malformedCharacters"] or file["tooLarge"]:
        print("FAILED (not a text file or too large)")
        return False

    lines = file["content"].splitlines()
    for line in lines:
        if line.startswith(">>>"):
            print("FAILED (file contains '>>>' line prefix used for our reviews)")
            return False

    return True


def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def extract_comments(path: str, original: str) -> list[str]:
    '''
    Extract comments from a commented file whilst comparing the content with the original file
    to ensure the right content was commented.
    - `path` is the path to the commented file
    - `original` is the content of the original file (as string)
    Returns a list of tuples (line_index, comment, issue)
    '''
    original_lines = original.splitlines()
    comments = []

    index = 0
    comment = []
    issue = False

    # read commented file as lines
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        while len(lines) > 0:
            line = lines.pop(0).rstrip("\n")
            if line.startswith(">>>"):
                line = line.lstrip(">>>")
                if line.startswith("!"):
                    issue = True
                    line = line.lstrip("!")
                line = line.lstrip(" ")
                comment.append(line)
            else:
                if len(comment) > 0:
                    comments.append((index, "\n".join(comment), issue))
                    comment = []
                    issue = False

                # check the content did not change
                original_line = original_lines.pop(0).rstrip("\n")
                if line != original_line:
                    print(f"ERROR: Modification found at {path}:{index}!")
                    print(f"Original line:\n{original_line}\n")
                    print(f"Modified line:\n{line}\n")
                    sys.exit(1)

                index += 1

    if len(comment) > 0:
        comments.append((index, "\n".join(comment), issue))
    return comments


def handle_download(solution, directory: str):
    files = solution.get_files()
    for file in files:
        print(f"Fetching content of file {file.get('name')} ... ", end="")
        content = file.get_content()
        if not check_file(content):
            continue

        write_file(Path(directory) / file.get('name'), content["content"])
        print("OK")


def handle_upload(solution, directory: str, rewrite: bool):
    if rewrite:
        # Delete the existing review if it exists
        if solution.get("review", "startedAt") is not None:
            print("Removing existing review ...")
            solution.get_review().remove()
    else:
        # closed reviews cannot be altered by this script
        if solution.get("review", "closedAt") is not None:
            print("The review is already closed, cannot upload comments!")
            sys.exit(0)

        if solution.get("review", "startedAt") is not None:
            print("Warning: The review has already been started, comments may be duplicated.")

    review = solution.start_review()
    files = solution.get_files()
    for file in files:
        print(f"Fetching content of file {file.get('name')} ... ", end="")
        content = file.get_content()
        if not check_file(content):
            continue
        print("OK")

        comments = extract_comments(Path(directory) / file.get('name'), content["content"])
        for line_index, comment, issue in comments:
            print(f"  Adding {'issue' if issue else 'comment'} for {file.get('name')}:{line_index} ...")
            review.add_comment(file.get('name'), line_index, comment, issue)

    print("Closing review ...")
    review.update_status(close=True)


def main():
    parser = argparse.ArgumentParser(description="A tool for downloading solution files and uploading review comments.")
    parser.add_argument("solution_id", help="ID of the solution being reviewed")
    parser.add_argument("directory", help="Directory to/from download solution files/upload review comments")
    parser.add_argument("--download", action="store_true", help="Download the solution files")
    parser.add_argument("--upload", action="store_true", help="Upload the review comments")
    parser.add_argument("--rewrite", action="store_true",
                        help="Additional flag for upload. The review is deleted if it already exists.")

    args = parser.parse_args()
    # exactly one of --download and --upload must be specified
    if not (args.download ^ args.upload):
        parser.error("Exactly one of --download and --upload must be specified")

    if not Path(args.directory).is_dir():
        parser.error(f"The specified path '{args.directory}' is not a directory!")

    client_factory.get_client_from_session()  # inject session into object model
    solution = om.Cache.cache().get(om.Solution, args.solution_id)
    print(f"Solution {solution.id()} by {solution.get_author().get_name()} created at {solution.get_ts('createdAt')}"
          f" (attempt {solution.get('attemptIndex')})")

    if args.download:
        handle_download(solution, args.directory)
    elif args.upload:
        handle_upload(solution, args.directory, args.rewrite)


if __name__ == "__main__":
    main()
