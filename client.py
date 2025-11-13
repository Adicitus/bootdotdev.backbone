import socket

import frame

with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:
    sock.connect(("127.0.0.1", 4000))
    challenge =  frame.read(sock)
    print("Received challenge: ", challenge)
    msg = b'world'
    print("Sending response: ", msg)
    frame.send(sock, msg)
    result = frame.read(sock)
    print(result)

