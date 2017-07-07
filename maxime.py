#!/usr/bin/env python

import dbus
import ConfigParser
import os
import argparse
import logging
import time
import pexpect
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from pulsectl import Pulse as PulseLib

# @TODO
# Comments

# These first two classes (BluetoothctlError and Bluetoothctl were adapted from
# Egor Fedorov's ReachView project. The GPLv3 license of this code is compatible with
# the Apache license of my project.

# BEGIN LICENSE OF REACHVIEW CODE
# ReachView code is placed under the GPL license.
# Written by Egor Fedorov (egor.fedorov@emlid.com)
# Copyright (c) 2015, Emlid Limited
# All rights reserved.

# If you are interested in using ReachView code as a part of a
# closed source project, please contact Emlid Limited (info@emlid.com).

# This file is part of ReachView.
# END LICENSE OF REACHVIEW CODE

class BluetoothctlError(Exception):
    """This exception is raised, when bluetoothctl fails to start."""
    pass


class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""

    def __init__(self):
        self.child = pexpect.spawn("bluetoothctl", echo=False)

    def get_output(self, command, pause=0, prompt="bluetooth"):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.child.send(command + "\n")
        time.sleep(pause)
        start_failed = self.child.expect([prompt, pexpect.EOF])

        if start_failed:
            raise BluetoothctlError("Bluetoothctl failed after running " + command)

        return self.child.before.split("\r\n")

    def get_device_info(self, mac_address):
        """Get device info by mac address."""
        try:
            out = self.get_output("info " + mac_address)
        except BluetoothctlError, e:
            print(e)
            return None
        else:
            return out

    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        try:
            out = self.get_output("connect " + mac_address, 2)
        except BluetoothctlError, e:
            print(e)
            return None
        else:
            res = self.child.expect(["Failed to connect", "Connection successful", pexpect.EOF])
            success = True if res == 1 else False
            return success

    def disconnect(self, mac_address, prompt):
        """Try to disconnect to a device by mac address."""
        try:
            out = self.get_output("disconnect " + mac_address, 2, prompt=prompt)
        except BluetoothctlError, e:
            print(e)
            return None
        else:
            res = self.child.expect(["Failed to disconnect", "Successful disconnected", pexpect.EOF])
            success = True if res == 1 else False
            return success

