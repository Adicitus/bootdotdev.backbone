import uuid
import os

from cryptography.hazmat.primitives.asymmetric import rsa


import frame
import key


clients_dir = os.path.join(os.path.dirname(__file__), ".clients")
server_dir  = os.path.join(os.path.dirname(__file__), ".server")
key_path    = os.path.join(server_dir, "key.pem")

class ChallengeFailed(Exception) :
    def __init__(self, text):
        super().__init__("Authentication challenge failed: {text}")

server_private_key = None
server_public_key  = None


def challenge(clientsock):
    challenge_data = os.urandom(256)

    frame.send(clientsock, challenge_data)
    response = frame.read(clientsock)

    client_id_b = response[0:16]
    client_id = uuid.UUID(bytes=client_id_b)
    
    client_key = get_client_key(client_id)
    if client_key == None:
        raise ChallengeFailed(f"No such client: {client_id.hex}")
    
    if not key.verify(client_key, challenge_data, response[16:]):
        raise ChallengeFailed("Invalid signature returned!")

    msg = b'Connection authenticated!'
    frame.send(clientsock, msg)

    return

def get_client_key(client_id: uuid.UUID) -> rsa.RSAPublicKey:
    client_key_path = os.path.join(clients_dir, client_id.hex)
    if not os.path.exists(client_key_path):
        return None
    
    with open(client_key_path, 'rb') as f:
        return key.deserialize(f.read())

def add_client_key(client_id: uuid.UUID, client_key: rsa.RSAPublicKey) -> bool:
    client_key_path = os.path.join(clients_dir, client_id.hex)
    if os.path.exists(client_key_path):
        return False
    
    with open(client_key_path, 'wb') as f:
        f.write(key.serialize(client_key))
    
    return True

def set_client_key(client_id: uuid.UUID, client_key: rsa.RSAPublicKey) -> bool:
    client_key_path = os.path.join(clients_dir, client_id.hex)
    
    with open(client_key_path, 'wb') as f:
        f.write(key.serialize(client_key))
    
    return True

def initialize():
    if not os.path.exists(clients_dir):
        os.makedirs(clients_dir)

    if not os.path.exists(server_dir):
        os.makedirs(server_dir)
    
    if not os.path.exists(key_path):
        server_private_key = key.generate()
        with open(key_path, 'wb') as f:
            f.write(
                key.serialize(server_private_key)
            )
    else:
        with open(key_path, 'rb') as f:
            server_private_key = key.deserialize(f.read())

initialize()