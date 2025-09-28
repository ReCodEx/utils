#!/bin/bash

PROJECT_DIR="$1"
OUTPUT_DIR=`dirname "$0"`/bin
EXE_NAME='__recodex_exe__'  # normalized name of the loader executable (build will ensure its existence)
OUT_ZIP=`dirname "$0"`/bin.zip  # output zip file containing packed bin (output) directory

cd "$PROJECT_DIR" || exit 1

# Find the .csproj file in the project root (there must be exactly one)
CS_PROJS=`find . -maxdepth 1 -type f -name '*.csproj'`
if [ -z "$CS_PROJS" ]; then
  echo "No .csproj file found in the project root."
  exit 1
fi

if [ `echo "$CS_PROJS" | wc -l` -gt 1 ]; then
  echo "Multiple .csproj files found in the project root, there must be exactly one!"
  echo "$CS_PROJS"
  exit 1
fi

# Check the .csproj file whether it is safe
CS_PROJ=`echo "$CS_PROJS" | head -n 1`

if [ -n "`cat "$CS_PROJ" | grep -E '<Project\s' | grep -v -E 'Sdk="Microsoft.NET.Sdk'`" ]; then
  echo "The .csproj file defines project SDK different than 'Microsoft.NET.Sdk', which is not allowed."
  exit 1
fi
if [ -n "`cat "$CS_PROJ" | grep -E '<Sdk[>\s]'`" ]; then
  echo "The .csproj file contains <Sdk> element(s), which are not allowed."
  exit 1
fi
if [ -n "`cat "$CS_PROJ" | grep -E '<Target[>\s]'`" ]; then
  echo "The .csproj file contains <Target> element(s), which are not allowed."
  exit 1
fi
if [ -n "`cat "$CS_PROJ" | grep -E '<UsingTask[>\s]'`" ]; then
  echo "The .csproj file contains <UsingTask> element(s), which are not allowed."
  exit 1
fi
if [ -n "`cat "$CS_PROJ" | grep -E '<Import[>\s]'`"	 ]; then
  echo "The .csproj file contains <Import> element(s), which are not allowed."
  exit 1
fi

# Find all .targets, .props, and .dll files (which are not allowed)
BAD_FILES=`find . -type f \( -name '*.targets' -o -name '*.props' -o -name '*.dll' \)`
if [ -n "$BAD_FILES" ]; then
  echo "The project contains .targets, .props or .dll files, which are not allowed:"
  echo "$BAD_FILES"
  exit 1
fi


# Build the project
BUILD_OUT=`/opt/dotnet/dotnet build --tl:off -v:q --nologo -p:PublishAot=true -p:EnableUnsafeBinaryFormatterInDesigntimeLicenseContextSerialization=false -r linux-x64 -c Release -o "$OUTPUT_DIR" 2>&1`
if [ $? -ne 0 ]; then
  echo "$BUILD_OUT"
  echo "Build failed."
  exit 1
fi

# If there are any warnings, print them (absence "0 Warning(s)"" message is taken as a sign)
WARN_REPORT=`echo "$BUILD_OUT" | grep -E'\s+0 Warning'`
if [ -z "$WARN_REPORT" ]; then
  echo "$BUILD_OUT"
fi


# Find the executable (loader) and rename it so the next pipeline knows which file to run
cd "$OUTPUT_DIR" || exit 1
EXES=`find "$OUTPUT_DIR" -type f -executable | grep -v -E '[.]dll$'`
if [ -z "$EXES" ]; then
  echo "No executable files found in output directory."
  exit 1
fi

if [ `echo "$EXES" | wc -l` -gt 1 ]; then
  echo "Multiple executable files found in output directory. Unable to decide, which one to use:"
  echo "$EXES"
  exit 1
fi

EXE=`echo "$EXES" | head -n 1`
mv "$EXE" "$OUTPUT_DIR/$EXE_NAME" || exit 1


# Zip the output directory (assuming we are still in it)
zip -q -r "$OUT_ZIP" . || exit 1

exit 0
