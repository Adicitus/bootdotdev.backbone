import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.exceptions import InvalidSignature


import frame


class ChallengeFailed(Exception) :
    def __init__(self):
        super().__init__("Authentication challenge failed")

# TODO: Hard-coded key data, should be moved to dynamic storage:
server_private_key_b = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAvIDEAz0tOPbvVH6519PxDcllVEznZwZbxbY/p8k+y8pSFhO+\nL1TZrwmffS0byTvpdxzJAlIaPZvMUod8luxSd0TGkut6J8REAj6/9ghZdM6CyBx6\nalnViw9w8xr4n95EPJsyeaFPQh+3BoNvW8Ldth7Z5LDSvhc/s+NO7jfwUCHDtsFn\njF3osjnXh6Eg2856WeLzkhpB6RHBOLCINpCnJ2wXA4MZpa/UbzDTycDohhIHLhTl\n99bfHO5A3YjH+HYzxXBg9PezvQwm4GeSyJ/vxCwVaz4v0SEURr6kysyHG0BqwpGc\nPHlaLmd3gMSzGwGCvzAlPic/WXCftCsDkFa/xwIDAQABAoIBAB5EQ0oig6/ZVQfz\n9G1so5BV+CtR0SKa2UJvfFy5n0JugRaiuI9LUvaGwjEsUdanrtldaa2x4XJnS9Er\n3aaIBHJlEcibqaNX9p7bqiExfwJBJFZIMvmqOfOYQ50ChXgkjT/5SrX6ih+GYxys\ndEVqDlpZ2Bz0V/+F+8hWT6FH9xHjyzIuq1sn8lz6VOS7WqzUvHT0XSu4ZYe2MyC0\ngJcn0deImTmVei51fuASc1RPxn+FVSdmUEAEm7cj4ItE2qbxGUZW/sipfA8PY9zC\n8GZWUkHY5IM3OihNGZ1kP8W1qhQzkrHeIDBUkX/eor+QuR+qzoTaM3IbZOeJUFkw\nMA7c2nECgYEA7x1so+JUO9JoO3G/26GOZVNstQDk8gLhzSNQNKeeK9I9l0zpVKgm\nAE1qE42cTS2mQxsjMcVyznHmF3LszI28peuyUJLHAy27E7wPyF5ixtKTIIu2eVlT\nTmutHkaMWR2kHRmXtNdtXLFLFfumuEAS81n5b9Jj9pSUlOdk4NcqTPECgYEAydBo\ntl5+8rvvKc6Vq1Ha0E1OM5Gi64sX7OBpM/f4MeLI1Gk3YWKB9V/j3rQYDND9pyV3\neeQCZPyz9DD0TY2oaOO/MkCiogGq+hantmcK4TI7xG3og1qj70poubEQg5R7Nzb+\n23mcJWiTH47FoMRdgPDNfaAMNhtkpaCqlQojuDcCgYEA4EAxPjWqF/yJoo5Yh8up\nNyAZSFvRW6MWT4Q52VgGAEUJXFdWUP3tvcTcof/iQYN5dWADDs+Fj1XEm+M9b83R\nya4VqnktSa7ez3BFQP48Fwkv0IsXFBGRDm/viQBS6dThsCTrYT/UoeTobXJ4dj4p\nR67vP08KTxwjiM7GjhNc6ZECgYBYq8xGTLCkgDRt/wm902I74at5dwTJTzz85AD1\nR39yk70/rtcZX8nQAQjC4ggrIWxBk3GySZ9PtcRvh07gAFy9cUuhjcqnOepgpbGc\nsBuUpJikDtJ5XErpKZ1n8UdbONMGiJBj6EPWH+N8myN0JrMaozL2fmq/HzwSlcw9\nXc4h8wKBgCtZD8kjipakadSbhosDOTmmnltI7ArMXuPjU/xn30TUJyp6YmHWKSQ5\nRODxzRS0DQhPijNcZmplrB1u4fYo+SapCHiqSSFzRdl3GTLDD9FniFE0nUWw/KUj\nVIdUc/9r1N2yNisZWMMM5uObKNIrFT9YThO8vRf2MRuwJbBp9RWj\n-----END RSA PRIVATE KEY-----\n'
server_public_key_b = b'-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvIDEAz0tOPbvVH6519Px\nDcllVEznZwZbxbY/p8k+y8pSFhO+L1TZrwmffS0byTvpdxzJAlIaPZvMUod8luxS\nd0TGkut6J8REAj6/9ghZdM6CyBx6alnViw9w8xr4n95EPJsyeaFPQh+3BoNvW8Ld\nth7Z5LDSvhc/s+NO7jfwUCHDtsFnjF3osjnXh6Eg2856WeLzkhpB6RHBOLCINpCn\nJ2wXA4MZpa/UbzDTycDohhIHLhTl99bfHO5A3YjH+HYzxXBg9PezvQwm4GeSyJ/v\nxCwVaz4v0SEURr6kysyHG0BqwpGcPHlaLmd3gMSzGwGCvzAlPic/WXCftCsDkFa/\nxwIDAQAB\n-----END PUBLIC KEY-----\n'

server_private_key   = serialization.load_pem_private_key(
    server_private_key_b,
    password=None
)
server_public_key   = serialization.load_pem_public_key(server_public_key_b)

# TODO: Client keys should be stored under associated client_id
client_public_key_b = b'-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyeSYjAhDTqkpFsSEaEIh\nrQzzlJwwE/uaHLbINxBQgWZ6EnxbrQg2jXZTUT7fIa8ImTNg7R/GNxE4Umx6R3Ga\nXpkhoxGhurAOlBUxuQpnPFvApNE5jnyUKtZIO2uv2ToqA1hvJYHTcl1gAUNuEPWW\nGe0fcNKIyKFtuU5LShIpvRW1uH5h4rWqjryVYImF7i9tmvalMYarBYDRq/SoHjz4\n63o56dTqcIJdkYgty7aEw+rmx+Tn6tW/axRw2RH0E3Zb7pAwehJ/HlL/MEfqRiUp\njVMd+kKX6TJhqCAf4QJU+P8/oehDXP89e6C+6AJpRl4DwPn6249PBi8iO5Zavref\nkQIDAQAB\n-----END PUBLIC KEY-----\n'
client_public_key   = serialization.load_pem_public_key(client_public_key_b)

def challenge(clientsock):
    # This should be replaced with a signature validation.
    challenge_data = os.urandom(256)

    frame.send(clientsock, challenge_data)
    response = frame.read(clientsock)
    
    try:
        client_public_key.verify(
            response,
            challenge_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        msg = b'Connection authenticated!'
        frame.send(clientsock, msg)
    except InvalidSignature:
        raise ChallengeFailed()

def respond(socket):
    challenge_data = frame.read(socket)
