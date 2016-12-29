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


def setup_log_files():
    file_drive, file_path = os.path.splitdrive(__file__)
    log_path = os.path.join(file_drive, "/python_logs")
    full_path, file_name = os.path.split(__file__)
    file_name, file_ext = os.path.splitext(file_name)
    if not os.path.isdir(log_path):
        os.mkdir(log_path)
    debug_logfile = (log_path + "/" +  file_name + "_debug.log")
    info_logfile = (log_path + "/" + file_name + "_info.log")
    return debug_logfile, info_logfile


def setup_log_handlers(debug_logfile, info_logfile):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = []
    # Create desired handlers
    debug_handler = logging.handlers.TimedRotatingFileHandler(debug_logfile, when="h", interval=1, backupCount=24, encoding=None, delay=False, utc=False, atTime=None)
    info_handler = logging.handlers.TimedRotatingFileHandler(info_logfile, when="h", interval=1, backupCount=24, encoding=None, delay=False, utc=False, atTime=None)
    console_handler = logging.StreamHandler()
    # Create individual formats for each handler
    debug_formatter = logging.Formatter('%(asctime)-24s,  %(levelname)-8s, %(message)s')
    info_formatter = logging.Formatter('%(asctime)-24s,  %(levelname)-8s, %(message)s')    
    console_formatter = logging.Formatter('%(asctime)-24s,  %(levelname)-8s, %(message)s')
    # Set formatting options for each handler
    debug_handler.setFormatter(debug_formatter)
    info_handler.setFormatter(info_formatter)
    console_handler.setFormatter(console_formatter)
    # Set logging levels for each handler
    debug_handler.setLevel(logging.DEBUG)
    info_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)
    # Add handlers to root logger
    root.addHandler(debug_handler)
    root.addHandler(info_handler)
    root.addHandler(console_handler)


# Define test class *******************************************************************************
class TestWemoServer(unittest.TestCase):
    def setUp(self):
        debug_file, info_file = setup_log_files()
        setup_log_handlers(debug_file, info_file)
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
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", 1)
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", 1)
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", 1)
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", 0)
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", 0)
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", 0)


    def test_get_device_state(self):
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, 0)
        self.assertEqual(self.device2_state, 0)
        self.assertEqual(self.device3_state, 0)
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", 1)
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, 1)
        self.assertEqual(self.device2_state, 0)
        self.assertEqual(self.device3_state, 0)
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", 1)
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, 1)
        self.assertEqual(self.device2_state, 1)
        self.assertEqual(self.device3_state, 0)
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", 1)
        self.device1_state = self.wemo_server.get_device_state("lrlt1", "192.168.86.25")
        self.device2_state = self.wemo_server.get_device_state("drlt1", "192.168.86.26")
        self.device3_state = self.wemo_server.get_device_state("br3lt1", "192.168.86.31")
        self.assertEqual(self.device1_state, 1)
        self.assertEqual(self.device2_state, 1)
        self.assertEqual(self.device3_state, 1)
        self.wemo_server.set_device_state("lrlt1", "192.168.86.25", 0)
        self.wemo_server.set_device_state("drlt1", "192.168.86.26", 0)
        self.wemo_server.set_device_state("br3lt1", "192.168.86.31", 0)





if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout)
    logger = logging.getLogger(__name__)
    logger.level = logging.DEBUG
    logger.debug("\n\nStarting log\n")
    unittest.main() 