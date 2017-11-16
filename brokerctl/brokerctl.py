#!/usr/bin/env python3

import zmq
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You must specify a command (freeze/unfreeze)")
        sys.exit(1)

    broker_address = "tcp://127.0.0.1:9658"

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect(broker_address)

    if sys.argv[1] == "freeze":
        socket.send_multipart([b"freeze"])
    elif sys.argv[1] == "unfreeze":
        socket.send_multipart([b"unfreeze"])

    socket.disconnect(broker_address)

