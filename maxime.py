#!/usr/bin/env python

import dbus
import ConfigParser
import os
import argparse
import logging
import time
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from pulsectl import Pulse as PulseLib


class App:
    """
    Shell class for application methods (arguments, config, that sort of
    stuff).
    """
    @staticmethod
    def read_config_file(file_path):
        """
        Read configuration directives from the config file.
        :param file_path: Path to the file that we want to read.
        :return: ConfigParser object.
        """
        # Read the config
        config = ConfigParser.RawConfigParser()
        config.read(file_path)

        return config

    @staticmethod
    def read_args():
        """
        Read arguments from the CLI.
        :return: ArgParse object.
        """
        description = "Bluetooth audio connection manager."
        epilog = "Written by Grant Cohoe (https://grantcohoe.com)"

        parser = argparse.ArgumentParser(description=description, epilog=epilog)
        parser.add_argument('-c', '--config', type=str,
                            default='~/.config/maxime.ini',
                            help='path to configuration file')

        parser.add_argument('-v', '--verbose',
                             default=False,
                             action='store_true',
                             help='enable verbose logging')

        parser.add_argument('-l', '--logfile', type=str,
                            default=('/var/tmp/maxime_%s.log' % os.getlogin()),
                            help='path to log file (or emptystring for STDOUT)')

        parser.add_argument('--connect',
                            default=False,
                            action='store_true',
                            help='simulate a connect event')

        parser.add_argument('--disconnect',
                            default=False,
                            action='store_true',
                            help='simulate a disconnect event')

        return parser.parse_args()

    @staticmethod
    def get_config_file_path(args):
        """
        Return a normalized path to our configuration file.
        :param args: ArgParse object.
        :return: String of the path to our config file.
        """
        # Normalize our path
        file_path = args.config
        file_path = os.path.expanduser(file_path)
        file_path = os.path.abspath(file_path)

        # Test if the file exists
        if os.path.exists(file_path) is False:
            raise Exception("Config file at '%s' does not exist!" % file_path)

        return file_path

    @staticmethod
    def setup_logging(verbose, filepath):
        """
        Setup the logging facility.
        :param verbose: Boolean of whether to be loud or not.
        :param filepath: Log file path.
        :return: None
        """
        if filepath is not '':
            if os.path.exists(filepath) is False:
                os.mknod(filepath)

        # You can only call this once, or others will be a noop.
        if verbose is True:
            logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', 
                                datefmt='%m/%d/%Y %H:%M:%S',
                                filename=filepath,
                                level=logging.DEBUG)
        else:
            logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', 
                                datefmt='%m/%d/%Y %H:%M:%S',
                                filename=filepath,
                                level=logging.INFO)

        logging.info("Starting logging facility")

    @staticmethod
    def log_angry(level, message):
        """
        Log a message to both stdout and the log facility.
        :param level: The logging.LEVEL
        :param message: The message
        :return: None
        """
        logging.log(level, message)
        print message


class DBus:
    """
    Shell class for DBus-related functions.
    """
    BT_SERVICE = "org.bluez"
    INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties"
    INTERFACE_DEVICE = "org.bluez.Device1"
    SIGNAL_PROPERTIESCHANGED = "PropertiesChanged"

    @staticmethod
    def get_normal_mac(mac):
        """
        Return a DBus-normalized MAC address.
        :param mac: MAC address to normalize
        :return: A DBus/BlueZ compatible MAC address
        """
        return mac.replace(':','_')

    @staticmethod
    def get_bt_device_path(adapter, mac):
        """
        Return the DBus object path of a particular device.
        :param adapter: The Bluetooth interface.
        :param mac: The normalized MAC address.
        :return: A string of the device path.
        """
        mac = DBus.get_normal_mac(mac)
        service = DBus.BT_SERVICE.replace('.', '/')
        obj_path = "/%s/%s/dev_%s" % (service, adapter, mac)

        return obj_path


class Pulse:
    """
    Shell class for Pulse related functions.
    """
    @staticmethod
    def get_sink_device(pulse_conn, description):
        """
        Return a pulse device
        :param pulse_conn: Pulse connection object.
        :param description: The text used for identification.
        :return: A Pulse device or None
        """
        for dev in pulse_conn.sink_list():
            if dev.description == description:
                return dev

        logging.error("Sink device not found! (Was searching for \"%s\")" % description)

    @staticmethod
    def get_sink_input_device(pulse_conn, name):
        """
        Return a Pulse device of our audio source (in my case, LADSPA EQ)
        :param pulse_conn: Pulse connection object.
        :param name: The name of the device to search for.
        :return: A Pulse device or None
        """
        for dev in pulse_conn.sink_input_list():
            if dev.name == name:
                return dev

        logging.error("Sink Input device not found! (Was searching for \"%s\")" % name)

    @staticmethod
    def move_input(pulse_conn, source, destination):
        """
        Move a Pulse stream
        :param pulse_conn: Pulse connection object.
        :param source: Source device that we want to redirect.
        :param destination: Target device that we want to hear from.
        :return: None
        """
        logging.info("Moving stream of \"%s\" to \"%s\"" % (source.name, destination.description))
        pulse_conn.sink_input_move(source.index, destination.index)