class Maxime:
    """
    Main application logic class.
    """
    MODE_ROUTE = "route"
    MODE_CONNECT = "connect"
    MODE_DISCONNECT = "disconnect"
    MODE_LISTEN = "listen"
    MODE_DAEMON = "daemon"
    MODE_TOGGLE = "toggle"
    MODE_STATUS = "status"
    MODE_RESYNC = "resync"
    MODE_RECONNECT = "reconnect"

    ROUTE_SPEAKERS = "speakers"
    ROUTE_HEADSET = "headset"
    ROUTE_WIRELESS = "wireless"

    def __init__(self):
        """
        Constructor
        """
        # CLI Args
        self.args = self._setup_args(self)

        # Config File
        config_file_path = self._get_config_file_path(self)
        self.config = self._read_config_file(self, config_file_path)
        self._validate_config(self)

        # Logging
        self._setup_logging(self)

        # Program mode
        # This cannot run until we have setup logging!
        self.mode = None
        self._validate_args()

    @staticmethod
    def _validate_config(self):
        """
        Validate the input from a configuration file.
        :param self: 
        :return: 
        """
        pass

    @staticmethod
    def _setup_args(self):
        """
        Read arguments from the CLI.
        :return: ArgParse object.
        """
        description = "Bluetooth/Pulse audio routing manager."
        epilog = "Written by Grant Cohoe (https://grantcohoe.com)"

        parser = argparse.ArgumentParser(description=description, epilog=epilog)
        parser.add_argument('-c', '--config', type=str,
                            default='~/.config/maxime.ini',
                            help='path to configuration file (defaults to ~/.config/maxime.ini)')

        parser.add_argument('-d', '--debug',
                             default=False,
                             action='store_true',
                             help='enable debug logging')

        parser.add_argument('-l', '--logfile', type=str,
                            default=None,
                            help='path to log file (otherwise logs to STDOUT)')

        parser.add_argument('--route',
                            default=None,
                            help='send audio to a device (wireless, headset, speakers)')

        parser.add_argument('--connect',
                            default=False,
                            action='store_true',
                            help='trigger a wireless connect event')

        parser.add_argument('--disconnect',
                            default=False,
                            action='store_true',
                            help='trigger a wireless disconnect event')

        parser.add_argument('--listen',
                            default=False,
                            action='store_true',
                            help='Listen for events but do not act on them')

        parser.add_argument('--toggle',
                            default=False,
                            action='store_true',
                            help='toggle between speakers/wireless')

        parser.add_argument('--resync',
                            default=False,
                            action='store_true',
                            help='resync the wireless device')

        parser.add_argument('--reconnect',
                            default=False,
                            action='store_true',
                            help='reconnect to the wireless device')

        parser.add_argument('--status',
                            default=False,
                            action='store_true',
                            help='show the current output device')

        return parser.parse_args()

    @staticmethod
    def _read_config_file(self, file_path):
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
    def _get_config_file_path(self):
        """
        Return a normalized path to our configuration file.
        :return: String of the path to our config file.
        """
        # Normalize our path
        file_path = self.args.config
        file_path = os.path.expanduser(file_path)
        file_path = os.path.abspath(file_path)

        # Test if the file exists
        if os.path.exists(file_path) is False:
            self.exit_err("Config file at '%s' does not exist!" % file_path)

        return file_path

    @staticmethod
    def _setup_logging(self):
        """
        Setup the logging facility.
        :return: None
        """
        log_level = logging.INFO

        if self.args.debug is True:
            log_level = logging.DEBUG

        # You can only call this once, or others will be a noop.
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                            datefmt='%m/%d/%Y %H:%M:%S',
                            filename=self.args.logfile,
                            level=log_level)

        logging.debug("Starting logging facility")

    @staticmethod
    def exit_err(message):
        """
        Exit with an error message.
        :param message: The message to print.
        :return: None
        """
        logging.error(message)
        logging.info("Exiting with error.")
        exit(1)
        
    def _validate_args(self):
        """
        Figure out what we should be doing based on CLI args
        :return: 
        """
        # Determine what we're going to do
        if self.args.status is True:
            if self.args.connect is True or self.args.disconnect is True or self.args.resync is True or self.args.reconnect is True:
                self.exit_err("You cannot specify --status and --connect/--disconnect/--resync/--reconnect")
            if self.args.route is not None:
                self.exit_err("You cannot specify --status and --route")
            if self.args.toggle is True:
                self.exit_err("You cannot specify --status and --toggle")
            if self.args.listen is True:
                self.exit_err("You cannot specify --status and --listen")
            self._set_mode(Maxime.MODE_STATUS)
            return

        if self.args.route is not None:
            if self.args.toggle is True:
                self.exit_err("You cannot specify --route and --toggle")
            if self.args.connect is True or self.args.disconnect is True or self.args.listen is True or self.args.resync is True or self.args.reconnect is True:
                self.exit_err("You cannot specify --route and --connect/--disconnect/--listen/--resync/--reconnect")

            self._set_mode(Maxime.MODE_ROUTE)
            return

        if self.args.connect is True:
            if self.args.disconnect is True:
                self.exit_err("You cannot specify both --connect and --disconnect.")
            if self.args.toggle is True:
                self.exit_err("You cannot specify --connect and --toggle")
            if self.args.resync is True:
                self.exit_err("You cannot specify both --connect and --resync.")
            if self.args.reconnect is True:
                self.exit_err("You cannot specify both --connect and --reconect.")

            self._set_mode(Maxime.MODE_CONNECT)
            return
        elif self.args.disconnect is True:
            if self.args.toggle is True:
                self.exit_err("You cannot specify --disconnect and --toggle")
            if self.args.resync is True:
                self.exit_err("You cannot specify --disconnect and --resync")
            if self.args.reconnect is True:
                self.exit_err("You cannot specify --disconnect and --reconnect")
            self._set_mode(Maxime.MODE_DISCONNECT)
            return

        if self.args.toggle is True:
            self._set_mode(Maxime.MODE_TOGGLE)
            return

        if self.args.resync is True:
            if self.args.reconnect is True:
                self.exit_err("--reconnect implies --resync. Only specify one or the other.")
            self._set_mode(Maxime.MODE_RESYNC)
            return

        if self.args.reconnect is True:
            if self.args.resync is True:
                self.exit_err("--reconnect implies --resync. Only specify one or the other.")
            self._set_mode(Maxime.MODE_RECONNECT)
            return

        logging.info("Starting daemon mode.")
        if self.args.listen is True:
            self._set_mode(Maxime.MODE_LISTEN)
            return

        self._set_mode(Maxime.MODE_DAEMON)
        return

    def _set_mode(self, mode):
        """
        Set the run mode of the program.
        :return: 
        """
        logging.debug("Setting mode to %s" % mode)
        self.mode = mode

    def route(self, pulse):
        """
        Route audio stream.
        :return: 
        """
        destination = self.args.route.lower()
        if destination == self.ROUTE_WIRELESS:
            pulse.activate_wireless(conn_event=False)
        elif destination == self.ROUTE_HEADSET:
            pulse.activate_headset(conn_event=False)
        elif destination == self.ROUTE_SPEAKERS:
            pulse.activate_speakers(conn_event=False)
        else:
            self.exit_err("Routing destination must be speakers|wireless|headset")

    def toggle(self, pulse):
        """
        Toggle between wireless and speakers.
        :param pulse: 
        :return: 
        """
        ladspa_device = pulse._lookup_sink_output_device("LADSPA Plugin Multiband EQ")
        logging.debug("LADSPA device is \"%s\"" % ladspa_device.description)
        if pulse.bt_device.output_device in ladspa_device.description:
            logging.info("Current output is wireless. Switching to speakers.")
            pulse.activate_speakers(conn_event=False)
        else:
            logging.info("Current output is not wireless. Switching to wireless.")
            pulse.activate_wireless(conn_event=False)

    def status(self, pulse):
        """
        Show the current output device.
        :param pulse: 
        :return: 
        """
        ladspa_device = pulse._lookup_sink_output_device("LADSPA Plugin Multiband EQ")
        logging.debug("LADSPA device is \"%s\"" % ladspa_device.description)
        output_string = ladspa_device.description.replace("LADSPA Plugin Multiband EQ on ", "")
        DBusHelper.send_notification("Current output is \"%s\"" % output_string)

    def connect(self, bt_device):
        """
        Connect to a Bluetooth device
        :param bt_device: 
        :return: 
        """
        logging.debug("Connecting to \"%s\" at \"%s\"" % (bt_device.output_device, bt_device.mac))
        bluez = Bluetoothctl()
        device_info = bluez.get_device_info(bt_device.mac)

        # Figure out if we're already connected to the device.
        prefix = "Connected: "
        raw_is_connected = None
        for line in device_info:
            if prefix in line:
                raw_is_connected = line.strip().replace(prefix, "").upper()
                break

        # Parse to Boolean
        if 'NO' in raw_is_connected:
            logging.debug("Wireless device is not connected.")
            is_connected = False
        elif 'YES' in raw_is_connected:
            logging.debug("Wireless device is connected.")
            is_connected = True
        else:
            logging.error("Could not determine connected state.")
            return

        # Connect
        if is_connected is False:
            bluez.connect(mac_address=bt_device.mac)
            logging.info("Connected to \"%s\" at \"%s\"" % (bt_device.output_device, bt_device.mac))
            DBusHelper.send_notification("Connected to %s." % bt_device.output_device, icon=DBusHelper.ICON_WIRELESS)

        logging.debug("Device was already connected. Not doing anything...")

    def disconnect(self, bt_device):
        """
        Disconnect to a Bluetooth device
        :param bt_device: 
        :return: 
        """
        logging.debug("Disconnecting \"%s\" at \"%s\"" % (bt_device.output_device, bt_device.mac))
        bluez = Bluetoothctl()
        bluez.disconnect(mac_address=bt_device.mac, prompt=bt_device.output_device)
        logging.info("Disconnected from \"%s\" at \"%s\"" % (bt_device.output_device, bt_device.mac))
        DBusHelper.send_notification("Disconnected from %s." % bt_device.output_device, icon=DBusHelper.ICON_WIRELESS)

    def resync(self, pulse):
        """
        Resync audio stream to the bluetooth device. This can happen when you
        encounter some signal problems by walking too far away.
        :param pulse: PulseAudio wrapper. 
        :return: 
        """
        logging.debug("Resyncing wireless")
        pulse.resync_wireless()

    def reconnect(self, bt_device):
        """
        Reconnect
        :param bt_device: 
        :return: 
        """
        logging.debug("Reconnecting to \"%s\" at \"%s\"" % (bt_device.output_device, bt_device.mac))
        self.disconnect(bt_device)
        # Dunno if this will actually be needed. Will see how it behaves
        # time.sleep(1)
        self.connect(bt_device)

