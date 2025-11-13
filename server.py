import sys
import signal
import socket

import frame

# Capture SIGINT to quit cleanly 
signal.signal(signal.SIGINT, lambda signum, _: sys.exit(1))

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

        frame.send(clientsock, expected["challenge"]["val"])
        try:
            # This should be replaced with a signature validation.
            response = frame.read(clientsock)
            if response == expected["response"]["val"]:
                msg = b'Connection authenticated!'
                frame.send(clientsock, msg)
            else:
                clientsock.close()
            
            # At this point the client is authenticated.
            # For now we just close the connection.
            clientsock.close()
        except:
            # Something went wrong with the underlying connection, close it.
            clientsock.close()
        
