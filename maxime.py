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
        """
        # Read the config
        config = ConfigParser.RawConfigParser()
        config.read(file_path)

        return config

    @staticmethod
    def read_args():
        """
        Read arguments from the CLI.
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

        return parser.parse_args()

    @staticmethod
    def get_config_file_path(args):
        """
        Return a normalized path to our configuration file.
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
        """
        return mac.replace(':','_')

    @staticmethod
    def get_bt_device_path(adapter, mac):
        """
        Return the DBus object path of a particular device.
        """
        mac = DBus.get_normal_mac(mac)
        service = DBus.BT_SERVICE.replace('.', '/')
        obj_path = "/%s/%s/dev_%s" % (service, adapter, mac)

        return obj_path

    @staticmethod
    def event_handler(interface, changed_properties, signature):
        """
        Event handler for a change in a Bluetooth device state.
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
                services_state = bool(changed_properties['ServicesResolved'])
                logging.info("%s: Ignoring ServicesResolved message." % interface)
                return
            except KeyError:
                # Some new edge case has appeared
                logging.error("%s: Key 'Connected' not in message and not ServiceResolved???" % interface)
                return

            logging.error("%s: Some weird error occurred." % interface)
            return

        # Deal with the connection state
        logging.info("%s: Connected -> %s" % (interface, conn_state))
        Pulse.manage_connection(conn_state)


class Pulse:
    """
    Shell class for Pulse related functions.
    """
    @staticmethod
    def get_sink_device(pulse_conn, description):
        """
        Return a pulse device
        :param description: The text used for identification.
        :return:
        """
        for dev in pulse_conn.sink_list():
            if dev.description == description:
                return dev

        logging.error("Sink device not found! (Was searching for \"%s\")" % description)

    @staticmethod
    def get_sink_input_device(pulse_conn, name):
        """
        Return a Pulse device of our audio source (in my case, LADSPA EQ)
        :param pulse_conn:
        :param name:
        :return:
        """
        for dev in pulse_conn.sink_input_list():
            if dev.name == name:
                return dev

        logging.error("Sink Input device not found! (Was searching for \"%s\")" % name)

    @staticmethod
    def move_input(pulse_conn, source, destination):
        """
        Move a Pulse stream
        :param pulse_conn:
        :param source:
        :param destination:
        :return:
        """
        logging.info("Moving stream of \"%s\" to \"%s\"" % (source.name, destination.description))
        pulse_conn.sink_input_move(source.index, destination.index)

    @staticmethod
    def manage_connection(conn_state):
        """
        Perform connection or disconnection actions from an event.
        :param conn_state:
        :return:
        """
        with PulseLib('maxime-manage') as pulse:
            ladspa_dev = Pulse.get_sink_input_device(pulse, "LADSPA Stream")

            target_device = Pulse.get_sink_device(pulse, "SB X-Fi Surround 5.1 Pro Digital Stereo (IEC958)")
            if conn_state is True:
                # We need to a wait a few seconds for Pulse to get its house
                # in order.
                time.sleep(4)
                target_device = Pulse.get_sink_device(pulse, "Bose QuietComfort 35")

            logging.info("Target device should be \"%s\"" % target_device.description)
            Pulse.move_input(pulse, ladspa_dev, target_device)

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
    # @TODO There will probably be more configuration options to deal with.

    # DBus setup
    DBusGMainLoop(set_as_default=True)

    adapter = config.get('bluetooth', 'adapter')
    mac = config.get('bluetooth', 'device_mac')

    obj_path = DBus.get_bt_device_path(adapter, mac)

    bus = dbus.SystemBus()
    dbus_bt_dev_proxy = bus.get_object(DBus.BT_SERVICE, obj_path)
    dbus_bt_dev_proxy.connect_to_signal(DBus.SIGNAL_PROPERTIESCHANGED,
                                   DBus.event_handler,
                                   dbus_interface=DBus.INTERFACE_PROPERTIES)
    
    # Print some info about the device
    dbus_bt_dev_properties = dbus.Interface(dbus_bt_dev_proxy,
                                            dbus_interface=DBus.INTERFACE_PROPERTIES)
    bt_dev_name = dbus_bt_dev_properties.Get(DBus.INTERFACE_DEVICE, 'Name')
    print bt_dev_name

    dbus_loop = GLib.MainLoop()
    dbus_loop.run()

if __name__ == "__main__":
    main()
