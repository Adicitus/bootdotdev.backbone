# handle.py
# Client handler and associated functionality
import threading
import socket

from uuid import UUID
from queue import Empty, Queue

import frame

from identity import Identity, IdentityComponent

class TerminateTaskGroup(Exception):
    def __init__(self):
        super().__init__("A monitor has called for task group to terminate.")

# Global server queue, used to pass messages to the main thread
server_queue = Queue()
# Individual client queues, used to pass messages to individual handlers
queues = {}
# Semaphore to coordinate access to the queues, since hashmaps are not thread-safe
queues_semaphore = threading.Semaphore()

def get_client_queue(client_id:UUID):
    queue = None
    queues_semaphore.acquire()
    if client_id.hex in queues:
        queue = queues[client_id.hex]
    queues_semaphore.release()
    return queue

def get_server_queue():
    return server_queue

def _register_client(client_id:UUID) -> Queue:
    queues_semaphore.acquire()
    queues[client_id.hex] = Queue()
    queues_semaphore.release()
    return queues[client_id.hex]

def _deregister_client(client_id:UUID) -> None:
    queues_semaphore.acquire()
    queues[client_id.hex] = None
    queues_semaphore.release()


        

class ClientHandler:
    def __init__(self, client_connection: socket.socket, client:Identity, server:IdentityComponent):
        self.connection = client_connection
        self.client = client
        self.server = server
        self.stop_flag = threading.Event()
    
    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.stop_flag.clear()
        self.thread.start()
    
    def stop(self, block=False):
        self.stop_flag.set()
        if block and self.thread:
            self.thread.join()

    def is_running(self):
        return self.thread != None
    
    def _run(self):
        print("Via stdout: handler started")
        get_server_queue().put("Via Queue: handler started")

        socket_semaphore = threading.Semaphore()
        arguments = (self.connection, socket_semaphore, self.stop_flag, self.client, self.server)
        self.queue_monitor  = threading.Thread(target=ClientHandler._monitor_queue, args=arguments, daemon=False)
        self.socket_monitor = threading.Thread(target=ClientHandler._monitor_socket, args=arguments, daemon=False)

        self.queue_monitor.start()
        self.socket_monitor.start()
        self.stop_flag.wait()

        print("Handler stopping...")

        self.queue_monitor.join()
        self.socket_monitor.join()

        get_server_queue().put("Via Queue: handler stopped")
        print("Handler stopped")
        
        self.queue_monitor = None
        self.socket_monitor = None
        self.thread = None

    @staticmethod
    def _monitor_queue(client_connection: socket.socket, send_access:threading.Semaphore, stop_flag:threading.Event, client:Identity, server:IdentityComponent):
        print("Queue monitor started")
        try:
            client_queue = _register_client(client.id)
            while True:
                if stop_flag.is_set():
                    break
                
                try:
                    msg = client_queue.get(timeout=1)
                except Empty:
                    continue
            
                # TODO: Implement message handling.
                # For now we'll just stop the thread if we receive any data via the queue.
                break
        finally:
            print("QM stopping...")
            _deregister_client(client.id)
            stop_flag.set()
            print("QM stopped")

    @staticmethod
    def _monitor_socket(client_connection: socket.socket, send_access:threading.Semaphore, stop_flag:threading.Event, client:Identity, server:IdentityComponent):
        print("Socket monitor started")
        client_connection.setblocking(True)
        client_connection.settimeout(1.0)
        try:
            while True:
                if stop_flag.is_set():
                    break
                
                try:
                    data = frame.read(client_connection, server.server_state["private_key"])
                except TimeoutError as e:
                    # This is expected if the client isn't sending any messages.
                    print(f"Socket timed out: {e}")
                    continue
                except OSError as e:
                    print(f"Failed to read data from socket: {e}")
                    break
                
                # Handle the case case where the socket has a timeout and may return None,
                # or where OS let us read 0 bytes because it turns off blocking when timeout is set:
                if data in (None, b''):
                    continue
                
                print(f"Received data via socket: {data}")

                # TODO: handle the message, for now we just add it to the server_queue
                server_queue.put(data)
        finally:
            print("SM stopping...")
            client_connection.close()
            stop_flag.set()
            print("SM stopped")