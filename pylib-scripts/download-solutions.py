from recodex import client_factory
import recodex.om as om
import sys
import pathlib


if __name__ == "__main__":
    assignment_id, dir = sys.argv[1:3] if len(sys.argv) > 2 else (None, None)
    if not assignment_id or not dir or not pathlib.Path(dir).is_dir():
        print("Usage: {} <assignment_id> <directory>".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    client = client_factory.get_client_from_session()
    assignment = om.Cache.cache().get(om.Assignment, assignment_id)
    solutions = assignment.get_solutions()
    for solution in solutions:
        print(f'{solution.id()} {solution.get_ts("createdAt")} {solution.get_author().get_name()}')
        solution.download(dir)
