from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.exceptions import InvalidSignature


def generate() -> rsa.RSAPrivateKey:
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend
    )
    return key

def sign(key: rsa.RSAPrivateKey, data:bytes) -> bytes:
    return key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

def verify(key: rsa.RSAPublicKey, data: bytes, signature: bytes) -> bool:
    try:
        key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    
def serialize(key) -> bytes:
    if isinstance(key, rsa.RSAPrivateKey):
        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
    elif isinstance(key, rsa.RSAPublicKey):
        return key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.PKCS1
        )

def deserialize(pem: bytes):
    if b'PUBLIC KEY' in pem:
        return serialization.load_pem_public_key(pem, backend=default_backend)
    if b'PRIVATE KEY' in pem:
        return serialization.load_pem_private_key(pem, password=None, backend=default_backend)

def encrypt(key: rsa.RSAPublicKey, data: bytes) -> bytes:
    enc_data = b''
    for chunk in encrypt_iter(key, data):
        enc_data += chunk
    return enc_data

def decrypt(key: rsa.RSAPrivateKey, enc_data: bytes) -> bytes:
    data = b''
    for chunk in decrypt_iter(key, enc_data):
        data += chunk
    return data


def encrypt_iter(key: rsa.RSAPublicKey, data: bytes):
    i = 0
    inc = 190
    max_i = (len(data) // inc) * inc
    while i < max_i:
        yield key.encrypt(
            data[i:i+190],
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        i += inc
    
    if len(data) % inc != 0:
        yield key.encrypt(
                data[max_i:],
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

def decrypt_iter(key: rsa.RSAPrivateKey, data: bytes):
    i = 0
    inc = 256
    max_i = (len(data) // inc) * inc
    
    while i < max_i:
        yield key.decrypt(
                data[i:i+inc],
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
            )
        )

        i += inc

    if len(data) % inc != 0:
        yield key.decrypt(
            data[max_i:],
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )