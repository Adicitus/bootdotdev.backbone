import os
import unittest
import time
import tomllib

from identity import IdentityComponent
from server import BackboneServer

class TestServer(unittest.TestCase):
    def test_server_creation_default(self):
        server = BackboneServer()
        self.assertIsInstance(server, BackboneServer)
    
    def test_server_default_settings(self):
        server = BackboneServer()
        self.assertIsInstance(server, BackboneServer)
        self.assertIsInstance(server.settings, dict)
        s = server.settings
        self.assertEqual(s["state_dir"], os.path.dirname(__file__))
        self.assertEqual(s["port"], 4000)
        self.assertEqual(s["challenge_size"], 2048)
        cs = s["client"]
        self.assertEqual(cs["heartbeat_timeout"], 600)
        self.assertEqual(cs["heartbeat_interval"], 300)
        

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