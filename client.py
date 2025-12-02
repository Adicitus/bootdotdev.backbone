import signal
import socket
import os
import time
import uuid
from threading import Thread, Event, Semaphore
from queue import Queue

from cryptography.hazmat.primitives.asymmetric import rsa

import frame
import key
from message import BackboneMessageC2S, BackboneMessageFormat, BackboneC2SType, BackboneMessage


class BackboneClient:
    def __init__(self, client_id:uuid.UUID, key:rsa.RSAPrivateKey) -> None:
        self.id  = client_id
        self.key = key
    
    def start(self, address:str, port:int=4000):
        self.stop_flag = Event()
        self._messages_in = Queue()
        self._messages_out = Queue()
        self._thread   = Thread(
            target=BackboneClient._run,
            kwargs={
                "address": address,
                "port": port,
                "client_id": self.id,
                "private_key": self.key,
                "messages_in": self._messages_in,
                "messages_out": self._messages_out,
                "stop_flag": self.stop_flag
            })
        self.stop_flag.clear()
        self._thread.start()
    
    def stop(self) -> bool:
        if not self.is_running():
            return False
        
        self.stop_flag.set()
        self._thread.join(10)

        self.stop_flag = None
        self._messages_in = None
        self._messages_out = None
    
    def is_running(self) -> bool:
        return self.stop_flag != None and not self.stop_flag.is_set()
    
    @staticmethod
    def _run(address:str, port:int, client_id:uuid.UUID, private_key:rsa.RSAPrivateKey, messages_in:Queue, messages_out:Queue, stop_flag:Event):
        
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:
            sock.connect((address, port))

            # Receive server challenge:
            challenge =  frame.read(sock)
            key_length = int.from_bytes(challenge[0:2])
            server_public_key_b = challenge[2:2+key_length]
            server_public_key = key.deserialize(server_public_key_b)

            # Prepare challenge response:
            challenge_data = challenge[2+key_length:]
            signature = key.sign(private_key, challenge_data)
            msg = client_id.bytes + signature

            # Send response:
            frame.send(sock, msg, server_public_key)
            result = frame.read(sock, private_key)

            try:
                msg = BackboneMessage.from_bytes(result)
            except Exception as e:
                print(f"{client_id}-master: Invalid response received from server, assuming authentication failed.")
                stop_flag.set()

            if msg.format != BackboneMessageFormat.C2S or msg.type != BackboneC2SType.CONFIG:
                print(f"{client_id}-master: Invalid response received from server, assuming authentication failed.")
                stop_flag.set()
                return
            
            # TODO: Run monitors

            socket_access = Semaphore()

            send_thread = Thread(
                target=BackboneClient._sender,
                kwargs={
                    "client_id": client_id,
                    "server_key": server_public_key,
                    "messages_out": messages_out,
                    "connection": sock,
                    "socket_access": socket_access,
                    "stop_flag": stop_flag
                }
            )
            receive_thread= Thread(
                target=BackboneClient._receiver,
                kwargs={
                    "client_id": client_id,
                    "private_key": private_key,
                    "messages_in": messages_in,
                    "connection": sock,
                    "socket_access": socket_access,
                    "stop_flag": stop_flag
                }
            )

            print(f"{client_id}-master: Starting send thread")
            send_thread.start()
            print(f"{client_id}-master: Starting receive thread")
            receive_thread.start()
            
            stop_flag.wait()

            print(f"{client_id}-master: Stop flag set, waiting for socket threads to finish...")
            send_thread.join()
            receive_thread.join()
            print(f"{client_id}-master: Socket threads stopped, stopping...")




    @staticmethod
    def _sender(client_id:uuid.UUID, server_key:rsa.RSAPublicKey, messages_out:Queue, connection:socket.socket, socket_access:Semaphore, stop_flag:Event):
        print(f"{client_id}-send: Starting...")
        frame.send(connection, BackboneMessageC2S(BackboneC2SType.STOP).to_bytes(), server_key)
        stop_flag.set()
        # TODO: Implement sending messages from the queue.
    
    @staticmethod
    def _receiver(client_id:uuid.UUID, private_key:rsa.RSAPrivateKey, messages_in:Queue, connection:socket.socket, socket_access:Semaphore, stop_flag:Event):
        print(f"{client_id}-receive: Starting...")
        stop_flag.set()
        # TODO: Implement receiving messages from the socket.


if __name__ == "__main__":
    client_id = uuid.UUID(hex='05260583c3b242958e6fcbecf50829e6')

    state_dir = os.path.join(os.path.dirname(__file__), ".client")
    key_path  = os.path.join(state_dir, f"{client_id.hex}")
    pub_key_path = f"{key_path}.pub"

    client_private_key = None

    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            client_private_key = key.deserialize(f.read())
    else:
        if not os.path.exists(state_dir):
            os.makedirs(state_dir)
        
        client_private_key = key.generate()
        with open(key_path, 'wb') as f:
            f.write(key.serialize(client_private_key))
        
        with open(pub_key_path, 'wb') as f:
            f.write(key.serialize(client_private_key.public_key()))
    
    client = BackboneClient(client_id, client_private_key)
    client.start("127.0.0.1", 4000)
    signal.signal(signal.SIGINT, lambda signum, signal: client.stop())
    while client.is_running():
        time.sleep(0.1)