class DBusHelper:
    """
    Shell class for DBus-related functions.
    """
    # Notifications
    SERVICE_NOTIFICATIONS = "org.freedesktop.Notifications"
    PATH_NOTIFICATIONS = "/org/freedesktop/Notifications"
    INTERFACE_NOTIFICATIONS = "org.freedesktop.Notifications"

    # Icons
    ICON_WIRELESS = "audio-headphones-bluetooth"
    ICON_GENERIC = "audio-card"
    ICON_SPEAKERS = "audio-speakers"
    ICON_HEADSET = "audio-headset"

    @staticmethod
    def send_notification(text, icon='audio-card', time=5000, actions_list=''):
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
        hint = ''

        # Create the objects and send!
        bus = dbus.SessionBus()
        dbus_notify_proxy = bus.get_object(DBusHelper.SERVICE_NOTIFICATIONS, DBusHelper.PATH_NOTIFICATIONS)
        dbus_notify_interface = dbus.Interface(dbus_notify_proxy, DBusHelper.INTERFACE_NOTIFICATIONS)
        dbus_notify_interface.Notify(app_name, id_num_to_replace, icon,
                                     title, text, actions_list, hint, time)
        bus.close()
        logging.debug("Sent notification to DBus: %s" % text)


class GenericAudioDevice:
    def __init__(self, config, mode):
        self.input_device = config.get(mode, 'input_device')
        self.output_device = config.get(mode, 'output_device')
        

