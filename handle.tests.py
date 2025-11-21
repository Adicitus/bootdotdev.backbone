import unittest
import uuid
import socket
import queue
import time

import key, frame
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
    
    def test_lifecycle(self):
        client_key = key.generate()
        client_key_pub = client_key.public_key()
        client = Identity(uuid.uuid4(), client_key_pub)
        server = IdentityComponent()
        socket1, socket2 = socket.socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM)
        
        server_queue = handle.get_server_queue()

        connection_handler = handle.ClientHandler(socket1, client, server)

        try:        
            connection_handler.start()

            time.sleep(0.01)

            self.assertFalse(server_queue.empty(), "Handler should have posted a message in the server queue when it started.")
            print(server_queue.get(timeout=3))
            self.assertTrue(server_queue.empty(), "There should only have been 1 message in the queue.")

            data = b'Hi!'
            frame.send(socket2, data, server.server_state["public_key"])
            time.sleep(0.01)

            self.assertFalse(server_queue.empty(), "Currently all messages received by the socket monitor should be forwarded top the server queue")
            self.assertEqual(server_queue.get(timeout=3), data, "Currently all messages received by the socket monitro should be forwarded top the server queue")

            client_queue = handle.get_client_queue(client.id)
            self.assertIsInstance(client_queue, queue.Queue, "The queue monitor should have registered a queue when it started.")

            client_queue.put(b'bye')
            connection_handler.thread.join(timeout=3)

            self.assertTrue(connection_handler.stop_flag.is_set(), "Currently, any message sent to the handler via the queue should cause it to stop.")
            self.assertIsNone(handle.get_client_queue(client.id), msg="The client's queue monitor should have removed the queue when it stopped.")
            with self.assertRaises(OSError):
                socket1.sendall(b'Hi!')
        finally:
            connection_handler.stop(block=True)
            socket2.close()




if __name__ == "__main__":
    unittest.main(verbosity=2)