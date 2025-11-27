# Modules used when module is run directly:
import signal
import tomllib
import time

# Modules that are core to the server:
import socket
import traceback
import threading

from identity import IdentityComponent, ChallengeFailed
import handle

class BackboneServer:
    def __init__(self, settings={}, identities:IdentityComponent = None) -> None:
        self.settings = settings
        
        self.auth = identities
        if self.auth == None:
            self.auth = IdentityComponent()

        self.server_thread = None
        self.stop_flag     = None
    
    def start(self, block:bool = False) -> bool:

        if self.stop_flag != None and not self.stop_flag.is_set():
            return False

        self.stop_flag = threading.Event()
        self.server_thread    = threading.Thread(target=BackboneServer._run, kwargs={
            "settings": self.settings,
            "auth": self.auth,
            "stop_flag": self.stop_flag,
        })
        

        self.stop_flag.clear()

        self.server_thread.start()
        if block:
            self.server_thread.join()
        
        return True
    
    def is_running(self):
        return self.server_thread != None and self.server_thread.is_alive()
    
    def stop(self, block:bool = False):
        if self.stop_flag == None:
            return False
        print(f"Stopping server {self}")
        self.stop_flag.set()
        if block and self.server_thread:
            self.server_thread.join()
        
        return True
    
    @staticmethod
    def _run(stop_flag:threading.Event, auth:IdentityComponent, settings):
        
        next_connection_id = 1
        handlers = {}

        port = settings["port"] if "port" in settings else 4000

        try:
            with socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM
            ) as sock:
            
                sock.bind(("0.0.0.0", port))
                sock.settimeout(0.1)
                sock.listen()
                print(f"Server listening on {sock.getsockname()[1]}")

                while not stop_flag.is_set():
                    try:
                        clientsock, address = sock.accept()
                    except TimeoutError:
                        continue
                
                    connection_id = next_connection_id
                    next_connection_id += 1
                        
                    print(f"{connection_id}: New connection from {address}")

                    try:
                        client_socket, client = auth.challenge(clientsock, settings["challenge_size"])
                        print(f"{connection_id}: challenge met for client {client.id}")

                        if handle.get_client_queue(client.id) != None:
                            print(f"{connection_id}: Client {client.id} is already connected, dropping this connection.")
                            client_socket.close()
                            continue
                        
                        # At this point the client is authenticated.
                        handler = handle.ClientHandler(
                            client_connection=client_socket,
                            client=client,
                            server=auth
                        )

                        handlers[client.id.hex] = handler
                        handler.start()

                    except ChallengeFailed as e:
                        print(f"{connection_id}: Challenge failed: {e}")
                        clientsock.close()
                    except Exception as e:
                        # Something went wrong with the underlying connection, close it.
                        print(f"{connection_id}: Unexpected failure during challenge: {e}")
                        traceback.print_tb(e.__traceback__)
                        clientsock.close()
        finally:
            for handler in handlers.values():
                try:
                    handler.stop()
                except Exception as e:
                    print(f"Exception occurred while trying to stop a handler: {e}")
                    continue
            for handler in handlers.values():
                if handler.is_running():
                    print(f"Waiting for {handler} to stop running")
                    handler.thread.join()

            print("Server stopped.")

if __name__ == "__main__":
    with open("./settings.toml", 'rb') as f:
        settings = tomllib.load(f)
    server = BackboneServer(settings=settings)

    def terminate(signum, frame):
        print(f"Received {signal.Signals(signum).name} at {frame}")
        print(f"Trying to stop the server...")
        server.stop()

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)

    server.start(block=False)
    while server.is_running():
        # Busy-waiting so that we can handle the SIGINT, SIGTERM
        time.sleep(1)

