import sys
import signal
import socket

old_signal_handler = signal.signal(signal.SIGINT, lambda signum, _: sys.exit(1))
print(old_signal_handler)

with socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM
) as sock:
    sock.bind(("0.0.0.0", 4000))
    sock.settimeout(0.01)
    sock.listen()
    print(f"Server listening on {sock.getsockname()[1]}")

    while True:
        try:
            clientsock, address = sock.accept()
        except TimeoutError:
            continue
            
        print(f"New connection from {address}")

        # Super-basic challenge-response setup, to be replaced.
        expected = {
            "challenge": { "len": 5, "val": b'hello' },
            "response":  { "val": b'world', "len": 5 }
        }

        clientsock.sendall(expected["challenge"]["len"].to_bytes(2) + expected["challenge"]["val"])

        try:
            # Get the length of the response data:
            l = int.from_bytes(clientsock.recv(2))
            if l != expected["response"]["len"]:
                clientsock.close()
                continue
            # This should be replaced with a signature validation.
            response = clientsock.recv(l)
            if response == expected["response"]["val"]:
                msg = b'Connection authenticated!'
                clientsock.send(len(msg).to_bytes(2) + msg)
            else:
                clientsock.close()
            
            # At this point the client is authenticated.
            # For now we just close the connection.
            clientsock.close()
        except:
            # Something went wrong with the underlying connection, close it.
            clientsock.close()
        
