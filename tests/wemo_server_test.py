#!/usr/bin/python3
""" wemo_server_test.py:   
""" 

# Import Required Libraries (Standard, Third Party, Local) ****************************************
import logging
import unittest
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
from wemo_gateway.wemo_server import WemoServer


# Define test class *******************************************************************************
class TestWemoServer(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self.wemo_server = WemoServer()

    def test_setup_log_files(self):
        self.debug_file, self.info_file = self.wemo_server.setup_log_files()
        self.assertEqual(self.debug_file, "c:/python_logs/wemo_server_debug.log")
        self.assertEqual(self.info_file, "c:/python_logs/wemo_server_info.log")





if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger(__name__)
    logger.level = logging.DEBUG
    logger.debug("\n\nStarting log\n")
    unittest.main() 