from tempfile import TemporaryDirectory
from threading import Thread, Event
import time
import socket
import unittest
import random
from uuid import uuid4

import key
import frame
from identity import ChallengeFailed, IdentityComponent
from client import BackboneClient
from message import BackboneMessageC2C as MsgC2C, BackboneMessageC2S as MsgC2S, BackboneC2SType as MsgC2SType, BackboneMessageFormat as MsgFormat, BackboneMessage

class TestBackboneClient(unittest.TestCase):
    def test_creation(self):
        client_key = key.generate()
        client_id  = uuid4()

        BackboneClient(client_id, client_key)

    def test_start_success(self):
        
        client_key = key.generate()
        client_id  = uuid4()
        client     = BackboneClient(client_id, client_key)
        port       = 4000 # random.randint(40000, 50000)

        client_settings = { 
            "heartbeat_interval": 5,
            "heartbeat_timeout": 10
        }

        with TemporaryDirectory() as tmp_path:
            auth = IdentityComponent(state_dir=tmp_path)
            auth.add_client_key(client_id, client_key.public_key())

            flags = {
                "challenge_failed": Event(),
                "stop": Event()
            }
            
            def stub_server(port:int, auth:IdentityComponent, client_settings:dict, flags:dict):
                print("Startingstub server...")
                with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as server_socket:
                    server_socket.bind(("0.0.0.0", port))
                    server_socket.listen()
                    print(f"stub server listening on port {port}")
                    client_socket, address = server_socket.accept()

                    try:
                        client_socket, client = auth.challenge(clientsock=client_socket, client_settings=client_settings)
                    except ChallengeFailed:
                        flags["challenge_failed"].set()
                    
                    flags["stop"].wait()
                    
                    frame.send(client_socket, MsgC2S(MsgC2SType.STOP).to_bytes(), client.key)
                    time.sleep(0.1)
                    server_socket.close()
                    time.sleep(0.1)
            
            server_thread = Thread(target=stub_server, kwargs={
                "port": port,
                "auth": auth,
                "client_settings": client_settings,
                "flags": flags
            })

            server_thread.start()
            client.start(address="127.0.0.1", port=port)
            time.sleep(0.2)
            self.assertTrue(client.is_running())
            self.assertFalse(flags["challenge_failed"].is_set())
            self.assertDictEqual(client_settings, client.settings)
            flags["stop"].set()
            time.sleep(0.2)
            self.assertFalse(client.is_running())


if __name__ == "__main__":
    unittest.main()