class BluetoothDevice:
    """
    Bluetooth specific crap.
    """
    DBUS_SERVICE = "org.bluez"
    DBUS_INTERFACE_DEVICE = "org.bluez.Device1"

    def __init__(self, config):
        """
        Constructor
        :param config: Validated ConfigParser object 
        """
        self.adapter = config.get('bluetooth', 'adapter')
        self.mac = config.get('bluetooth', 'device_mac')
        self.dbus_object_path = self._get_dbus_device_object_path(self.adapter, self.mac)
        self.proxy = None
        self.properties = None
        self.output_device = config.get('bluetooth', 'output_device')

    @staticmethod
    def _get_normal_mac(mac):
        """
        Return a DBus-normalized MAC address.
        :param mac: MAC address to normalize
        :return: A DBus/BlueZ compatible MAC address
        """
        return mac.replace(':','_')

    def _get_dbus_device_object_path(self, adapter, mac):
        """
        Return the DBus object path of a particular device.
        :param adapter: The Bluetooth interface.
        :param mac: The normalized MAC address.
        :return: A string of the device path.
        """
        mac = self._get_normal_mac(mac)
        service = self.DBUS_SERVICE.replace('.', '/')
        obj_path = "/%s/%s/dev_%s" % (service, adapter, mac)

        return obj_path

    def get_property(self, key):
        """
        Return a device property from DBus.
        :param key: 
        :return: 
        """
        try:
            return self.properties.Get(self.DBUS_INTERFACE_DEVICE, key)
        except Exception as e:
            logging.error("Could not retrieve property '%s' on '%s'. Error \"%s\"" % (key, self.DBUS_INTERFACE_DEVICE, e))


