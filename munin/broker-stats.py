#!/usr/bin/env python3

import zmq

if __name__ == "__main__":
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)

    socket.send_multipart([b"get-runtime-stats"])
    reply = socket.recv_multipart()

    data = {}

    for key in reply:
        data[key] = next(reply)

    print("broker.evaluated", data["evaluated-jobs"])
    print("broker.failed", data["failed-jobs"])
    print("broker.queued", data["queued-jobs"])
