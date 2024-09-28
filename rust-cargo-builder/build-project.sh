#!/bin/bash

cd `dirname "$0"` || exit 1
BUILDER=`pwd`
BUILDER=`basename "$BUILDER"`
cd ..
BASE=`pwd`
if [ ! -d "./$BUILDER" ]; then
	echo "Cannot find my own directory, something is really odd..."
	exit 200
fi

BOX=/box
if [ ! -d $BOX ]; then
	echo "No $BOX directory..."
	exit 2
fi

if [ ! -w $BOX ]; then
	echo "Insuficient rights for $BOX directory..."
	exit 3
fi

echo "Clearing $BOX ..."
rm -rf $BOX/*

NAME=project

echo "Preparing project solution template..."
rm -rf ./$NAME
cargo init $NAME
rm -r ./$NAME/src ./$NAME/.cargo ./$NAME/Cargo.toml ./$NAME/.git ./$NAME/.gitignore
cp -r ./$BUILDER/src ./$NAME || exit 201
cp -r ./$BUILDER/.cargo ./$NAME || exit 201
cp ./$BUILDER/Cargo.toml ./$NAME || exit 201

echo "Loading dependencies into ./vendor directory..."
cd ./$NAME || exit 1
cargo vendor

cd .. || exit 1
mv $NAME $BOX
cd $BOX/$NAME

echo "Building project to make sure the dependencies are compiled..."
cargo build
rm -rf ./target/debug/main ./target/debug/main* ./target/debug/incremental

echo "Zipping the package $BASE/$NAME.zip..."
zip -r "$BASE/$NAME.zip" .
rm -rf $BOX/*
