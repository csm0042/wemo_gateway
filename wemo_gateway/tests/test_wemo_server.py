#!/usr/bin/python3
""" wemo_server_test.py:   
""" 

# Import Required Libraries (Standard, Third Party, Local) ****************************************
import logging
import file_logger
import unittest
import os
import sys
#sys.path.insert(0, os.path.abspath('..'))
from wemo_gateway.wemo_server import WemoServer


# Define test class *******************************************************************************
class TestWemoServer(unittest.TestCase):
    def setUp(self):
        file_logger.setup_logging(__file__)
        self.logger = logging.getLogger(__name__)
        self.wemo_server = WemoServer()


    def test_setup_listener_connection(self):
        self.wemo_server.setup_listener_connection("localhost", 6013, b"password")
        self.assertNotEqual(self.wemo_server.listener, None)


    def test_discover_device(self):
        self.device1 = self.wemo_server.discover_device("lrlt1", "192.168.86.25")
        self.device2 = self.wemo_server.discover_device("drlt1", "192.168.86.26")
        self.assertEqual(len(self.wemo_server.device_list), 2)


    def test_set_device_state(self):
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", "1")
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", "1")
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", "1")
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", "0")
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", "0")
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", "0")


    def test_get_device_state(self):
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, "0")
        self.assertEqual(self.device2_state, "0")
        self.assertEqual(self.device3_state, "0")
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", "1")
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, "1")
        self.assertEqual(self.device2_state, "0")
        self.assertEqual(self.device3_state, "0")
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", "1")
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, "1")
        self.assertEqual(self.device2_state, "1")
        self.assertEqual(self.device3_state, "0")
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", "1")
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, "1")
        self.assertEqual(self.device2_state, "1")
        self.assertEqual(self.device3_state, "1")
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", "0")
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", "0")
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", "0")





if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger(__name__)
    logger.level = logging.DEBUG
    logger.debug("\n\nStarting log\n")
    unittest.main() 