class DBusListener:
    """
    Class to deal with DBus events.
    """
    # Static vars for DBus properties and interfaces
    INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties"
    SIGNAL_PROPERTIESCHANGED = "PropertiesChanged"

    def __init__(self, device, pulse):
        """
        Constructor
        """
        DBusGMainLoop(set_as_default=True)
        proxy, properties = self._setup_dbus(device)
        device.proxy = proxy
        device.properties = properties
        self.device = device
        self.pulse = pulse

    def _setup_dbus(self, device):
        """
        Setup our DBus proxy object and properties interface. The proxy object
        is used to perform operations against a specific DBus object.
        The properties interface is our templated way into viewing properties
        about the device we just (dis)connected.
        :return: None
        """
        bus = dbus.SystemBus()
        bt_dev_proxy = bus.get_object(BluetoothDevice.DBUS_SERVICE, device.dbus_object_path)
        bt_dev_proxy.connect_to_signal(self.SIGNAL_PROPERTIESCHANGED,
                                       self._bluetooth_signal_handler,
                                       dbus_interface=self.INTERFACE_PROPERTIES)
        bt_dev_properties = dbus.Interface(bt_dev_proxy,
                                           dbus_interface=self.INTERFACE_PROPERTIES)

        return bt_dev_proxy, bt_dev_properties

    def listen(self):
        """
        Listen for events and do stuff when they happen!
        :return: 
        """
        loop_msg = "Started listening for BT audio devices."
        DBusHelper.send_notification(text=loop_msg, icon="audio-card")
        dbus_loop = GLib.MainLoop()
        dbus_loop.run()

    def _bluetooth_signal_handler(self, interface, changed_properties, signature):
        """
        Event handler for a change in a Bluetooth device state.
        :param interface: String of the DBus interface.
        :param changed_properties: Dictionary of the properties that changed.
        :param signature: String of something that I don't care about.
        :return: None
        """
        logging.debug("%s: Change detected." % interface)

        # Right now I only care about device connectivity
        if interface != BluetoothDevice.DBUS_INTERFACE_DEVICE:
            logging.debug("%s: Ignoring change." % interface)
            return

        # Test for the appropriate key in the messages we will get
        try:
            connected = bool(changed_properties['Connected'])
        except KeyError:
            # Ignore a ServicesResolved message
            try:
                bool(changed_properties['ServicesResolved'])
                logging.debug("%s: Ignoring ServicesResolved." % interface)
                return
            except Exception:
                logging.error("%s: Some weird error occurred "
                              "(and it wasnt ServicesResolved)." % interface)
                return
        except Exception:
            logging.error("%s: Some weird error occurred." % interface)
            return

        # Deal with the connection state
        logging.info("%s: Connected -> %s" % (interface, connected))
        self.pulse.manage_connection(connected)


