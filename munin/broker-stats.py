#!/usr/bin/env python3

import zmq

if __name__ == "__main__":
    context = zmq.Context()
    socket = context.socket(zmq.DEALER)
    socket.connect("tcp://127.0.0.1:9658")

    socket.send_multipart([b"get-runtime-stats"])
    reply = socket.recv_multipart()
    socket.disconnect("tcp://127.0.0.1:9658")

    data = {}

    it = iter(reply)
    for key in it:
        data[key] = next(it)

    print("broker.evaluated", data[b"evaluated-jobs"].decode('ascii'))
    print("broker.failed", data[b"failed-jobs"].decode('ascii'))
    print("broker.queued", data[b"queued-jobs"].decode('ascii'))
