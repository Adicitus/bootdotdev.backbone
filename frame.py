from cryptography.hazmat.primitives.asymmetric import rsa

import key

def read(conn, private_key:rsa.RSAPrivateKey=None):
    l_b = conn.recv(2)
    l   = int.from_bytes(l_b)

    if l == 0:
        return None
    
    print(f"Receiving {l} bytes")

    data = conn.recv(l)

    if (private_key == None):
        return data
    
    # TODO: Add a function to decrypt directly from socket.
    return key.decrypt(private_key, data)
    

def send(conn, msg, public_key:rsa.RSAPublicKey=None):
    
    if public_key == None:
        # Send clear text:
        l = len(msg)
        print(f"Sending {l} bytes")

        l_b = l.to_bytes(2)
        conn.send(l_b)
        conn.sendall(msg)
        return
        
    # Send encrypted:
    enc_data = key.encrypt(public_key, msg)
    l = len(enc_data)
    print(f"Sending {l} bytes")
    
    l_b = l.to_bytes(2)
    conn.send(l_b)
    conn.sendall(enc_data)
    
