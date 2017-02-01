#!/usr/bin/python3
""" wemo_server.py: Log server process
"""

# Import Required Libraries (Standard, Third Party, Local) ****************************************
import copy
import datetime
import logging
import file_logger
import os
import sys
import time
import message
import multiprocessing
from multiprocessing.connection import Listener, Client
import pywemo
import queue


# Authorship Info *********************************************************************************
__author__ = "Christopher Maue"
__copyright__ = "Copyright 2016, The RpiHome Project"
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
        self.local_port = "6013"
        self.last_refnum = None
        self.listener = None
        self.conn = None
        self.device = None
        self.device_list = []
        self.state = str()
        self.main_loop = True
        self.logger.debug("Init complete")
        self.result = None
        self.msg_to_send = None
        self.payload = []


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
        # Log each message passed to the processor regardless of steps taken
        self.logger.debug("Received message [%s]", msg.raw)
        # Check if message is destined for this service and isn't a repeat
        if (msg.refnum != self.last_refnum) and (msg.dest == self.local_port):
            
            # If message is a heartbeat, update heartbeat datetime and generate msg ack
            if msg.msgtype == "001":
                self.heartbeat = datetime.datetime.now()
                self.logger.debug("Local heartbeat reset")
                self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="001A", payload="")
                # Log ack message and update last ref number register
                self.logger.debug("Returning ACK message [%s]", self.msg_to_send.raw)
                self.last_refnum = copy.copy(msg.refnum)
                self.logger.debug("Updating last refnum register to [%s]", self.last_refnum)
            
            # Discover device command
            if msg.msgtype == "160":
                self.payload = msg.payload.split(sep=",", maxsplit=2)
                if len(self.payload) >= 2:
                    self.logger.debug("Attempting to discover device [%s] at address [%s]", self.payload[0], self.payload[1])
                    self.discover_device(self.payload[0], self.payload[1])
                    self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="162A", payload="")
                else:
                    self.logger.warning("Incorrect message payload received for type 160")
                    self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="162A", payload="error")
                # Log ack message and update last ref number register
                self.logger.debug("Returning ACK message [%s]", self.msg_to_send.raw)
                self.last_refnum = copy.copy(msg.refnum)
                self.logger.debug("Updating last refnum register to [%s]", self.last_refnum)
            
            # Set device state command
            if msg.msgtype == "161":
                self.payload = msg.payload.split(sep=",", maxsplit=3)
                if len(self.payload) >= 3:
                    self.logger.debug("Attempting to set device [%s] at address [%s] to state [%s]", self.payload[0], self.payload[1], self.payload[2])
                    self.set_device_state(self.payload[0], self.payload[1], self.payload[2])
                    self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="161A", payload="")
                else:
                    self.logger.warning("Incorrect message payload received for type 161")
                    self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="161A", payload="error")
                # Log ack message and update last ref number register
                self.logger.debug("Returning ACK message [%s]", self.msg_to_send.raw)
                self.last_refnum = copy.copy(msg.refnum)
                self.logger.debug("Updating last refnum register to [%s]", self.last_refnum)

            # Read device current status
            if msg.msgtype == "162":
                self.payload = msg.payload.split(sep=",", maxsplit=2)
                if len(self.payload) >= 2:
                    self.logger.debug("Attempting to read status from device [%s] at address [%s]", self.payload[0], self.payload[1])
                    self.result = None
                    self.result = self.get_device_state(self.payload[0], self.payload[1])
                    if self.result is not None:
                        self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="162A", payload=(self.payload[0] + "," + self.payload[1] + "," + self.result))
                    else:
                        self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="162A", payload="error")
                # Log ack message and update last ref number register
                self.logger.debug("Returning ACK message [%s]", self.msg_to_send.raw)
                self.last_refnum = copy.copy(msg.refnum)
                self.logger.debug("Updating last refnum register to [%s]", self.last_refnum)
            
            # Kill gateway process
            if msg.msgtype == "999":
                self.logger.info("Kill code received - Shutting down")
                self.shutdown_time = datetime.datetime.now()
                self.main_loop = False
                self.msg_to_send = message.Message(refnum=msg.refnum, source=self.local_port, dest=msg.source, msgtype="999A", payload="")
                # Log ack message and update last ref number register
                self.logger.debug("Returning ACK message [%s]", self.msg_to_send.raw)
                self.last_refnum = copy.copy(msg.refnum)
                self.logger.debug("Updating last refnum register to [%s]", self.last_refnum)


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
                self.msg = message.Message(raw=self.msg_raw)
            self.conn.close()
            if self.msg is not None:
                self.logger.info("Processing message: %s", self.msg.raw)
                self.process_message(self.msg)
            if self.msg_to_send is not None:
                try:
                    self.conn = Client(("localhost", int(self.msg_to_send.dest)), authkey=b"password")
                    self.logger.info("Ack connection established.  Sending ACK message")
                    self.conn.send(self.msg_to_send.raw)
                    self.logger.info("ACK message sent.  Closing connection")
                    self.conn.close()
                    self.logger.info("Message ACK [%s] successfully sent", self.msg_to_send.raw)
                except:
                    self.logger.info("Unable to send message ACK [%s]", self.msg_to_send.raw)
                    pass
            self.msg = None
            self.msg_to_send = None
            time.sleep(0.010)




if __name__ == "__main__":
    print("\n\nWemo Server Is Running and Listening for Connections...")
    debug_file, info_file = file_logger.setup_log_files(__file__)
    logger = file_logger.setup_log_handlers(__file__, debug_file, info_file)
    #logger = logging.getLogger(__name__)
    wemo_server = WemoServer(logger=logger)
    wemo_server.run()