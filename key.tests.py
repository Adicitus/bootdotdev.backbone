from os import urandom
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa

import key

class TestKeyFunctions(unittest.TestCase):
    def test_generation(self):
        private_key = key.generate()
        self.assertIsInstance(private_key, rsa.RSAPrivateKey, "Should generate a RSAPrivateKey.")
        public_key = private_key.public_key()
        self.assertIsInstance(public_key, rsa.RSAPublicKey, "Should be possible to generate a RSAPublicKey from the private key.")
    
    def test_serialization(self):
        private_key = key.generate()
        private_key_s = key.serialize(private_key)
        self.assertIsInstance(private_key_s, bytes, "RSAPrivatekey should serialize into 'bytes' type.")
        self.assertEqual(private_key.private_numbers(), key.deserialize(private_key_s).private_numbers(), "Deserialized key should use the same private numbers as unerialized key.")
        
        public_key = private_key.public_key()
        public_key_s = key.serialize(public_key)
        self.assertIsInstance(public_key_s, bytes, "RSAPublicKey should serialize into bytes.")
        self.assertNotEqual(id(public_key), id(key.deserialize(public_key_s)))
        self.assertEqual(public_key, key.deserialize(public_key_s), "Deserialized key should have the same public numbers as the unserialized key.")
    
    def test_signing(self):
        private_key1 = key.generate()
        private_key2 = key.generate()
        public_key1  = private_key1.public_key()

        data = urandom(256)
        
        signature1 = key.sign(private_key1, data)
        signature2 = key.sign(private_key2, data)
        self.assertIsInstance(signature1, bytes, "Signature should be of type 'bytes'.")
        self.assertTrue(key.verify(public_key1, data, signature1), "Should return True for signatures using the associated private key")
        self.assertFalse(key.verify(public_key1, data, signature2), "Should return False for signatures generated with foreign private key")
        self.assertFalse(key.verify(public_key1, bytes([]), signature2), "Should return false for empty byte array.")
    
    def test_encryption(self):
        private_key1 = key.generate()
        public_key1  = private_key1.public_key()
        private_key2 = key.generate()

        # data = urandom(1024)
        data = b'Hello World!'

        encrypted_data = key.encrypt(public_key1, data)
        self.assertEqual(len(encrypted_data) % 256, 0, "Since we are using a 256 bit hashing function, encrypted data lenght should be a multiple of 256.")
        self.assertNotEqual(data, encrypted_data, "Encrypted message should differ from the unencrypted message")

        self.assertEqual(data, key.decrypt(private_key1, encrypted_data), "Decrypted message should be the same as the unencrypted message.")
        self.assertRaises(ValueError, lambda: key.decrypt(private_key2, encrypted_data))


if __name__ == "__main__":
    unittest.main()