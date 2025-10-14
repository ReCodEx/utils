import argparse
import datetime
from os import path
from recodex import client_factory
from recodex.client import Client
from recodex.generated.swagger_client import DefaultApi


def _get_localized_names(localized_texts: dict, name: str = "name") -> dict:
    result = {}
    for lt in localized_texts:
        result[lt["locale"]] = lt[name]
    return result


def _get_groups(client: Client, root_id: str) -> dict:
    '''
    Retrieves all non-organizational (non-archived) groups in the hierarchy
    starting from the given root group ID.
    Returns a dictionary mapping group IDs to group data.
    '''
    groups = client.send_request_by_callback(
        DefaultApi.groups_presenter_action_default
    ).get_payload()

    index = {}
    for group in groups:
        index[group["id"]] = group

    if root_id not in index:
        raise Exception(f"Root group {root_id} not found")

    result = {}
    queue = [root_id]
    while len(queue) > 0:
        current_id = queue.pop(0)
        if current_id not in index:
            continue

        current_group = index[current_id]
        if not current_group["organizational"]:
            result[current_id] = current_group

        for child_id in current_group["childGroups"]:
            queue.append(child_id)

    return result


def _get_assignments(client: Client, group_ids: list, exercise_id: str):
    '''
    Retrieves all assignments in the given group that match the given exercise.
    '''
    assignments = client.send_request_by_callback(
        DefaultApi.exercises_presenter_action_assignments,
        path_params={"id": exercise_id}
    ).get_payload()

    return list(filter(lambda a: a["groupId"] in group_ids, assignments))


def _get_assignment_solutions(client: Client, assignment_id: str):
    '''
    Retrieves all solutions for the given assignment.
    '''
    return client.send_request_by_callback(
        DefaultApi.assignments_presenter_action_solutions,
        path_params={"id": assignment_id}
    ).get_payload()


def _get_solution_submissions(client: Client, solution_id: str):
    '''
    Retrieves all submissions for the given solution.
    '''
    return client.send_request_by_callback(
        DefaultApi.assignment_solutions_presenter_action_submissions,
        path_params={"id": solution_id}
    ).get_payload()


class Submission:
    '''
    Wrapper class for submission entity enriched with other data.
    A submission is one evaluation of the solution.
    A solution may have multiple evaluations
    (the last one is the one that counts for scoring).
    '''

    def __init__(self, submission: dict):
        keys = [
            "id",
            "submittedAt",
            "isDebug",
            "evaluation",
            "failure",
        ]
        for k in keys:
            setattr(self, k, submission[k])

    def get_score(self) -> float | None:
        if self.evaluation is None or "score" not in self.evaluation:
            return None
        return self.evaluation["score"]

    def download_logs(self, client: Client, target_path: str) -> None:
        '''
        Downloads the debug ZIP file for this submission to the given path.
        '''
        response = client.send_request_by_callback(
            DefaultApi.assignment_solutions_presenter_action_download_result_archive,  # noqa: E501
            path_params={"submissionId": self.id}
        )
        with open(target_path, "wb") as f:
            f.write(response.get_data_binary())

    def delete(self, client: Client) -> None:
        '''
        Deletes this submission.
        '''
        client.send_request_by_callback(
            DefaultApi.assignment_solutions_presenter_action_delete_submission,
            path_params={"submissionId": self.id}
        ).check_success()


class Solution:
    '''
    Wrapper class for assignment solution entity enriched with other data.
    '''

    def __init__(self, solution: dict, group: dict):
        keys = [
            "id",
            "attemptIndex",
            "assignmentId",
            "authorId",
            "createdAt",
            "accepted",
            "isBestSolution",
            "actualPoints",
            "bonusPoints",
            "overriddenPoints",
            "lastSubmission",
        ]
        for k in keys:
            setattr(self, k, solution[k])
        if self.lastSubmission:
            self.lastSubmission = Submission(self.lastSubmission)
        self.submission_ids = solution["submissions"]
        self.submissions = None

        self.group_id = group["id"]
        self.group_name = _get_localized_names(group["localizedTexts"])

    def load_submissions(self, client: Client) -> None:
        '''
        Load all submissions for the given solution.
        '''
        submissions = _get_solution_submissions(client, self.id)
        self.submissions = list(map(lambda s: Submission(s), submissions))
        self.submissions.sort(key=lambda s: s.submittedAt, reverse=True)

    def get_debug_submissions(self) -> list:
        '''
        Returns a list of submissions that were done in debug mode.
        '''
        if self.submissions is None:
            raise Exception("Submissions are not loaded yet")
        return list(filter(lambda s: s.isDebug, self.submissions))

    def resubmit(self, client: Client, debug: bool = True) -> None:
        '''
        Resubmits the solution for evaluation.
        If debug is True, the evaluation will be in debug mode.
        '''
        client.send_request_by_callback(
            DefaultApi.submit_presenter_action_resubmit,
            path_params={"id": self.id},
            body={"debug": debug}
        ).check_success()

    def get_id_and_info(self) -> str:
        '''
        Returns a string with solution ID and some info about it.
        '''
        # convert createdAt to a more readable format
        created_at = datetime.fromtimestamp(self.createdAt)
        return (f"Solution {self.id} (by {self.authorId}, "
                f"#{self.attemptIndex} {created_at})")

    def get_url(self, domain: str) -> str:
        '''
        Returns a URL to this solution in the ReCodEx web interface.
        '''
        return (f"{domain}/app/assignment/{self.assignmentId}/solution/{self.id}")

    @staticmethod
    def load_solutions(client: Client, group_id: str, exercise_id: str):
        '''
        Load all solutions for the given exercise and
        any group under given root group.
        '''
        groups = _get_groups(client, group_id)
        assignments = _get_assignments(client, list(groups.keys()),
                                       exercise_id)
        for assignment in assignments:
            aid = assignment["id"]
            gid = assignment["groupId"]
            for solution in _get_assignment_solutions(client, aid):
                yield Solution(solution, groups[gid])

    @staticmethod
    def filter_best(solution: "Solution"):
        return solution.isBestSolution


