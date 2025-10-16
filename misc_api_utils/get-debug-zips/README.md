A script `get-debug-zip.py` for retrieving debug evaluation ZIP files -- i.e., a complete artifact of evaluation process from the worker.

The script loads the best solutions from given exercise and group (including all subgroups) and
- resubmits them in debug mode (if necessary),
- downloads the resulting ZIP files,
- cleans up debug submissions that are no longer needed.

If the evaluation is still pending, the script will report it and terminate. It might be necessary to run the script again later (or even multiple times) to get all the debug ZIPs.

The script always generates a `manifest.csv` file in the target directory, containing information about all processed solutions (including the action that was take during the last run).

**Arguments:**

- `--dir` - Directory where the ZIPs will be stored. (default: current directory)
- `--group` - ID of the top-level group in ReCodEx (default: `0fe38443-05d3-44aa-8b6b-b25b9753c6ff`); all non-archived subgroups will be processed as well.
- `--exercise` - Exercise ID whose solutions will be processed. (required)
- `--no-resubmits` - Prevents resubmitting solutions (only downloads them).
- `--no-cleanup` - Keeps the debug re-submissions after downloading.
- `--only-cleanup` - Only delete debug submissions (nothing else).
- `--clean-failed` - When cleaning up debug submissions, also delete failed submissions. In regular mode, failed submissions are kept to allow further investigation.
- `--verbose` - Print more information about what is being done.
