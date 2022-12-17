#!/bin/bash

cd `dirname "$0"` || exit 1
BASE=`pwd`

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
rm -r ./$NAME/src ./$NAME/.cargo ./$NAME/Cargo.toml
cp -r ./src ./$NAME
cp -r ./.cargo ./$NAME
cp ./Cargo.toml ./$NAME

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
