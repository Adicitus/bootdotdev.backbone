from datetime import datetime
from os import urandom
from uuid import uuid4
import unittest, uuid

import message
from message import BackboneMessage, BackboneMessageC2C, BackboneMessageC2S, BackboneMessageS2S, BackboneC2SType, BackboneS2SType, BackboneMessageFormat

class TestMessageTranslation(unittest.TestCase):

    def test_message_formats(self):
        self.assertTrue(BackboneMessageFormat.C2C == 0)
        self.assertTrue(BackboneMessageFormat.C2S == 1)
        self.assertTrue(BackboneMessageFormat.S2S == 2)
    
    def test_message_c2s_types(self):
        self.assertTrue(BackboneC2SType.HEARTBEAT == 0)
        self.assertTrue(BackboneC2SType.STOP == 15)
    
    def test_message_s2s_types(self):
        self.assertTrue(BackboneS2SType.DONE == 14)
        self.assertTrue(BackboneS2SType.STOP == 15)
        

    def test_message_c2c_creation(self):
        msg = BackboneMessageC2C(uuid4(), urandom(256))
        self.assertIsInstance(msg, BackboneMessage)
        self.assertIsInstance(msg, BackboneMessageC2C)
    
    def test_message_c2s_creation(self):
        BackboneMessageC2S(BackboneC2SType.STOP)
        BackboneMessageC2S(BackboneC2SType.HEARTBEAT)
        BackboneMessageC2S(BackboneC2SType.STOP, datetime.now())
        BackboneMessageC2S(BackboneC2SType.HEARTBEAT, datetime.now())
        BackboneMessageC2S(15)
        BackboneMessageC2S(0)
        with self.assertRaises(ValueError):
            msg = BackboneMessageC2S(-1)
    
    def test_message_s2s_creation(self):
        BackboneMessageS2S(BackboneS2SType.STOP)
        BackboneMessageS2S(BackboneS2SType.DONE)
        BackboneMessageS2S(BackboneS2SType.STOP, datetime.now())
        BackboneMessageS2S(BackboneS2SType.DONE, datetime.now())
        BackboneMessageS2S(15)
        BackboneMessageS2S(14)
        with self.assertRaises(ValueError):
            BackboneMessageS2S(-1)
    
    def test_message_c2c_equality(self):
        recipient = uuid4()
        payload   = urandom(256)
        self.assertEqual(BackboneMessageC2C(recipient, payload), BackboneMessageC2C(recipient, payload))
        self.assertNotEqual(BackboneMessageC2C(recipient, payload), BackboneMessageC2C(uuid4(), payload))
        self.assertNotEqual(BackboneMessageC2C(recipient, payload), BackboneMessageC2C(recipient, urandom(256)))

    def test_message_c2s_equality(self):
        self.assertEqual(BackboneMessageC2S(BackboneC2SType.HEARTBEAT), BackboneMessageC2S(BackboneC2SType.HEARTBEAT))
        self.assertEqual(BackboneMessageC2S(BackboneC2SType.STOP), BackboneMessageC2S(BackboneC2SType.STOP))
        self.assertNotEqual(BackboneMessageC2S(BackboneC2SType.HEARTBEAT), BackboneMessageC2S(BackboneC2SType.STOP))
        self.assertNotEqual(BackboneMessageC2S(BackboneC2SType.STOP), BackboneMessageC2S(BackboneC2SType.HEARTBEAT))
    
    def test_message_s2s_equality(self):
        self.assertEqual(BackboneMessageS2S(BackboneS2SType.DONE), BackboneMessageS2S(BackboneS2SType.DONE))
        self.assertEqual(BackboneMessageS2S(BackboneS2SType.STOP), BackboneMessageS2S(BackboneS2SType.STOP))
    
    def test_message_c2c_to_bytes(self):
        recipient = uuid4()
        payload   = urandom(16)
        msg = BackboneMessageC2C(recipient, payload)
        frame = msg.to_bytes()
        self.assertEqual(frame, b'\x00' + recipient.bytes + payload)
    
    def test_message_c2s_to_bytes(self):
        timestamp = datetime.now()
        timestamp_b = int(timestamp.timestamp()).to_bytes(4)
        msg = BackboneMessageC2S(BackboneC2SType.STOP, timestamp)
        frame = msg.to_bytes()
        self.assertEqual(frame, b'\x1F' + timestamp_b)

    def test_message_s2s_to_bytes(self):
        timestamp = datetime.now()
        timestamp_b = int(timestamp.timestamp()).to_bytes(4)
        msg = BackboneMessageS2S(BackboneS2SType.STOP, timestamp)
        frame = msg.to_bytes()
        self.assertEqual(frame, b'\x2F' + timestamp_b)

    def test_message_c2c_from_bytes(self):
        recipient = uuid4()
        payload   = urandom(16)
        msg = BackboneMessageC2C(recipient, payload)
        self.assertEqual(msg, BackboneMessage.from_bytes(b'\x00' + recipient.bytes + payload))
    
    def test_message_c2s_from_bytes(self):
        timestamp = datetime.now()
        timestamp_b = int(timestamp.timestamp()).to_bytes(4)
        msg = BackboneMessageC2S(BackboneC2SType.STOP, timestamp)
        self.assertEqual(msg, BackboneMessage.from_bytes(b'\x1F' + timestamp_b))

    def test_message_s2s_from_bytes(self):
        timestamp = datetime.now()
        timestamp_b = int(timestamp.timestamp()).to_bytes(4)
        msg = BackboneMessageS2S(BackboneS2SType.STOP, timestamp)
        self.assertEqual(msg, BackboneMessage.from_bytes(b'\x2F' + timestamp_b))
    
    def test_message_c2s_from_bytes_with_payload(self):
        timestamp = datetime.now()
        timestamp_b = int(timestamp.timestamp()).to_bytes(4)
        payload   = urandom(16)
        msg = BackboneMessageC2S(BackboneC2SType.STOP, timestamp, payload)
        self.assertEqual(msg, BackboneMessage.from_bytes(b'\x1F' + timestamp_b + payload))

    def test_message_s2s_from_bytes_with_payload(self):
        timestamp = datetime.now()
        timestamp_b = int(timestamp.timestamp()).to_bytes(4)
        payload   = urandom(16)
        msg = BackboneMessageS2S(BackboneS2SType.STOP, timestamp, payload)
        self.assertEqual(msg, BackboneMessage.from_bytes(b'\x2F' + timestamp_b + payload))


if __name__ == "__main__":
    unittest.main()