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
from server import BackboneServer
from message import BackboneMessageC2C as MsgC2C, BackboneMessageC2S as MsgC2S, BackboneC2SType as MsgC2SType, BackboneMessageFormat as MsgFormat, BackboneMessage

class TestBackboneClient(unittest.TestCase):
    def test_creation(self):
        print()
        client_key = key.generate()
        client_id  = uuid4()

        BackboneClient(client_id, client_key)

    def test_start_success(self):
        print()
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
                print("Starting stub server...")
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
                    client_socket.close()
                    time.sleep(0.1)
                    server_socket.close()
                    time.sleep(0.1)
            
            server_thread = Thread(target=stub_server, kwargs={
                "port": port,
                "auth": auth,
                "client_settings": client_settings,
                "flags": flags
            })

            try:
                start_time = time.monotonic_ns()
                server_thread.start()
                client.start(address="127.0.0.1", port=port)
                time.sleep(0.2)
                self.assertTrue(client.is_running())
                self.assertFalse(flags["challenge_failed"].is_set())
                flags["stop"].set()
                time.sleep(0.2)
                self.assertFalse(client.is_running())
            finally:
                print(f"Test finished in {(time.monotonic_ns() - start_time)/10**9}s")
                flags["stop"]
                client.stop()

    
    def test_c2c(self):
        print()

        client_id1  = uuid4()
        client_key1 = key.generate()
        client_id2  = uuid4()
        client_key2 = key.generate()
        client1 = BackboneClient(client_id1, client_key1)
        client2 = BackboneClient(client_id2, client_key2)
        port    = random.randint(40000, 50000)

        with TemporaryDirectory() as tmp_path:
            auth = IdentityComponent(state_dir=tmp_path)
            auth.add_client_key(client_id1, client_key1.public_key())
            auth.add_client_key(client_id2, client_key2.public_key())

            settings = {
                "port": port
            }
            
            try:
                start_time = time.monotonic_ns()
                backbone_server = BackboneServer(settings=settings, identities=auth)

                backbone_server.start()
                client1.start("127.0.0.1", port).wait(3)
                client2.start("127.0.0.1", port).wait(3)

                msg1 = MsgC2C(client_id1, b'loopback')
                e1 = client1.send(msg1)
                e1.wait()
                self.assertEqual(client1.read(block=True), msg1)

                msg2 = MsgC2C(client_id2, b'client1->client2')
                e2 = client1.send(msg2)
                e2.wait()
                self.assertEqual(client2.read(block=True), msg2)

                msg3 = MsgC2C(client_id1, b'client2->client1')
                e3 = client2.send(msg3)
                e3.wait()
                self.assertEqual(client1.read(block=True), msg3)
            except Exception as e:
                print(f"Exception occurred: {e}")
                raise e
            finally:
                print(f"Test finished in {(time.monotonic_ns() - start_time)/10**9}s")
                backbone_server.stop(block=True)
                client1.stop()
                client2.stop()

            




if __name__ == "__main__":
    unittest.main(verbosity=2)
