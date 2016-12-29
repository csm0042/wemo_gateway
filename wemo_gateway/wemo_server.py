#!/usr/bin/python3
""" wemo_server.py: Log server process
"""

# Import Required Libraries (Standard, Third Party, Local) ****************************************
import datetime
import logging
import logging.handlers
import os
import sys
import time
import multiprocessing
from multiprocessing.connection import Listener
import pywemo



# Authorship Info *********************************************************************************
__author__ = "Christopher Maue"
__copyright__ = "Copyright 2016, The Maue-Home Project"
__credits__ = ["Christopher Maue"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Christopher Maue"
__email__ = "csmaue@gmail.com"
__status__ = "Development"


# Main process class ******************************************************************************
class WemoServer(object):
    """ Log server that listens on port 6000 for incoming messages from other processes """
    def __init__(self):
        # Set up local logging
        self.setup_log_files()
        self.setup_log_handlers()
        self.logger = logging.getLogger(__name__)

        self.setup_listener_connection("localhost", 6013, b"password")
        self.conn = None

        self.device = None
        self.device_list = []
        self.state = int()
        self.main_loop = True


    def setup_log_files(self):
        self.file_drive, self.file_path = os.path.splitdrive(__file__)
        self.log_path = os.path.join(self.file_drive, "/python_logs")
        self.full_path, self.file_name = os.path.split(__file__)
        self.file_name, self.file_ext = os.path.splitext(self.file_name)
        if os.path.isdir(self.log_path):
            print("logging to file folder: ", self.log_path)
        else:
            os.mkdir(self.log_path)
            print("creating log file folder: ", self.log_path)
        self.debug_logfile = (self.log_path + "/" +  self.file_name + "_debug.log")
        self.info_logfile = (self.log_path + "/" + self.file_name + "_info.log")
        return self.debug_logfile, self.info_logfile


    def setup_log_handlers(self):
        root = logging.getLogger()
        root.handlers = []
        # Create desired handlers
        debug_handler = logging.handlers.TimedRotatingFileHandler(self.debug_logfile, when="h", interval=1, backupCount=24, encoding=None, delay=False, utc=False, atTime=None)
        info_handler = logging.handlers.TimedRotatingFileHandler(self.info_logfile, when="h", interval=1, backupCount=24, encoding=None, delay=False, utc=False, atTime=None)
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
        

    def setup_listener_connection(self, host, port, password):
        """ Set up a listener object """
        self.listener = Listener((host, port), authkey=password)


    def discover_device(self, name, address):
        """ Searches for a wemo device on the network at a particular IP address and appends it to
        the master device list if found """
        self.logger.debug("Searching for wemo device at: %s", address)
        self.port = None
        self.device = None
        # Probe device at specified IP address for port it is listening on
        try:
            self.port = pywemo.ouimeaux_device.probe_wemo(address)
        except:
            self.logger.warning("Error discovering port of wemo device at address: %s", address)
            self.port = None
        # If port is found, probe device for type and other attributes
        if self.port is not None:
            self.logger.debug("Found wemo device at: %s on port: %s", address, str(self.port))
            self.url = 'http://%s:%i/setup.xml' % (address, self.port)
            try:
                self.device = pywemo.discovery.device_from_description(self.url, None)
            except:
                self.logger.warning("Error discovering attributes for device at address: %s, port: %s", address, str(self.port))
                self.device = None
        else:
            self.logger.warning("No wemo device detected at: %s", address)
        # If device is found and probe was successful, check existing device list to
        # determine if device is already present in list
        if self.port is not None and self.device is not None:
            if self.device.name.find(name) != -1:
                self.logger.debug("Discovery successful for wemo device: %s at: %s, port: %s", name, address, str(self.port))
                # Search device list to determine if device already exists
                for index, device in enumerate(self.device_list):
                    if self.device.name == device.name:
                        self.logger.debug("Device: %s already exists in device list at address: %s and port: %s", self.device.name, address, self.port)
                        self.device_list[index] = copy.copy(device)
                        self.logger.debug("Replacing old device [%s] record in know device list with updated device attributes", self.device.name)
                        break
                else:
                # If not found in list, add it
                    self.logger.debug("Device [%s] not previously discovered.  Adding to known device list", self.device.name)
                    self.device_list.append(copy.copy(self.device))
                    self.logger.debug("Updated device list: %s", str(self.device_list))
                    return self.device
            else:
                self.logger.error("Device name mis-match between found device and configuration")
        else:
            self.logger.warning("Device was not found")
            return None


    def set_device_state(self, name, address, state):
        """ Searches list for existing wemo device with matching name, then sends on command
        to device if found """
        self.found = False
        # Search list of existing devices on network for matching device name
        for index, device in enumerate(self.device_list):
            # If match is found, send ON command to device
            if device.name.find(name) != -1:
                self.found = True
                if state == 0:
                    device.off()
                    self.logger.debug("OFF command sent to device: %s", name)
                    return True
                elif state == 1:
                    device.on()
                    self.logger.debug("ON command sent to device: %s", name)
                    return True
        # If match is not found, log error and continue
        if self.found is False:
            self.logger.warning("Could not find device: %s on the network", name)
            return False           


    def get_device_status(self, name, address):
        """ Searches list for existing wemo device with matching name, then sends "get status-
        update" message to device if found """
        self.found = False
        self.logger.debug("Querrying status for device: %s", name)
        # Search list of existing devices on network for matching device name
        for index, device in enumerate(self.device_list):
            # If match is found, get status update from device, then send response message to
            # originating process
            if device.name.find(name) != -1:
                self.found = True
                self.logger.debug("Found device [%s] in existing device list", name)
                self.state = str(device.get_state(force_update=True))
                self.logger.debug("Returning status [%s] to main program", self.state)
                return self.state
        if self.found is False:
            self.logger.warning("Could not find device [%s] in existing device list", name)
            return None 


    def process_message(self, msg):
        if msg.dest == "6013":
            # If message is a heartbeat, update heartbeat and reset
            if msg.type == "001":
                self.heartbeat = datetime.datetime.now()
                print("Resetting heartbeat")
            # Discover device command
            elif msg.type == "160":
                self.discover_device(msg.name, msg.payload)
            # Set device state command
            elif msg.type == "161":
                self.set_device_state(msg.name, msg.payload, msg.state)
            # Read device current status
            elif msg.type == "162":
                self.get_device_status(msg.name, msg.payload)
            # Kill gateway process
            elif msg.type == "999":
                self.logger.info("Kill code received - Shutting down")
                self.shutdown_time = datetime.datetime.now()
                self.main_loop = False


    def run(self):
        """ Runs a connection listener and processes any messages that are received """
        while self.main_loop is True:
            self.conn = self.listener.accept()
            self.msg = self.conn.recv()
            self.conn.close()
            self.process_message(self.msg)


if __name__ == "__main__":
    listener = LogServer()
    listener.run()