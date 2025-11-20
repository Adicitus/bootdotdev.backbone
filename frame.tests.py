from os import urandom
import socket
import unittest

import frame, key

class TestFrameFunctions(unittest.TestCase):

    def test_unencrypted(self):
        sock1, sock2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)
        l = 256
        data = urandom(l)
        frame.send(sock1, data)
        self.assertEqual(data, frame.read(sock2), "Data receiveed across the socket connection should match the data sent")
        sock1.close()
        sock2.close()
    
    def test_encrypted(self):
        private_key1 = key.generate()
        private_key2 = key.generate()
        public_key  = private_key1.public_key()

        sock1, sock2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)
        l = 256
        data = urandom(l)
        frame.send(sock1, data, public_key)
        self.assertEqual(data, frame.read(sock2, private_key1), "Data receiveed across the socket connection should match the data sent")
        frame.send(sock1, data, public_key)
        with self.assertRaises(
            ValueError,
            msg="Should raise a ValueError if a foreign private key is used to decrypt the data."
        ):
            frame.read(sock2, private_key2)
        sock1.close()
        sock2.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)