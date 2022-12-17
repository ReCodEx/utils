#!/bin/bash

# When this script is started, it is expected that the pre-compiled project directory has been alredy unzipped
# (path to it is given as argument) and input files (as well as extra files) are loaded in current (box) directory.
BOXDIR=`pwd`

ZIP="$1"
if [ ! -f "$ZIP" ]; then
	echo "Project directory bundle was not downloaded."
	exit 1
fi

# Rename input directory to "project" (a hack to avoid recompilation ... the libraries are precompiled in fixed path $BOXDIR/project)
rm -rf $BOXDIR/project
unzip -qq "$ZIP" -d $BOXDIR/project

# Make sure src dir exists
SRC="$BOXDIR/project/src"
mkdir -p "$SRC"
if [ ! -d "$SRC" ]; then
	echo "The src subdir not found in project directory."
	exit 1
fi

# Move Rust files into the right directory for compilation
mv ./*.rs "$SRC"

# Execute build
cd "$BOXDIR/project"
cargo --quiet --frozen build
RES=$?
if [[ $RES != 0 ]]; then
	exit $RES
fi
cd "$BOXDIR"

# Move the executable to current dir, so it can be located 
EXE="$BOXDIR/project/target/debug/main"
if [ -f "$EXE" ]; then
	mv "$EXE" "$BOXDIR/solution"
fi
