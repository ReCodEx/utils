#!/bin/bash

# Yay, another wrapper by Martin Krulis.
# Captures all the outputs (stderr redirected to stdout).
# Warnings are filtered out by sed and if any output remains,
# it is treated as compilation error.
# (This is necessary, since swipl returns 0 even if compilation fails.)

EXECUTABLE=$1
shift

OUTPUT=`"$EXECUTABLE" "$@" 2>&1`
ERRORS=`echo "$OUTPUT" | sed -e '/^Warning:/,+1d'`
RES=$?
if [[ $RES == 0 && "$ERRORS" != "" ]]; then
	RES=1
fi

echo "$OUTPUT"
exit $RES
