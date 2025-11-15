import socket
import uuid

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

import frame

client_private_key_b = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAAKCAQEAyeSYjAhDTqkpFsSEaEIhrQzzlJwwE/uaHLbINxBQgWZ6Enxb\nrQg2jXZTUT7fIa8ImTNg7R/GNxE4Umx6R3GaXpkhoxGhurAOlBUxuQpnPFvApNE5\njnyUKtZIO2uv2ToqA1hvJYHTcl1gAUNuEPWWGe0fcNKIyKFtuU5LShIpvRW1uH5h\n4rWqjryVYImF7i9tmvalMYarBYDRq/SoHjz463o56dTqcIJdkYgty7aEw+rmx+Tn\n6tW/axRw2RH0E3Zb7pAwehJ/HlL/MEfqRiUpjVMd+kKX6TJhqCAf4QJU+P8/oehD\nXP89e6C+6AJpRl4DwPn6249PBi8iO5ZavrefkQIDAQABAoIBABT21w1RbVXNdH4P\n/XTLCy6qRd/UYRyuF2hsZXlsSQPK1Zm2Tpm23N1PIGMzHV3kzEaGQoYU8tL0h43t\nhDwHdKFmksrZUZsuXXEsizt89E/c8jHbJPgiAQu6sQj0i2/J3aN3yyDQrJl3TzkK\nXLNHoSTDjex7/CajNp7TnbdNEAb5et6rYLUgxW3vsx2c+jEnUgP9po1jO9Xb5KUe\nOeAsoYv0P2PMcihGCRjLKyb4NmHpJGsrqJvrHQNpb4ed9am19p5VlbKn4ENKcLJk\nEBjNrLlsz+SlQJH7113LPnMEPTAFXLdrVNighUucP8tJ6gIWFIK2EsdR+psn8f6M\narrPjo0CgYEA/qiSL/kWlk2l2UvCHC1jxIBA7UkkGJxXZwVHWmExPn39E9VnT1af\n1Uk54FyqsrNOUkkJcPuUmzVz7JEusMoHRmuRwr5Nc5WcSwl3VAjzulMBujj6DWYY\nNc5CPL2/OQVPcXmToD0tYhZAOPgEQc48RUGVRYQlkt3jFMbhr9ayPD0CgYEAyvTd\nsD45oW1GlTXBzlHoFYH73W4nQjvhQXV8orY/AK9/ViKUJa14z9HMlCtUVbkq6gvD\nFkWu0b/1tHVGN0VY/Wf5+qaij9InvKZ2NcXNV1/Ni5zmueIU5qgyiZZxAUCMQbpy\nU57ESgtiODecEqXOYQPrIwCBdx+O8O6oQxJxgeUCgYAJxchOZP2z6OjrbNfXIvrI\nKK/VK1BiTWWhQ3eYhVBReJ5Eq5TaW5WoprW84XF/iBgCWmEtX8o1Jpj7RBsJl8ct\nsaUXVxw7yksEKinVJL7NsK/JSLR33SoirnamRBXZh1WkIilDJfXe5MG0Lfhj2hlA\nAyNKVqbmevNi8brpd5DBdQKBgGJNbh8SVJmisyBMVF3ZgD8CoXqkAvHqzPUGseKh\nwSxU1KlkwDrrpeuK47sUrZmDwYxxPAHKqJ1BjAHnF6ZnuW2r8gF8uppMoSCXxAPR\nld7vMUChM4PvRE5gQ3Iu4vdHS2f+pado7AwtLVqrXLYPh0GoQzjF4u9O4s5B2k/6\nW+4dAoGAWVzG1/TAahqxC4CH8nFe3Se3U50klaoVSOSTlNPgEcRancJVY/yXGO9+\nSa3NIJb/EivoEpNuUHPoojNklLRonVBzdvfpu2YSkpwgdGpfropwxFsnrGju635I\nFHq5xOYDtTxCUspH4WqN1BXrIHNgj6bP9tcsVbat16T34OAAteU=\n-----END RSA PRIVATE KEY-----\n'
client_private_key   = serialization.load_pem_private_key(client_private_key_b, password=None)

client_id = uuid.UUID(hex='05260583c3b242958e6fcbecf50829e6')

with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as sock:
    sock.connect(("127.0.0.1", 4000))
    challenge =  frame.read(sock)
    print("Received challenge: ", challenge)
    sig = client_private_key.sign(
        challenge,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    msg = client_id.bytes + sig
    print("Sending response: ", msg)
    frame.send(sock, msg)
    result = frame.read(sock)
    print(result)

