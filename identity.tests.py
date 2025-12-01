import json
import unittest
from uuid import UUID, uuid4
import os
import tempfile
import socket
import threading
import time

from cryptography.hazmat.primitives.asymmetric import rsa

import identity, key, frame, message

default_settings = {
    "heartbeat_timeout": 600,
    "heartbeat_intervall": 300
}

def get_success_msg():
    return message.BackboneMessageC2S(message.BackboneC2SType.CONFIG, payload=json.dumps(default_settings).encode(encoding='utf-8')).to_bytes()

def stub_client(s:socket.socket, client_id:UUID, client_key:rsa.RSAPrivateKey, result:dict):
    data = frame.read(s)
    kl = int.from_bytes(data[0:2])
    server_public_key = key.deserialize(data[2:2+kl])
    signature = key.sign(client_key, data[2+kl:])
    frame.send(s, client_id.bytes + signature, server_public_key)
    data = frame.read(s, client_key)
    result["data"] = data

class TestIdentity(unittest.TestCase):

    def test_identity_creation(self):
        client_key = key.generate()
        identity.Identity(uuid4(), client_key.public_key())

class TestIdentityComponent(unittest.TestCase):

    def test_creation(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            self.assertIsInstance(identities, identity.IdentityComponent)

            self.assertTrue(os.path.isdir(store_path))

    def test_identity_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key1 = key.generate()
            client_key2 = key.generate()

            self.assertEqual(identities.get_client_key(client_id), None,                     "get_client_key should return None before adding key for given client_id.")
            self.assertTrue(identities.add_client_key(client_id, client_key1.public_key()),  "add_client_key should return True for non-existing client_id.")
            self.assertEqual(identities.get_client_key(client_id), client_key1.public_key(), "get_client_key should return the public key associated with the client_id when the client_id has been added.")
            self.assertFalse(identities.add_client_key(client_id, client_key1.public_key()), "add_client_key should return False for a client_id once it has been added.")
            self.assertTrue(identities.set_client_key(client_id, client_key2.public_key()),  "set_client_key should return True for existing client_id")
            self.assertEqual(identities.get_client_key(client_id), client_key2.public_key(), "After setting a new key using set_client_key, get_client_key should return the new key.")
            self.assertTrue(identities.remove_client_key(client_id),                         "remove_client_key should return True when removing an existing client key.")
            self.assertEqual(identities.get_client_key(client_id), None,                     "get_client_key should return None for a client_id that has been removed.")
            self.assertFalse(identities.remove_client_key(client_id),                        "remove_client_key should return False for non-existent client_id.")
            self.assertFalse(identities.set_client_key(client_id, client_key1.public_key()),  "set_client_key should return False for non-existing client_id.")

    def test_challenge_default_success(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key  = key.generate()

            identities.add_client_key(client_id, client_key.public_key())
            
            socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

            try:
                result = {}
                client_thread = threading.Thread(
                    target=stub_client,
                    kwargs={
                        "s": socket2,
                        "client_id": client_id,
                        "client_key": client_key,
                        "result": result
                    }
                )
                client_thread.start()

                client_socket, client = identities.challenge(socket1, client_settings=default_settings)

                time.sleep(0.1)

                self.assertEqual(client_socket, socket1,              "challenge method should return the socket used to complete the authentication.")
                self.assertEqual(client.id, client_id,                "The returned client Identity 'id' should match the client_id submitted by the client.")
                self.assertEqual(client.key, client_key.public_key(), "The returned client identity 'key' should match the key added for client_id.")
                self.assertEqual(result["data"], get_success_msg())
            finally:
                socket1.close()
                socket2.close()
    
    def test_challenge_default_failed(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key1  = key.generate()
            client_key2  = key.generate()

            identities.add_client_key(client_id, client_key1.public_key())
            
            socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

            try:
                result = {}
                client_thread = threading.Thread(
                    target=stub_client,
                    kwargs={
                        "s": socket2,
                        "client_id": client_id,
                        "client_key": client_key2,
                        "result": result
                    }
                )
                client_thread.start()

                with self.assertRaises(identity.ChallengeFailed):
                    identities.challenge(socket1)

            finally:
                socket1.close()
                socket2.close()
        
    def test_challenge_2048_success(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key  = key.generate()

            identities.add_client_key(client_id, client_key.public_key())
            
            socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

            try:
                result = {}
                client_thread = threading.Thread(
                    target=stub_client,
                    kwargs={
                        "s": socket2,
                        "client_id": client_id,
                        "client_key": client_key,
                        "result": result
                    }
                )
                client_thread.start()

                client_socket, client = identities.challenge(socket1, 2048, client_settings=default_settings)

                time.sleep(0.1)

                self.assertEqual(result["data"], get_success_msg())
                self.assertEqual(client_socket, socket1)
                self.assertEqual(client.id, client_id)
                self.assertEqual(client.key, client_key.public_key())
                
            finally:
                socket1.close()
                socket2.close()

    def test_challenge_2048_failed(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key1  = key.generate()
            client_key2  = key.generate()

            identities.add_client_key(client_id, client_key1.public_key())
            
            socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

            try:
                result={}
                client_thread = threading.Thread(
                    target=stub_client,
                    kwargs={
                        "s": socket2,
                        "client_id": client_id,
                        "client_key": client_key2,
                        "result": result
                    }
                )
                client_thread.start()

                with self.assertRaises(identity.ChallengeFailed):
                    identities.challenge(socket1, 2048)

            finally:
                socket1.close()
                socket2.close()
    
    def test_challenge_malformed_response_failure1(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key1  = key.generate()
            client_key2  = key.generate()

            identities.add_client_key(client_id, client_key1.public_key())
            
            socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

            try:
                def client_response(s:socket.socket, client_id:UUID, client_key:rsa.RSAPrivateKey):
                    data = frame.read(s)
                    kl = int.from_bytes(data[0:2])
                    server_public_key = key.deserialize(data[2:2+kl])
                    frame.send(s, b'hi', server_public_key)
                    data = frame.read(s, client_key)
                    self.assertEqual(data, None)

                client_thread = threading.Thread(
                    target=client_response,
                    kwargs={
                        "s": socket2,
                        "client_id": client_id,
                        "client_key": client_key2
                    }
                )
                client_thread.start()

                with self.assertRaises(identity.ChallengeFailed):
                    identities.challenge(socket1)

            finally:
                socket1.close()
                socket2.close()
    
    def test_challenge_malformed_response_failure2(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            store_path = os.path.join(tmp_path, '.store')

            identities = identity.IdentityComponent(state_dir=store_path)

            client_id   = uuid4()
            client_key1  = key.generate()
            client_key2  = key.generate()

            identities.add_client_key(client_id, client_key1.public_key())
            
            socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

            try:
                def client_response(s:socket.socket, client_id:UUID, client_key:rsa.RSAPrivateKey):
                    data = frame.read(s)
                    kl = int.from_bytes(data[0:2])
                    server_public_key = key.deserialize(data[2:2+kl])
                    frame.send(s, os.urandom(16), server_public_key)
                    data = frame.read(s, client_key)
                    self.assertEqual(data, None)

                client_thread = threading.Thread(
                    target=client_response,
                    kwargs={
                        "s": socket2,
                        "client_id": client_id,
                        "client_key": client_key2
                    }
                )
                client_thread.start()

                with self.assertRaises(identity.ChallengeFailed):
                    identities.challenge(socket1)

            finally:
                socket1.close()
                socket2.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)