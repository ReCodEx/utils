#!/bin/bash

# A thin wrapper around running the compiled .NET executable.
# This is basically a hack, since we have no means how to identify the executable within the bin directory
# (using current constructs of ReCodEx pipelines).
# This may be removed in the future (if we add support for more customizable execution commands).

# The first argument is the bin directory, remaining arguments are passed to the executable
EXEC_DIR="$1"
shift
EXEC_PATH="$EXEC_DIR/__recodex_exe__"  # normalized name of the loader executable

$EXEC_PATH "$@"
EXIT_CODE=$?
exit $EXIT_CODE
