import sys
import signal
import socket
import traceback


from identity import IdentityComponent, ChallengeFailed

# Capture SIGINT to quit cleanly 
signal.signal(signal.SIGINT, lambda signum, _: sys.exit(1))

def run():
    auth = IdentityComponent()

    with socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM
    ) as sock:
    
        sock.bind(("0.0.0.0", 4000))
        sock.settimeout(0.1)
        sock.listen()
        print(f"Server listening on {sock.getsockname()[1]}")

        next_connection_id = 1

        while True:
            try:
                clientsock, address = sock.accept()
            except TimeoutError:
                continue

            connection_id = next_connection_id
            next_connection_id += 1
                
            print(f"{connection_id}: New connection from {address}")
            
            try:
                auth.challenge(clientsock)
                print(f"{connection_id}: challenge met")
                # At this point the client is authenticated.
                # For now we just close the connection.
                clientsock.close()
            except ChallengeFailed as e:
                print(f"{connection_id}: Challenge failed: {e}")
                # Something went wrong with the underlying connection, close it.
                clientsock.close()
            except Exception as e:
                print(f"{connection_id}: Unexpected failure during challenge: {e}")
                traceback.print_tb(e.__traceback__)
                clientsock.close()
            
if __name__ == "__main__":
    run()