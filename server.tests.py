import unittest
import time
import tomllib

from identity import IdentityComponent
from server import BackboneServer

class TestServer(unittest.TestCase):
    def test_server_creation_default(self):
        server = BackboneServer()
        self.assertIsInstance(server, BackboneServer)
    
    def test_server_creation_custom(self):
        with open("./settings.toml", 'rb') as f:
            settings = tomllib.load(f)
        auth = IdentityComponent()
        server = BackboneServer(identities=auth, settings=settings)
        self.assertIsInstance(server, BackboneServer)
    
    def test_server_start_stop(self):
        server = BackboneServer()
        server.start()
        time.sleep(1)
        server.stop()
        

if __name__ == "__main__":
    unittest.main()