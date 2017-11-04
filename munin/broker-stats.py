#!/usr/bin/env python3

import zmq
import sys

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "config":
        print("graph_title Broker job counters")
        print("graph_vlabel jobs")
        print("graph_category broker")
        print("evaluated.label Jobs evaluated")
        print("failed.label Failed jobs")
        print("queued.label Jobs in queue")
        sys.exit(0)

    broker_address = "tcp://127.0.0.1:9658"

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(broker_address)

    socket.send_multipart([b"get-runtime-stats"])
    reply = socket.recv_multipart()
    socket.disconnect(broker_address)

    data = {}

    it = iter(reply)
    for key in it:
        data[key] = next(it)

    print("evaluated.value", data[b"evaluated-jobs"].decode('ascii'))
    print("failed.value", data[b"failed-jobs"].decode('ascii'))
    print("queued.value", data[b"queued-jobs"].decode('ascii'))
