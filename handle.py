# handle.py
# Client handler and associated functionality
import threading
import socket

from uuid import UUID
from queue import Empty, Queue

import frame
import message

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
        self.id = id(client_connection)
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
        print(f"{self.id}: handler started")

        socket_semaphore = threading.Semaphore()
        arguments = (self.connection, socket_semaphore, self.stop_flag, self.client, self.server)
        self.queue_monitor  = threading.Thread(target=ClientHandler._monitor_queue, args=arguments, daemon=False)
        self.socket_monitor = threading.Thread(target=ClientHandler._monitor_socket, args=arguments, daemon=False)

        self.queue_monitor.start()
        self.socket_monitor.start()
        self.stop_flag.wait()

        print(f"{self.id}: Handler stopping...")

        self.queue_monitor.join()
        self.socket_monitor.join()

        print(f"{self.id}: Handler stopped")
        get_server_queue().put(message.BackboneMessageS2S(message.BackboneS2SType.DONE))
        
        self.queue_monitor = None
        self.socket_monitor = None
        self.thread = None

    @staticmethod
    def _monitor_queue(client_connection: socket.socket, send_access:threading.Semaphore, stop_flag:threading.Event, client:Identity, server:IdentityComponent):
        handler_id = id(client_connection)
        print(f"{handler_id}: Queue monitor started")
        try:
            client_queue = _register_client(client.id)
            while not stop_flag.is_set():
                
                try:
                    msg = client_queue.get(timeout=1)
                except Empty:
                    continue
                
                match msg.format:
                    case message.BackboneMessageFormat.C2C:
                        if msg.recipient != client.id:
                            print(f"{handler_id}: Invalid routing: handler for {client.id} received message for {msg.recipient}. Dropping message!")
                            continue
                        send_access.acquire()
                        frame.send(client_connection, msg.to_bytes(), client.key)
                        send_access.release()
                    case message.BackboneMessageFormat.S2S:
                        match msg.type:
                            case message.BackboneS2SType.STOP:
                                print(f"{handler_id}: Received {msg.type.name} message on queue, stopping...")
                                break
                    case _:
                        print(f"{handler_id}: Recevied a {msg.format} message on queue, dropping it (only C2C or S2S permitted)")

        finally:
            print(f"{handler_id}: QM stopping...")
            _deregister_client(client.id)
            stop_flag.set()
            print(f"{handler_id}: QM stopped")

    @staticmethod
    def _monitor_socket(client_connection: socket.socket, send_access:threading.Semaphore, stop_flag:threading.Event, client:Identity, server:IdentityComponent):
        handler_id = id(client_connection)
        print(f"{handler_id}: Socket monitor started")
        client_connection.setblocking(True)
        client_connection.settimeout(1.0)
        try:
            while not stop_flag.is_set():
                
                try:
                    data = frame.read(client_connection, server.server_state["private_key"])
                except TimeoutError as e:
                    # This is expected if the client isn't sending any messages.
                    print(f"{handler_id}: Socket timed out: {e}")
                    continue
                except OSError as e:
                    print(f"{handler_id}: Failed to read data from socket: {e}")
                    break
                
                # Handle the case case where the socket has a timeout and may return None,
                # or where OS let us read 0 bytes because it turns off blocking when timeout is set:
                if data in (None, b''):
                    continue
                
                print(f"{handler_id}: Received data via socket: {data}")

                msg = message.BackboneMessage.from_bytes(data)

                if msg == None:
                    print(f"{handler_id}: Failed to parse data as a message: {data}")
                    continue
                
                match msg.format:
                    case message.BackboneMessageFormat.C2C:
                        recipient_queue = get_client_queue(msg.recipient)
                        recipient_queue.put(msg)
                        continue

                    case message.BackboneMessageFormat.C2S:
                        match msg.type:
                            case message.BackboneC2SType.HEARTBEAT:
                                # TODO: implement activity tracking.
                                pass
                            case message.BackboneC2SType.STOP:
                                print(f"{handler_id}: Received {msg.type.name} message from client, stopping...")
                                break
                    case _:
                        print(f"{handler_id}: Recevied a {msg.format} message on socket, dropping it (only C2C or C2S permitted)")

        finally:
            print(f"{handler_id}: SM stopping...")
            client_connection.close()
            stop_flag.set()
            print(f"{handler_id}: SM stopped")