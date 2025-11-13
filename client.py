import socket

with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:
    sock.connect(("127.0.0.1", 4000))
    length_b  = sock.recv(2)
    length    =  int.from_bytes(length_b)
    challenge =  sock.recv(length)
    print("Received challenge: ", challenge)
    msg = b'world'
    print("Sending response: ", msg)
    sock.sendall(len(msg).to_bytes(2))
    sock.sendall(msg)
    length = int.from_bytes(sock.recv(2))
    result = sock.recv(length)
    print(result)

