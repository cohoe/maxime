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

        parser.add_argument('--toggle',
                            default=False,
                            action='store_true',
                            help='toggle to another device')

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

    @staticmethod
    def send_notification(text, icon='', time=5000):
        """
        Send an OS notification to the user.
        :param text: Text to display.
        :param icon: Name of the icon to use.
        :param time: Time the notification should live.
        :return: None
        """

        # This blog post has a lot of good examples on how to do this.
        # http://cheesehead-techblog.blogspot.com/2009/02/five-ways-to-make-notification-pop-up.html
        app_name = "Maxime"
        id_num_to_replace = 0
        title = app_name

        actions_list = ''
        hint = ''

        # Create the objects and send!
        bus = dbus.SessionBus()
        dbus_notify_proxy = bus.get_object(DBus.SERVICE_NOTIFICATIONS, DBus.PATH_NOTIFICATIONS)
        dbus_notify_interface = dbus.Interface(dbus_notify_proxy, DBus.INTERFACE_NOTIFICATIONS)
        dbus_notify_interface.Notify(app_name, id_num_to_replace, icon,
                                     title, text, actions_list, hint, time)

class DBus:
    """
    Shell class for DBus-related functions.
    """
    SERVICE_BT = "org.bluez"
    INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties"
    INTERFACE_DEVICE = "org.bluez.Device1"

    SIGNAL_PROPERTIESCHANGED = "PropertiesChanged"

    SERVICE_NOTIFICATIONS = "org.freedesktop.Notifications"
    PATH_NOTIFICATIONS = "/org/freedesktop/Notifications"
    INTERFACE_NOTIFICATIONS = "org.freedesktop.Notifications"


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
        service = DBus.SERVICE_BT.replace('.', '/')
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
        raise Exception("Sink device not found! (Was searching for \"%s\")" % description)

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

    @staticmethod
    def locate_sink_device(pulse_conn, prefix):
        """
        Find an appropraite sink device to use as output.
        :param devices:
        :return:
        """
        for dev in pulse_conn.sink_list():
            if dev.name.startswith(prefix):
                return dev

        raise Exception("Could not find an appropriate output device (prefix \"%s\")." % prefix)

    @staticmethod
    def is_bt_active(pulse_conn, name):
        """
        Return a boolean indicating if our BT device is active.
        :param pulse_conn: Pulse connection object.
        :param name: Device name to check for.
        :return: Boolean
        """
        out_dev_name = Pulse.locate_sink_device(pulse_conn, "ladspa_output").description
        logging.info("Current output description is \"%s\"" % out_dev_name)
        if name in out_dev_name:
            return True
        return False


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
        self.dbus_bt_dev_proxy = bus.get_object(DBus.SERVICE_BT,
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
        try:
            return self.dbus_bt_dev_properties.Get(DBus.INTERFACE_DEVICE, property)
        except Exception as e:
            logging.error("Could not retrieve property '%s' on '%s'. Error \"%s\"" % (property, DBus.INTERFACE_DEVICE, e))

    def manage_connection(self, conn_state):
        """
        Perform connection or disconnection actions from an event.
        :param conn_state: Boolean of whether the device was connected or not.
        :return: None
        """
        with PulseLib('maxime-manage_connection') as pulse:
            # @TODO Make this not static
            ladspa_dev = Pulse.get_sink_input_device(pulse, "LADSPA Stream")

            # We default to speakers, and override with headphones
            target_device = Pulse.locate_sink_device(pulse, "alsa_output")
            if conn_state is True:
                # We need to a wait a few seconds for Pulse to catch up
                App.send_notification("Connecting to %s..." % self.get_bt_dev_property('Name'), "audio-headphones-bluetooth")
                time.sleep(4)
                try:
                    target_device = Pulse.get_sink_device(pulse, self.get_bt_dev_property('Name'))
                except Exception:
                    logging.error("Failed to find connected sink.")
                    return

            logging.info("Target device is \"%s\"" % target_device.description)

            # Tell Pulse to move the stream to our target device
            Pulse.move_input(pulse, ladspa_dev, target_device)

        # @TODO This should probably deal with errors, but until then...
        # Send notification
        icon = "audio-speakers"
        if conn_state is True:
            icon = "audio-headphones-bluetooth"
        text = "Connected to %s" % target_device.description
        App.send_notification(text, icon)
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
    if args.connect or args.disconnect or args.toggle:
        App.log_angry(logging.WARN, "Simulating an event. DBus will not monitor.")

        # Test if the user is paying attention
        if args.connect and args.disconnect:
            App.log_angry(logging.ERROR, "You cannot specify both connect and disconnect")
            if args.toggle:
                App.log_angry(logging.ERROR, "You cannot specify connect/disconnect and toggle")
                exit(1)

        # Perform
        if args.connect:
            ar._dbus_handler(DBus.INTERFACE_DEVICE, {"Connected": True}, None)
        if args.disconnect:
            ar._dbus_handler(DBus.INTERFACE_DEVICE, {"Connected": False}, None)
        if args.toggle:
            # Detect whether we're on BT device or not and do the opposite.
            with PulseLib('maxime-toggle_connection') as pulse:
                current_state = Pulse.is_bt_active(pulse, ar.get_bt_dev_property('Name'))
                if current_state:
                    # Disconnect
                    ar._dbus_handler(DBus.INTERFACE_DEVICE, {"Connected": False},
                                     None)
                else:
                    # Connect
                    ar._dbus_handler(DBus.INTERFACE_DEVICE, {"Connected": True},
                                     None)

        # Done with our simulations.
        App.log_angry(logging.WARN, "Simulation complete!")
        exit()

    # DBus event loop. Listen to the sounds....
    loop_msg = "Started listening for BT audio devices."
    App.send_notification(loop_msg, "audio-card")
    dbus_loop = GLib.MainLoop()
    dbus_loop.run()


def test():
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

    with PulseLib('maxime-manage') as pulse:
        pass


if __name__ == "__main__":
    main()
    #test()