class PulseAudio:
    """
    PulseAudio connection
    """
    BT_CARD_PREFIX = "bluez_card"
    BT_PROFILE_A2DP = "a2dp_sink"
    BT_PROFILE_HSP = "headset_head_unit"

    def __init__(self, config, bt_device, sp_device, hs_device):
        """
        Constructor for PulseAudio connection.
        :param config: 
        """
        self.config = config
        self.pulse_conn = PulseLib('maxime-manage_connection')
        self.ladspa_device = self._lookup_sink_input_device("LADSPA Stream")
        self.bt_device = bt_device
        self.hs_device = hs_device
        self.sp_device = sp_device

    def activate_wireless(self, conn_event=True):
        """
        Activate the wireless device. If it's a (dis)connect event,
        also mute the speakers so we don't blast audio.
        :param conn_event:
        :return:
        """
        logging.debug("Activating wireless.")

        device_name = self.bt_device.output_device

        # We need to a wait a few seconds for Pulse to catch up
        first_run = True
        while True:
            try:
                target_device = self._lookup_sink_output_device(device_name)
                break
            except Exception as e:
                if "not found" in e.message:
                    if first_run is True:
                        DBusHelper.send_notification("Routing to %s..." % device_name, DBusHelper.ICON_WIRELESS)
                        first_run = False
                    logging.debug("Sleeping for 1 second so that Pulse can sort itself out.")
                    time.sleep(1)
                logging.error("Unable to find wireless device.")

        logging.debug("Target device is \"%s\"" % target_device.description)

        # This event check is used to make sure the headphones being
        # (un)intentionally disconnected don't suddenly blast loud noises
        # out of the speakers.
        if conn_event is True:
            logging.debug("This is a connection event. Unmuting wireless.")
            self._unmute(self.ladspa_device)
        self._move_output(self.ladspa_device, target_device, DBusHelper.ICON_WIRELESS)

    def resync_wireless(self):
        """
        Resync a wireless stream.
        :return: 
        """
        # This uses a card identifer rather than a device. No idea if that matters.
        card_dev = self._lookup_card(self.BT_CARD_PREFIX)

        # There is no direct way to resync a stream to the wireless
        # device, but the folks on this here forum have found a
        # way to make it sorta work.
        # https://askubuntu.com/questions/145935/get-rid-of-0-5s-latency-when-playing-audio-over-bluetooth-with-a2dp
        logging.debug("Setting profile of \"%s\" to \"%s\"" % (card_dev.name, self.BT_PROFILE_HSP))
        DBusHelper.send_notification("Resyncing Bluetooth audio stream.", icon=DBusHelper.ICON_GENERIC)
        self.pulse_conn.card_profile_set(card_dev, self.BT_PROFILE_HSP)
        # We need to let Pulse catch its breath.
        time.sleep(1)
        logging.debug("Setting profile of \"%s\" to \"%s\"" % (card_dev.name, self.BT_PROFILE_A2DP))
        self.pulse_conn.card_profile_set(card_dev, self.BT_PROFILE_A2DP)

        # Switching profiles makes the sinks change, so we need to reroute.
        # @TODO might need to switch conn_even to true if there are mute issues
        self.activate_wireless(conn_event=False)

    def activate_headset(self, conn_event=True):
        """
        Activate the headset device.
        :param conn_event:
        :return:
        """
        logging.debug("Activating headset.")

        out_device_name = self.hs_device.output_device
        in_device_name = self.hs_device.input_device
        try:
            target_output_device = self._lookup_sink_output_device(out_device_name)
            target_input_device = self._lookup_source_device(in_device_name)
        except:
            return

        logging.debug("Target output device is \"%s\"" % target_output_device.description)
        self._move_output(self.ladspa_device, target_output_device, DBusHelper.ICON_HEADSET)
        self._set_input(target_input_device)

    def activate_speakers(self, conn_event=True):
        logging.debug("Activating speakers.")

        device_name = self.sp_device.output_device
        target_device = self._lookup_sink_output_device(device_name)
        logging.debug("Target device is \"%s\"" % target_device.description)

        # This event check is used to make sure the headphones being
        # (un)intentionally disconnected don't suddenly blast loud noises
        # out of the speakers.
        if conn_event is True:
            logging.debug("This is a connection event. Muting speakers.")
            self._mute(self.ladspa_device)
        self._move_output(self.ladspa_device, target_device, DBusHelper.ICON_SPEAKERS)

    def _lookup_sink_input_device(self, name):
        """
        Return a Pulse sink input device. These are the items in the "Playback"
        tab in pavucontrol.
        :param name: 
        :return: 
        """
        for device in self.pulse_conn.sink_input_list():
            if device.name == name:
                return device

        logging.error("Sink Input device not found! (Was searching for \"%s\")" % name)

    def _lookup_sink_output_device(self, description):
        """
        Find a Pulse Sink device. These are what show up in the "Output Devices"
        tab in pavucontrol.
        :param prefix: 
        :param description: 
        :return: 
        """
        for device in self.pulse_conn.sink_list():
            if device.description.startswith(description):
                return device

        logging.error("Sink Input device not found! (Was searching for \"%s\")" % description)
        raise Exception("Sink Input device not found! (Was searching for \"%s\")" % description)

    def _lookup_source_device(self, description):
        """
        Find a Pulse source device. These are what show up in the "Input Devices"
        tab in pavucontrol.
        :param prefix: 
        :param description: 
        :return: 
        """
        for device in self.pulse_conn.source_list():
            if device.description == description:
                return device

        logging.error("Source device not found! (Was searching for \"%s\")" % description)
        raise Exception("Source device not found! (Was searching for \"%s\")" % description)

    def _lookup_card(self, name):
        """
        Find a Pulse card. This is the equivalent of pacmd list-cards.
        :param name: The string to search for in the name of the card.
        :return: 
        """
        for device in self.pulse_conn.card_list():
            if name in device.name:
                return device
        logging.error("Card \"%s\" not found!" % name)
        raise Exception("Card \"%s\" not found!" % name)

    def _move_output(self, source, destination, icon):
        """
        Move a Pulse stream
        :param source: Source device that we want to redirect.
        :param destination: Target device that we want to hear from.
        :return: None
        """
        logging.info("Moving stream of \"%s\" to \"%s\"" % (source.name, destination.description))
        self.pulse_conn.sink_input_move(source.index, destination.index)

        text = "Routed %s to %s" % (source.name, destination.description)
        DBusHelper.send_notification(text, icon)

    def _set_input(self, device):
        """
        Set Pulse input device.
        :param device: 
        :return: 
        """
        logging.info("Setting default source device to \"%s\"" % device.description)
        self.pulse_conn.source_default_set(device.name)

    def manage_connection(self, conn_state):
        """
        Decide what to activate based on connection event
        :param conn_state: Boolean of whether the device was connected or not.
        :return: None
        """
        if conn_state is True:
            # Connection
            self.activate_wireless(conn_event=True)
        elif conn_state is False:
            # Disconnection
            self.activate_speakers(conn_event=True)

    def _mute(self, device):
        """
        Mute a sink device
        :param device:
        :return:
        """
        logging.debug("Muting device \"%s\"" % device.name)
        self.pulse_conn.sink_input_mute(device.index, True)

    def _unmute(self, device):
        """
        Unmute a sink input device.
        :param device:
        :return:
        """
        logging.debug("Unmuting device \"%s\"" % device.name)
        self.pulse_conn.sink_input_mute(device.index, False)


def main():
    """
    Main program logic. Wait for dbus events and go from there.
    """
    max = Maxime()
    logging.debug("Our mode is: %s" % max.mode)

    # @TODO This is hax
    # Setup PulseAudio
    bt_device = BluetoothDevice(max.config)
    sp_device = GenericAudioDevice(max.config, 'speakers')
    hs_device = GenericAudioDevice(max.config, 'headset')
    pulse = PulseAudio(max.config, bt_device, sp_device, hs_device)

    if max.mode == max.MODE_STATUS:
        max.status(pulse)
    elif max.mode == max.MODE_ROUTE:
        max.route(pulse)
    elif max.mode == max.MODE_TOGGLE:
        max.toggle(pulse)
    elif max.mode == max.MODE_CONNECT:
        max.connect(bt_device)
    elif max.mode == max.MODE_DISCONNECT:
        max.disconnect(bt_device)
    elif max.mode == max.MODE_RESYNC:
        max.resync(pulse)
    elif max.mode == max.MODE_RECONNECT:
        max.reconnect(bt_device)
    else:
        # Daemon Mode
        dbus_listener = DBusListener(bt_device, pulse)
        dbus_listener.listen()

    logging.debug("Exiting.")

if __name__ == "__main__":
    main()
