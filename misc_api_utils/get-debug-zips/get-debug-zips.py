import argparse
from datetime import datetime
import csv
from os import path
from recodex import client_factory
from recodex.client import Client
from recodex.generated.swagger_client import DefaultApi

#
# Helper functions
#


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


def _load_users(client: Client, users: dict) -> dict:
    '''
    '''
    response = client.send_request_by_callback(
        DefaultApi.users_presenter_action_list_by_ids,
        body={"ids": list(users.keys())}
    ).get_payload()

    for user in response:
        users[user["id"]] = user

    return users

#
# Classes
#


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

        self.last_action_taken = None

    def get_id_and_info(self) -> str:
        '''
        Returns a string with solution ID and some info about it.
        '''
        # convert createdAt to a more readable format
        created_at = datetime.fromtimestamp(self.createdAt)
        author = self.get_author_name_struct()
        if author:
            author_name = author.get("lastName", "") + " " + author.get(
                "firstName", "")
        else:
            author_name = self.authorId

        return (f"Solution {self.id} (by {author_name}, "
                f"#{self.attemptIndex} {created_at})")

    def get_url(self, domain: str) -> str:
        '''
        Returns a URL to this solution in the ReCodEx web interface.
        '''
        return (f"{domain}/app/assignment/{self.assignmentId}/solution/{self.id}")  # noqa: E501

    def get_last_score(self) -> float | None:
        '''
        Returns the score of the last submission, or None if not available.
        '''
        if self.lastSubmission is None or self.lastSubmission.evaluation is None:  # noqa: E501
            return None
        return self.lastSubmission.evaluation.get("score", None)

    def get_last_compilation_failed(self) -> bool | None:
        '''
        Returns whether the last submission had compilation failed,
        or None if not available.
        '''
        if self.lastSubmission is None or self.lastSubmission.evaluation is None:  # noqa: E501
            return None
        return self.lastSubmission.evaluation.get("initFailed", None)

    def get_debug_submissions(self) -> list:
        '''
        Returns a list of submissions that were done in debug mode.
        '''
        if self.submissions is None:
            raise Exception("Submissions are not loaded yet")
        return list(filter(lambda s: s.isDebug, self.submissions))

    def get_author_name_struct(self) -> dict | None:
        '''
        Returns the decomposed name of the author, or None if not available.
        Returns dict with keys:
         - titlesBeforeName
         - firstName
         - lastName
         - titlesAfterName
        '''
        if not hasattr(self, "author") or self.author is None:
            return None
        return self.author.get("name", None)

    def load_submissions(self, client: Client) -> None:
        '''
        Load all submissions for the given solution.
        '''
        submissions = _get_solution_submissions(client, self.id)
        self.submissions = list(map(lambda s: Submission(s), submissions))
        self.submissions.sort(key=lambda s: s.submittedAt, reverse=True)

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

    def process_solution(self, client: Client, target_dir: str,
                         no_resubmits: bool, verbose: bool, failures: list
                         ) -> None:
        '''
        Processes a single solution:
        - if a ZIP file already exists, do nothing
        - if there is a debug submission with results, download the ZIP
        - if there is a debug submission pending or failed, report it
        - if there is no debug submission, resubmit the solution for debug
        evaluation (unless no_resubmits is True)

        Returns a string indicating what was done for statistics purposes.
        '''
        zip_path = f"{target_dir}/{self.id}.zip"
        if path.exists(zip_path):
            if verbose:
                print(f"Solution {self.get_id_and_info()} already processed, "
                      "skipping.")
            self.last_action_taken = "done"  # already
            return

        # try to download latest debug submission
        debug_submissions = self.get_debug_submissions()
        if len(debug_submissions) > 0:
            latest = debug_submissions[0]

            if latest.failure is not None:
                if verbose:
                    print(f"Evaluation of {self.get_id_and_info()} FAILED!!!")
                failures.append(self)
                self.last_action_taken = "failed"
                return

            if latest.evaluation is None:
                if verbose:
                    print(f"Evaluation of {self.get_id_and_info()} is still "
                          "running.")
                self.last_action_taken = "pending"
                return

            if verbose:
                print(f"Downloading ZIP for {self.get_id_and_info()} "
                      f"to {zip_path}.")
            latest.download_logs(client, zip_path)
            self.last_action_taken = "downloaded"
            return

        # try to resubmit
        if no_resubmits:
            if verbose:
                print(f"Solution {self.get_id_and_info()} has no debug "
                      "submissions and resubmits are disabled, skipping.")
            self.last_action_taken = "skipped"
            return
        if verbose:
            print(f"Resubmitting {self.get_id_and_info()} for debug "
                  "evaluation.")
        self.resubmit(client, debug=True)
        self.last_action_taken = "resubmitted"

    def cleanup_debug_submissions(self, client: Client, clean_failed: bool,
                                  verbose: bool) -> int:
        '''
        Deletes all (evaluated) debug submissions for the given solution.
        '''
        debug_submissions = self.get_debug_submissions()
        if (len(debug_submissions) == len(self.submissions)
                and len(debug_submissions) > 0):
            # all submissions are debug, we need to keep at least one
            debug_submissions = debug_submissions[:-1]

        deleted = 0
        for submission in debug_submissions:
            if submission.evaluation is None and submission.failure is None:
                continue  # still pending, do not delete
            if not clean_failed and submission.failure is not None:
                continue  # skipping failed submission

            if verbose:
                print(f"Deleting debug submission {submission.id} of "
                      f"{self.get_id_and_info()}.")
            submission.delete(client)
            deleted += 1

        return deleted

    @staticmethod
    def load_solutions(client: Client, group_id: str, exercise_id: str,
                       inject_authors: bool = True) -> list:
        '''
        Load all solutions for the given exercise and
        any group under given root group.
        '''
        groups = _get_groups(client, group_id)
        assignments = _get_assignments(client, list(groups.keys()),
                                       exercise_id)
        result = []
        for assignment in assignments:
            aid = assignment["id"]
            gid = assignment["groupId"]
            for solution in _get_assignment_solutions(client, aid):
                result.append(Solution(solution, groups[gid]))

        if inject_authors:
            authors = {}
            for solution in result:
                authors[solution.authorId] = None
            _load_users(client, authors)
            for solution in result:
                solution.author = authors[solution.authorId]

        return result

    @staticmethod
    def filter_best(solution: "Solution"):
        return solution.isBestSolution


