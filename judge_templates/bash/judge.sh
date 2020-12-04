#!/bin/bash

cd `dirname "$0"` || exit 2

ERRORS=""
REFERENCE_FILE="$1"
RESULT_FILE="$2"

# 
# Check the result...
# 

# Print out the judgement...
if [ -z "$ERRORS" ]; then
    echo "1.0"
    exit 0
else
    echo "0.0"
    echo "$ERRORS"
    exit 1
fi
