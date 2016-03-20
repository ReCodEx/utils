#!/bin/bash


# Default values
WORKER_BIN=/usr/bin/recodex-worker
WORKER_CONF=/etc/recodex/worker/config-1.yml
BROKER_BIN=/usr/bin/recodex-broker
BROKER_CONF=/etc/recodex/broker/config.yml

FILE_SERVER=
FAKE_SUBMIT=
EXERCISES_DIR=
EXERCISES=

TEMP_DIR=/tmp/recodex

START_FS=true
START_BROKER=true
START_WORKER=true


# first param is argv[0] of the whole script
function init_paths {
	local path_to_script=$(dirname "$1")
	mkdir -p ${TEMP_DIR}
	if [ ! -f "$path_to_script/file_server.py" -o ! -f "$path_to_script/fake_submit.py" ]; then
		# we need to clone utils repo
		git clone https://github.com/ReCodEx/utils.git "${TEMP_DIR}/utils" > /dev/null 2>&1
		FILE_SERVER="${TEMP_DIR}/utils/submission/file_server.py"
		FAKE_SUBMIT="${TEMP_DIR}/utils/submission/fake_submit.py"
	else
		# file server is in the same repository as this script
		FILE_SERVER="$path_to_script/file_server.py"
		# and fake submit too
		FAKE_SUBMIT="$path_to_script/fake_submit.py"
	fi
	
	# try to find exercises repo in the same dir as the root of utils repo is
	local repo_root="$path_to_script/../.." # up are "submission" and "utils" dirs
	if [ -d "$repo_root/exercises" ]; then
		# it exists, so set up the dir
		EXERCISES_DIR="$repo_root/exercises"
	else
		# else clone the repo from our private git
		# NOTE: you should have set up passwordless login to virtual machine by name
		# "recodex" (in ~/.ssh/config)
		git clone ssh://recodex:/opt/git/exercises.git "${TEMP_DIR}/exercises" > /dev/null 2>&1
		EXERCISES_DIR="${TEMP_DIR}/exercises"
	fi
}

function parse_opts {
	OPTS=`getopt -o fbws -l fileserver,broker,worker,submit -- "$@"`
	if [ $? != 0 ]
	then
	    exit 1
	fi
	
	eval set -- "$OPTS"
	
	while true ; do
	    case "$1" in
	        -f | --fileserver) 
				shift
				;;
	        -b | --broker)
				START_FS=false
				shift
				;;
	        -w | --worker)
				START_FS=false
				START_BROKER=false
				shift
				;;
			-s | --submit)
				START_FS=false
				START_BROKER=false
				START_WORKER=false
				shift
				;;
	        --)
				shift
				break
				;;
	    esac
	done
	
	if [ $# -eq 0 ]; then
		# Run all the exercises available
		EXERCISES=$(ls ${EXERCISES_DIR})
	else
		for arg in "$@"; do
			EXERCISES="$EXERCISES $arg"
		done
	fi
}

function check_or_init_binaries {
	# Worker
	if [ ! -f ${WORKER_BIN} -o ! -f ${WORKER_CONF} ]; then
		# worker needs to be build
		git clone https://github.com/ReCodEx/worker.git "${TEMP_DIR}/worker" > /dev/null 2>&1
		pushd .
		cd ${TEMP_DIR}/worker
		mkdir -p build
		cd build
		cmake ..
		make -j 4
		popd
		WORKER_BIN="${TEMP_DIR}/worker/build/recodex-worker"
		WORKER_CONF="${TEMP_DIR}/worker/examples/config.yml"
	fi

	# Broker
	if [ ! -f ${BROKER_BIN} -o ! -f ${BROKER_CONF} ]; then
		# broker needs to be build
		git clone https://github.com/ReCodEx/broker.git "${TEMP_DIR}/broker" > /dev/null 2>&1
		pushd .
		cd ${TEMP_DIR}/broker
		mkdir -p build
		cd build
		cmake ..
		make -j 4
		popd
		WORKER_BIN="${TEMP_DIR}/broker/build/recodex-broker"
		WORKER_CONF="${TEMP_DIR}/broker/examples/config.yml"
	fi
}

function start_broker {
	if $START_BROKER; then
		${BROKER_BIN} -c ${BROKER_CONF} &
		BROKER_PID=$!
		if [ $? -ne 0 ];then
			echo "Starting broker failed"
			exit 1
		else
			echo "Broker started"
		fi
	fi
}

function stop_broker {
	if $START_BROKER; then
		kill ${BROKER_PID}
		wait ${BROKER_PID} 2> /dev/null
		echo "Broker stopped"
	fi
}

function start_worker {
	if $START_WORKER; then
		${WORKER_BIN} -c ${WORKER_CONF} > /dev/null 2>&1 &
		WORKER_PID=$!
		if [ $? -ne 0 ]; then
			echo "Starting worker failed"
			exit 1
		else
			echo "Worker started"
		fi
	fi
}

function stop_worker {
	if $START_WORKER; then
		kill ${WORKER_PID}
		wait ${WORKER_PID} 2> /dev/null
		echo "Worker stopped"
	fi
}


function start_file_server {
	if $START_FS; then
		TEMP_OUT=${TEMP_DIR}/file_server_output.txt
		${FILE_SERVER} > ${TEMP_OUT} 2>&1 &
		FILE_SERVER_PID=$!
		sleep 1
		SERVER_DIR=$(head -n 1 ${TEMP_OUT} | grep -o "/tmp/tmp[^ ]*")
		if [ "${SERVER_DIR}" = "" ]; then
			echo " Cannot read file server directory!"
			exit 1
		fi
		echo "File server started in ${SERVER_DIR}"
	fi
}

function stop_file_server {
	if $START_FS; then
		kill -s SIGINT ${FILE_SERVER_PID}
		wait ${FILE_SERVER_PID} 2> /dev/null
		rm ${TEMP_OUT}
		rm -rf ${SERVER_DIR}
		echo "File server stopped"
	fi
}

# first param is name of exercise (subdir in EXERCISES_DIR dir)
function submit_exercise {
	if [ ! -d ${EXERCISES_DIR}/$1 ]; then
		echo "No such exercise $1!!!"
		return
	fi

	if $START_FS; then
		rm -rf ${SERVER_DIR}/tasks/*
		cp ${EXERCISES_DIR}/$1/data/* ${SERVER_DIR}/tasks
	fi
	${FAKE_SUBMIT} "${EXERCISES_DIR}/$1/submit" > /dev/null
	echo "Submitting job $1 ..."
}

function wait_time {
	echo "Waiting $1 s"
	sleep $1
}

# ===== Main =====

# command line arguments are from which stage to run (optional) and 
# which exercises submit (optional, default all)

init_paths $0
parse_opts "$@"

# Prepare all resources
start_file_server
start_broker
start_worker

# Send some submits
for ec in ${EXERCISES}; do
	submit_exercise $ec
	sleep 1
done

# Wait to finish execution
wait_time 20

# Copy interesting files to result dir
result_dir=~/Desktop/job_results
rm -rf $result_dir
cp -R ${SERVER_DIR}/results $result_dir
ln -s /var/log/recodex/broker.log $result_dir/broker.log
ln -s /var/log/recodex/worker.log $result_dir/worker.log

# Do the cleanup
stop_worker
stop_broker
stop_file_server

rm -rf ${TEMP_DIR}

