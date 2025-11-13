import sys
import signal
import socket

import auth

# Capture SIGINT to quit cleanly 
signal.signal(signal.SIGINT, lambda signum, _: sys.exit(1))

def run():
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
            
            try:
                auth.challenge(clientsock)
                
                # At this point the client is authenticated.
                # For now we just close the connection.
                clientsock.close()
            except:
                # Something went wrong with the underlying connection, close it.
                clientsock.close()
            
if __name__ == "__main__":
    run()