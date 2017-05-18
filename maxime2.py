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

# @TODO
# Move send_notification to DBus class and make it instantiable.
# Make App instantiable and move lots of main() to it's constructor.


class App:
    """
    Shell class for application methods (arguments, config, that sort of
    stuff).
    """

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


class Maxime:
    """
    Main application logic class.
    """
    MODE_ROUTE = "route"
    MODE_CONNECT = "connect"
    MODE_DISCONNECT = "disconnect"
    MODE_LISTEN = "listen"
    MODE_DAEMON = "daemon"

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

        logging.info("Starting logging facility")

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
        if self.args.route is not None:
            if self.args.connect is True or self.args.disconnect is True or self.args.listen is True:
                self.exit_err("You cannot specify --route and --connect/--disconnect/--listen")

            self._set_mode(Maxime.MODE_ROUTE)
            return

        if self.args.connect is True:
            if self.args.disconnect is True:
                self.exit_err("You cannot specify both --connect and --disconnect.")

            self._set_mode(Maxime.MODE_CONNECT)
            return

        elif self.args.disconnect is True:
            self._set_mode(Maxime.MODE_DISCONNECT)
            return
        else:
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




def main():
    """
    Main program logic. Wait for dbus events and go from there.
    """
    max = Maxime()
    logging.info("Our mode is: %s" % max.mode)


    logging.info("Reached the end, for now.")

if __name__ == "__main__":
    main()
