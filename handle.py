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

def _monitor_queue(client_connection: socket.socket, send_access:threading.Semaphore, stop_flag:threading.Event, client:Identity, server:IdentityComponent):
    print("Queue monitor started")
    try:
        client_queue = _register_client(client.id)
        while True:
            if stop_flag.is_set():
                break
            print("QM loop")
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

def _monitor_socket(client_connection: socket.socket, send_access:threading.Semaphore, stop_flag:threading.Event, client:Identity, server:IdentityComponent):
    print("Socket monitor started")
    try:
        while True:
            if stop_flag.is_set():
                break
            print("SM loop")

            try:
                data = frame.read(client_connection, server.server_state["private_key"])
            except TimeoutError:
                continue
            
            # Handle the case case where the socket has a timeout and may return None:
            if data == None:
                continue
            
            print(f"Received data via socket: {data}")

            # TODO: handle the message, for now we just add it to the server_queue
            server_queue.put(data)
    finally:
        print("SM stopping...")
        client_connection.close()
        stop_flag.set()
        print("SM stopped")
        

class ClientHandler:
    def __init__(self, client_connection: socket.socket, client:Identity, server:IdentityComponent):
        client_connection.settimeout(1)
        self.connection = client_connection
        self.client = client
        self.server = server

        socket_semaphore = threading.Semaphore()
        self.stop_flag = threading.Event()

        self.queue_monitor  = threading.Thread(target=_monitor_queue, args=(client_connection, socket_semaphore, self.stop_flag, client, server), daemon=False)
        self.socket_monitor = threading.Thread(target=_monitor_socket, args=(client_connection, socket_semaphore, self.stop_flag, client, server), daemon=False)
    
    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.stop_flag.clear()
        self.thread.start()
    
    def stop(self, block=False):
        self.stop_flag.set()
        if block and self.thread:
            self.thread.join()
    
    def _run(self):
        print("Via stdout: handler started")
        get_server_queue().put("Via Queue: handler started")

        self.queue_monitor.start()
        self.socket_monitor.start()
        self.stop_flag.wait()

        print("Handler stopping...")

        self.queue_monitor.join()
        self.socket_monitor.join()

        get_server_queue().put("Via Queue: handler stopped")
        print("Handler stopped")
        self.thread = None