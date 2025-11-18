import socket
import os
import uuid

import frame
import key

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
    

with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:

    sock.connect(("127.0.0.1", 4000))
    challenge =  frame.read(sock)
    key_length = int.from_bytes(challenge[0:2])
    server_public_key_b = challenge[2:2+key_length]
    server_public_key = key.deserialize(server_public_key_b)
    challenge_data = challenge[2+key_length:]
    print("Received challenge: ", challenge_data)
    sig = key.sign(client_private_key, challenge_data)
    msg = client_id.bytes + sig
    print(f"Sending response {len(msg)}: ", msg)
    frame.send(sock, msg, server_public_key)
    result = frame.read(sock, client_private_key)
    print(result)