def load_solution(group_id: str, exercise_id: str, verbose: bool = False
                  ) -> list:
    if verbose:
        print("Loading solutions... ", end="", flush=True)
    solutions = list(Solution.load_solutions(client, group_id, exercise_id))
    if verbose:
        print(f"{len(solutions)} solutions found.")

    if verbose:
        print("Loading submissions.", end="")
    for solution in solutions:
        solution.load_submissions(client)
        if verbose:
            print(".", end="", flush=True)

    return solutions


def process_solution(client: Client, solution: Solution, target_dir: str,
                     no_resubmits: bool, verbose: bool, failures: list) -> str:

    zip_path = f"{target_dir}/{solution.id}.zip"
    if path.exists(zip_path):
        if verbose:
            print(f"Solution {solution.get_id_and_info()} already processed, "
                  "skipping.")
        return "done"  # already

    # try to download latest debug submission
    debug_submissions = solution.get_debug_submissions()
    if len(debug_submissions) > 0:
        latest = debug_submissions[0]

        if latest.failure is not None:
            if verbose:
                print(f"Evaluation of {solution.get_id_and_info()} FAILED!!!")
            failures.append(solution)
            return "failed"

        if latest.evaluation is None:
            if verbose:
                print(f"Evaluation of {solution.get_id_and_info()} is still "
                      "running.")
            return "pending"

        if verbose:
            print(f"Downloading ZIP for {solution.get_id_and_info()} "
                  f"to {zip_path}.")
        latest.download_logs(client, zip_path)
        return "downloaded"

    # try to resubmit
    if no_resubmits:
        if verbose:
            print(f"Solution {solution.get_id_and_info()} has no debug "
                  "submissions and resubmits are disabled, skipping.")
        return "skipped"
    if verbose:
        print(f"Resubmitting {solution.get_id_and_info()} for debug "
              "evaluation.")
    solution.resubmit(client, debug=True)
    return "resubmitted"


def get_domain() -> str:
    '''
    Returns the domain of the ReCodEx instance from the current session.
    '''
    session = client_factory.load_session()
    url = session.get_api_url()
    if url.endswith("/"):
        url = url[:-1]
    if url.endswith("/api"):
        url = url[:-4]
    return url


if __name__ == "__main__":
    # Process program arguments...
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, default=".",
                        help="Directory where the ZIPs will be stored.")
    parser.add_argument("--group", type=str,
                        default="0fe38443-05d3-44aa-8b6b-b25b9753c6ff",
                        help="ID of the top-level group in ReCodEx")
    parser.add_argument("--exercise", type=str, required=True,
                        help="Exercise whose solutions will be processed.")
    parser.add_argument("--no-resubmits", action="store_true",
                        help="Do not resubmit solutions (only download).")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Do not delete the debug re-submissions after"
                        " downloading.")
    parser.add_argument("--only-cleanup", action="store_true",
                        help="Only delete debug submissions (nothing else).")
    parser.add_argument("--verbose", action="store_true",
                        help="Print more information about what is being done.")
    args = parser.parse_args()

    # Establish ReCodEx session
    try:
        client = client_factory.get_client_from_session()
    except Exception as e:
        print("Cannot create ReCodEx client:", e)
        print("Use ReCodEx CLI to login first. This script will re-use the "
              "same session.")
        exit(1)

    # Main program
    solutions = load_solution(args.group, args.exercise)

    # download debug ZIPs, resubmit solutions if needed
    stats = {}
    if not args.only_cleanup:
        best_solutions = list(filter(Solution.filter_best, solutions))
        failures = []
        for solution in best_solutions:
            action = process_solution(client, solution, args.dir,
                                      args.no_resubmits, args.verbose,
                                      failures)
            stats[action] = stats.get(action, 0) + 1

        if failures:
            domain = get_domain()
            print("The following solutions have FAILED re-submissions:")
            for solution in failures:
                print(solution.get_url(domain))

    # cleanup debug submissions
    if not args.no_cleanup or args.only_cleanup:
        if args.verbose:
            print("Cleaning up debug submissions.", end="")
        for solution in solutions:
            pass
