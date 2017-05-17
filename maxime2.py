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
    def setup_logging(debug, filepath):
        """
        Setup the logging facility.
        :param debug: Boolean of whether to be loud or not.
        :param filepath: Log file path.
        :return: None
        """

        # You can only call this once, or others will be a noop.
        if debug is True:
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

    @staticmethod
    def exit_err(message):
        """
        Exit with an error message.
        :param message: The message to print.
        :return: None
        """
        logging.error(message)
        exit(1)


def main():
    """
    Main program logic. Wait for dbus events and go from there.
    """
    # Parse command-line arguments
    args = App.read_args()

    # Setup configuration structures (Note: No logging can occur before
    # this otherwise it will break the output)
    config = App.read_config_file(App.get_config_file_path(args))
    App.setup_logging(args.debug, args.logfile)

    # Determine what we're going to do
    if args.route is not None:
        if args.connect is True or args.disconnect is True or args.listen is True:
            App.exit_err("You cannot specify --route and --connect/--disconnect/--listen")

        logging.info("Routing audio stream")
        # App code here

    if args.connect is True:
        if args.disconnect is True:
            App.exit_err("You cannot specify both --connect and --disconnect.")

        logging.info("Triggering a connection event.")
        # App code here

    elif args.disconnect is True:
        logging.info("Triggering a disconnection event.")
        # App code here

    else:
        logging.info("Starting daemon mode.")
        if args.listen is True:
            logging.info("Listening only")
        # App code here with conditionals for listen

    logging.info("Reached the end, for now.")

if __name__ == "__main__":
    main()