#
# Important functions (main logic)
#

def load_solution(group_id: str, exercise_id: str, verbose: bool = False
                  ) -> list:
    '''
    Load all solutions for the given exercise and
    any group under given root group.
    '''
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


def save_manifest(solution: list, filepath: str) -> None:
    '''
    Saves a CSV manifest of the given solutions to the given file path.
    '''
    with open(filepath, "w", newline='', encoding="utf-8") as csv_file:
        fieldnames = ["solution_id", "attempt_index", "author_id",
                      "author_last_name", "author_first_name",
                      "created_at", "created_at_unix", "accepted",
                      "score", "compilation_failed", "last_action_taken",
                      "assignment_id", "group_id", ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for s in solution:
            author = s.get_author_name_struct()
            writer.writerow({
                "solution_id": s.id,
                "attempt_index": s.attemptIndex,
                "assignment_id": s.assignmentId,
                "author_id": s.authorId,
                "author_last_name": author.get("lastName", "") if author else "",  # noqa: E501
                "author_first_name": author.get("firstName", "") if author else "",  # noqa: E501
                "created_at": datetime.fromtimestamp(s.createdAt),
                "created_at_unix": s.createdAt,
                "accepted": s.accepted,
                "score": s.get_last_score(),
                "compilation_failed": s.get_last_compilation_failed(),
                "last_action_taken": s.last_action_taken
            })


#
# Top-level program
#
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
    parser.add_argument("--clean-failed", action="store_true",
                        help="When cleaning up debug submissions, also delete "
                             "failed submissions.")
    parser.add_argument("--verbose", action="store_true",
                        help="Print out more information.")
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
    solutions = load_solution(args.group, args.exercise, args.verbose)

    # Download debug ZIPs, resubmit solutions if needed
    stats = {}
    failures = []
    if not args.only_cleanup:
        best_solutions = list(filter(Solution.filter_best, solutions))
        for solution in best_solutions:
            solution.process_solution(client, args.dir, args.no_resubmits,
                                      args.verbose, failures)
            stats[solution.last_action_taken] = stats.get(
                solution.last_action_taken, 0) + 1

    # Cleanup debug submissions
    if not args.no_cleanup or args.only_cleanup:
        if args.verbose:
            print("Cleaning up debug submissions...")
        for solution in solutions:
            deleted = solution.cleanup_debug_submissions(client,
                                                         args.clean_failed,
                                                         args.verbose)
            if deleted > 0:
                stats["deleted submissions"] = stats.get(
                    "deleted submissions", 0) + deleted

    # Save manifest
    manifest_path = f"{args.dir}/manifest.csv"
    if args.verbose:
        print(f"Saving manifest to {manifest_path}.")
    save_manifest(best_solutions, manifest_path)

    # Print statistics
    if len(stats) == 0 or (len(stats) == 1 and "done" in stats):
        print("Nothing to be done.")
    else:
        print("Solutions processed summary:")
        for k in sorted(stats.keys()):
            print(f"  {k}: {stats[k]}")

    if failures and not args.clean_failed:
        domain = get_domain()
        print("The following solutions have FAILED re-submissions:")
        for solution in failures:
            print(solution.get_url(domain))

    pending = stats.get("pending", 0) + stats.get("resubmitted", 0)
    if pending > 0:
        print("Some solutions are still being evaluated, please run the "
              "script again later to download the ZIPs.")
