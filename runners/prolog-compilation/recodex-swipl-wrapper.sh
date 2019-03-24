#!/bin/bash

# Yay, another wrapper by Martin Krulis.
# Captures all the outputs (stderr redirected to stdout).
# Any output is treated as error.

EXECUTABLE=$1
shift

OUTPUT=`"$EXECUTABLE" "$@" 2>&1`
RES=$?

if [ $RES -ne 0 ]; then
	echo "$OUTPUT"
	exit $RES
fi

if [ ! -z "$OUTPUT" ]; then
	echo "$OUTPUT"
	exit 1
fi

exit 0
