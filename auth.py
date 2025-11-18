import uuid
import os

from cryptography.hazmat.primitives.asymmetric import rsa


import frame
import key

class ChallengeFailed(Exception) :
    def __init__(self, text):
        super().__init__(f"Authentication challenge failed: {text}")

class AuthComponent:

    def __init__(self, state_dir=None):
        if state_dir == None:
            state_dir = os.path.dirname(__file__)
        self.clients_dir = os.path.join(state_dir, ".clients")
        self.server_dir  = os.path.join(state_dir, ".server")
        self.key_path    = os.path.join(self.server_dir, "key.pem")

        self.server_state = {
            "pivate_key": None,
            "public_key": None,
            "public_key_bytes": None
        }

        self.initialize()

    def challenge(self, clientsock):
        challenge_data = os.urandom(256)

        msg = len(self.server_state["public_key_bytes"]).to_bytes(2) + self.server_state["public_key_bytes"] + challenge_data

        frame.send(clientsock, msg)
        response = frame.read(clientsock, self.server_state["private_key"])

        client_id_b = response[0:16]
        client_id = uuid.UUID(bytes=client_id_b)
        
        client_key = self.get_client_key(client_id)
        if client_key == None:
            raise ChallengeFailed(f"No such client: {client_id.hex}")
        
        print(f"Response data ({len(response[16:])}): {response[16:]}")

        if not key.verify(client_key, challenge_data, response[16:]):
            raise ChallengeFailed("Invalid signature returned!")

        msg = b'Connection authenticated!'
        frame.send(clientsock, msg, client_key)

        return client_id, client_key

    def get_client_key(self, client_id: uuid.UUID) -> rsa.RSAPublicKey:
        client_key_path = os.path.join(self.clients_dir, client_id.hex)
        if not os.path.exists(client_key_path):
            return None
        
        with open(client_key_path, 'rb') as f:
            return key.deserialize(f.read())

    def add_client_key(self, client_id: uuid.UUID, client_key: rsa.RSAPublicKey) -> bool:
        client_key_path = os.path.join(self.clients_dir, client_id.hex)
        if os.path.exists(client_key_path):
            return False
        
        with open(client_key_path, 'wb') as f:
            f.write(key.serialize(client_key))
        
        return True

    def set_client_key(self, client_id: uuid.UUID, client_key: rsa.RSAPublicKey) -> bool:
        client_key_path = os.path.join(self.clients_dir, client_id.hex)
        
        with open(client_key_path, 'wb') as f:
            f.write(key.serialize(client_key))
        
        return True

    def initialize(self):
        if not os.path.exists(self.clients_dir):
            os.makedirs(self.clients_dir)

        if not os.path.exists(self.server_dir):
            os.makedirs(self.server_dir)
        
        if not os.path.exists(self.key_path):
            self.server_state["private_key"] = key.generate()
            with open(self.key_path, 'wb') as f:
                f.write(
                    key.serialize(self.server_state["private_key"])
                )
        else:
            with open(self.key_path, 'rb') as f:
                self.server_state["private_key"] = key.deserialize(f.read())
        
        self.server_state["public_key"] = self.server_state["private_key"].public_key()
        self.server_state["public_key_bytes"] = key.serialize(self.server_state["public_key"])

