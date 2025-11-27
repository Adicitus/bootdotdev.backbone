import unittest
import time

from identity import IdentityComponent
from server import BackboneServer
import settings

class TestServer(unittest.TestCase):
    def test_server_creation_default(self):
        server = BackboneServer()
        self.assertIsInstance(server, BackboneServer)
    
    def test_server_creation_custom(self):
        auth = IdentityComponent()
        server = BackboneServer(identities=auth)
        self.assertIsInstance(server, BackboneServer)
    
    def test_server_start_stop(self):
        server = BackboneServer()
        server.start()
        time.sleep(1)
        server.stop()
        

if __name__ == "__main__":
    print(type(settings))
    unittest.main()