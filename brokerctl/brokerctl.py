#!/usr/bin/env python3

import zmq
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("You must specify a command (freeze/unfreeze)", file=sys.stderr)
        sys.exit(1)

    broker_address = "tcp://127.0.0.1:9658"

    if sys.argv[1] == "freeze":
        command = b"freeze"
    elif sys.argv[1] == "unfreeze":
        command = b"unfreeze"
    else:
        print("Unknown command", file=sys.stderr)
        sys.exit(1)

    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.setsockopt(zmq.LINGER, -1)
    socket.connect(broker_address)

    socket.send_multipart([command])

    socket.disconnect(broker_address)

