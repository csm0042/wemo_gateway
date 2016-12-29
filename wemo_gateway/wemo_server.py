#!/usr/bin/python3
""" wemo_server.py: Log server process
"""

# Import Required Libraries (Standard, Third Party, Local) ****************************************
import copy
import datetime
import logging
import logging.handlers
import os
import sys
import time
import multiprocessing
from multiprocessing.connection import Listener
import pywemo
sys.path.insert(0, os.path.abspath('..'))
import message



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
    """ Log server that listens on port 6013 for incoming messages from other processes """
    def __init__(self, logger=None):
        # Set up local logging
        self.logger = logger or logging.getLogger(__name__)
        self.listener = None
        self.conn = None
        self.device = None
        self.device_list = []
        self.state = str()
        self.main_loop = True
        self.logger.debug("Init complete")


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
        self.loop_count = 0
        while self.found is False and self.loop_count < 2:
            # Search list of existing devices on network for matching device name
            for index, device in enumerate(self.device_list):
                # If match is found, send ON command to device
                if device.name.find(name) != -1:
                    self.found = True
                    if state == "0":
                        device.off()
                        self.logger.debug("OFF command sent to device: %s", name)
                        return True
                    elif state == "1":
                        device.on()
                        self.logger.debug("ON command sent to device: %s", name)
                        return True
            else:
                self.discover_device(name, address)
                self.loop_count += 1
        # If match is still not found, log error and continue
        if self.found is False:
            self.logger.warning("Could not find device: %s on the network", name)
            return False           


    def get_device_state(self, name, address):
        """ Searches list for existing wemo device with matching name, then sends "get status-
        update" message to device if found """
        self.found = False
        self.logger.debug("Querrying status for device: %s", name)
        self.loop_count = 0
        while self.found is False and self.loop_count < 2:
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
            else:
                self.discover_device(name, address)
                self.loop_count += 1
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
                self.get_device_state(msg.name, msg.payload)
            # Kill gateway process
            elif msg.type == "999":
                self.logger.info("Kill code received - Shutting down")
                self.shutdown_time = datetime.datetime.now()
                self.main_loop = False


    def run(self):
        """ Runs a connection listener and processes any messages that are received """
        self.setup_listener_connection("localhost", 6013, b"password")
        self.logger.debug("Begin running listener loop")
        while self.main_loop is True:
            self.conn = self.listener.accept()
            self.logger.info("Accepted connection from: %s", str(self.listener.last_accepted))
            time.sleep(0.010)
            if self.conn.poll() is True:
                self.logger.info("Message detected.  Begin receving")
                self.msg_raw = self.conn.recv()
                print(self.msg_raw)
                self.msg = message.Message(raw=self.msg_raw)
            self.conn.close()
            if self.msg is not None:
                self.logger.info("Processing message")
                self.logger.info("Source: %s", self.msg.source)
                self.logger.info("Dest: %s", self.msg.dest)
                self.logger.info("Type: %s", self.msg.type)
                self.logger.info("Name: %s", self.msg.name)
                self.logger.info("State: %s", self.msg.state)
                self.logger.info("Payload: %s", self.msg.payload)
                self.process_message(self.msg)
            self.msg = None
            time.sleep(0.010)

# Logging helper functions ************************************************************************
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
    root = logging.getLogger(__name__)
    root.setLevel(logging.DEBUG)
    root.handlers = []
    # Create desired handlers
    debug_handler = logging.FileHandler(debug_logfile)
    info_handler = logging.FileHandler(info_logfile)
    console_handler = logging.StreamHandler(sys.stdout)
    # Set logging levels for each handler
    debug_handler.setLevel(logging.DEBUG)
    info_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)
    # Create individual formats for each handler
    debug_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    info_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')    
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # Set formatting options for each handler
    debug_handler.setFormatter(debug_formatter)
    info_handler.setFormatter(info_formatter)
    console_handler.setFormatter(console_formatter)
    # Add handlers to root logger
    root.addHandler(debug_handler)
    root.addHandler(info_handler)
    root.addHandler(console_handler)
    root.debug("logging configured with 3 handlers")


if __name__ == "__main__":
    print("\n\nWemo Server Is Running and Listening for Connections...")
    debug_file, info_file = setup_log_files()
    setup_log_handlers(debug_file, info_file)
    logger = logging.getLogger(__name__)
    wemo_server = WemoServer()
    wemo_server.run()