class AudioRouter:
    """
    Main functional class. Holds the logic for listening for DBus events and
    responding to them.
    """
    def __init__(self, config):
        """
        Constructor for the AudioRouter class. It sets some other basic stuff for us.
        :param config: The output from ConfigParser
        """
        self.config = config
        self.bt_adapter = config.get('bluetooth', 'adapter')
        self.bt_mac = config.get('bluetooth', 'device_mac')
        self.bt_object_path = DBus.get_bt_device_path(self.bt_adapter, self.bt_mac)
        self.dbus_bt_dev_proxy = None
        self.dbus_bt_dev_properties = None

    def setup_dbus(self):
        """
        Setup our DBus proxy object and properties interface. The proxy object
        is used to perform operations against a specific DBus object.
        The properties interface is our templated way into viewing properties
        about the device we just (dis)connected.
        :return: None
        """
        bus = dbus.SystemBus()
        self.dbus_bt_dev_proxy = bus.get_object(DBus.BT_SERVICE,
                                                self.bt_object_path)
        self.dbus_bt_dev_proxy.connect_to_signal(DBus.SIGNAL_PROPERTIESCHANGED,
                                                 self._dbus_handler,
                                                 dbus_interface=DBus.INTERFACE_PROPERTIES)
        self.dbus_bt_dev_properties = dbus.Interface(self.dbus_bt_dev_proxy,
                                                     dbus_interface=DBus.INTERFACE_PROPERTIES)

    def _dbus_handler(self, interface, changed_properties, signature):
        """
        Event handler for a change in a Bluetooth device state.
        :param interface: String of the DBus interface.
        :param changed_properties: Dictionary of the properties that changed.
        :param signature: String of something that I don't care about.
        :return: None
        """
        logging.info("%s: Change detected." % interface)

        # Right now I only care about device connectivity
        if interface != DBus.INTERFACE_DEVICE:
            logging.info("%s: Ignorning change." % interface)
            return

        # Test for the appropriate key in the messages we will get
        try:
            conn_state = bool(changed_properties['Connected'])
        except KeyError:
            # Ignore a ServicesResolved message
            try:
                bool(changed_properties['ServicesResolved'])
                logging.info("%s: Ignoring ServicesResolved." % interface)
                return
            except Exception:
                logging.error("%s: Some weird error occurred "
                              "(and it wasnt ServicesResolved)." % interface)
                return
        except Exception:
            logging.error("%s: Some weird error occurred." % interface)
            return

        # Deal with the connection state
        logging.info("%s: Connected -> %s" % (interface, conn_state))
        self.manage_connection(conn_state)

    def get_bt_dev_property(self, property):
        """
        Return a DBus property from our device.
        :param property: String of the property.
        :return: The value of the property.
        """
        return self.dbus_bt_dev_properties.Get(DBus.INTERFACE_DEVICE, property)

    def manage_connection(self, conn_state):
        """
        Perform connection or disconnection actions from an event.
        :param conn_state: Boolean of whether the device was connected or not.
        :return: None
        """
        with PulseLib('maxime-manage') as pulse:
            # @TODO Make this not static
            ladspa_dev = Pulse.get_sink_input_device(pulse, "LADSPA Stream")

            # We default to speakers, and override with headphones
            # @TODO Make this not static
            target_device = Pulse.get_sink_device(pulse,
                                                  "SB X-Fi Surround 5.1 Pro Digital Stereo (IEC958)")
            if conn_state is True:
                # We need to a wait a few seconds for Pulse to catch up
                time.sleep(4)
                target_device = Pulse.get_sink_device(pulse, self.get_bt_dev_property('Name'))

            logging.info("Target device is \"%s\"" % target_device.description)

            # Tell Pulse to move the stream to our target device
            Pulse.move_input(pulse, ladspa_dev, target_device)

        # @TODO This should probably deal with errors, but until then...
        logging.info("Success!")


def main():
    """
    Main program logic. Wait for dbus events and go from there.
    """
    # Parse command-line arguments
    args = App.read_args()

    # Setup configuration structures (Note: No logging can occur before
    # this otherwise it will break the output)
    config = App.read_config_file(App.get_config_file_path(args))
    App.setup_logging(args.verbose, args.logfile)

    # DBus setup
    DBusGMainLoop(set_as_default=True)

    # Setup our router object which will handle what to do when a BT event hits
    # This must occur after the DBusGMainLoop call above.
    ar = AudioRouter(config)
    ar.setup_dbus()

    # See if we are simulating
    if args.connect or args.disconnect:
        App.log_angry(logging.WARN, "Simulating an event. DBus will not monitor.")

        # Test if the user is paying attention
        if args.connect and args.disconnect:
            App.log_angry(logging.ERROR, "You cannot specify both connect and disconnect")
            exit(1)

        # Perform
        if args.connect:
            ar._dbus_handler(DBus.INTERFACE_DEVICE, {"Connected": True}, None)
        if args.disconnect:
            ar._dbus_handler(DBus.INTERFACE_DEVICE, {"Connected": False}, None)

        App.log_angry(logging.WARN, "Simulation complete!")
        exit()

    # DBus event loop. Listen to the sounds....
    dbus_loop = GLib.MainLoop()
    dbus_loop.run()

if __name__ == "__main__":
    main()
