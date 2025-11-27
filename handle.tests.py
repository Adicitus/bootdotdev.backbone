import unittest
import uuid
import socket
import queue
import time

import key, frame, message
from identity import IdentityComponent, Identity

import handle

class TestClientQueues(unittest.TestCase):
    def test_get_server_queue(self):
        self.assertIsInstance(handle.get_server_queue(), queue.Queue)

    def test_get_client_queue(self):
        client_id = uuid.uuid4()
        qr = handle._register_client(client_id)
        self.assertIsInstance(qr, queue.Queue)
        q = handle.get_client_queue(client_id)
        self.assertIsInstance(q, queue.Queue)
        self.assertEqual(qr, q)
        handle._deregister_client(client_id)
        self.assertIsNone(handle.get_client_queue(client_id))

class TestClientHandler(unittest.TestCase):
    def test_creation(self):
        client_key = key.generate()
        client_key_pub = client_key.public_key
        client = Identity(uuid.uuid4(), client_key_pub)
        server = IdentityComponent()
        socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)
        
        handle.ClientHandler(socket1, client, server)

        # Cleaning up sockets here since we're forefully closing the handler:
        socket1.close()
        socket2.close()
    
    def test_stop_by_queue(self):
        client_key = key.generate()
        client_key_pub = client_key.public_key()
        client = Identity(uuid.uuid4(), client_key_pub)
        server = IdentityComponent()
        socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

        connection_handler = handle.ClientHandler(socket1, client, server)

        try:        
            connection_handler.start()

            time.sleep(0.01)

            client_queue = handle.get_client_queue(client.id)
            self.assertIsInstance(client_queue, queue.Queue, "The queue monitor should have registered a queue when it started.")

            stop_s2s = message.BackboneMessageS2S(message.BackboneS2SType.STOP)
            client_queue.put(stop_s2s)
            connection_handler.thread.join(timeout=3)

            self.assertTrue(connection_handler.stop_flag.is_set(), "A S2S STOP message sent to the handler via the queue should cause it to stop.")
            self.assertIsNone(handle.get_client_queue(client.id), msg="The client's queue monitor should have removed the queue when it stopped.")
            with self.assertRaises(OSError, msg="The socket held by the handler should have been closed by the socket monitor."):
                socket1.sendall(b'Hi!')
        finally:
            connection_handler.stop(block=True)
            socket2.close()

    def test_stop_by_stop_message(self):
        client_key = key.generate()
        client_key_pub = client_key.public_key()
        client = Identity(uuid.uuid4(), client_key_pub)
        server = IdentityComponent()
        socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)

        connection_handler = handle.ClientHandler(socket1, client, server)

        try:
            connection_handler.start()

            time.sleep(0.01)

            frame.send(socket2, message.BackboneMessageC2S(message.BackboneC2SType.STOP).to_bytes(), server.server_state["public_key"])

            socket2.close()

            time.sleep(1)

            self.assertTrue(connection_handler.stop_flag.is_set(), "On discovering that the connection is closed, the socket monitor should have signalled the handler to stop")

            time.sleep(1)

            self.assertFalse(connection_handler.is_running(), "With the stop_flag set, the handler should stop all threads.")

            with self.assertRaises(OSError, msg="The socket held by the handler should have been closed by the socket monitor."):
                socket1.sendall(b'Hi!')

        finally:
            connection_handler.stop(block=True)
            socket2.close()
        
    def test_message_routing_rebound(self):
        client_key = key.generate()
        client_key_pub = client_key.public_key()
        client = Identity(uuid.uuid4(), client_key_pub)
        server = IdentityComponent()
        socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)
        
        connection_handler = handle.ClientHandler(socket1, client, server)

        try:
            connection_handler.start()

            time.sleep(0.01)

            sent_msg = message.BackboneMessageC2C(recipient=client.id, payload=b'Hi!')
            frame.send(socket2, sent_msg.to_bytes(), server.server_state["public_key"])
            time.sleep(0.01)

            received_msg = message.BackboneMessage.from_bytes(frame.read(socket2, client_key))
            self.assertEqual(received_msg, sent_msg)

        finally:
            connection_handler.stop(block=True)
            socket2.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)