from recodex import client_factory
import recodex.om as om
import sys


if __name__ == "__main__":
    assignment_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not assignment_id:
        print("Usage: {} <assignment_id>".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    client = client_factory.get_client_from_session()
    assignment = om.Cache.cache().get(om.Assignment, assignment_id)
    if not assignment:
        print(f"Assignment {assignment_id} not found", file=sys.stderr)
        sys.exit(1)

    solutions = assignment.get_solutions()
    for solution in solutions:
        if solution.get("isBestSolution") and not solution.get("accepted"):
            print(f'Accepting {solution.id()} {solution.get_ts("createdAt")} {solution.get_author().get_name()} ...')
            solution.set_flag("accepted", True)
            thread = solution.get_comments_thread()
            comments = thread.get_comments()
            if comments:
                last_comment = comments[-1]
                print(f'  Last comment by {last_comment.user_name} at {last_comment.posted_at}:')
                print(f'    {last_comment.text}')
            thread.add_comment("Solution was accepted.")
