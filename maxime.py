#!/usr/bin/env python

import dbus
import ConfigParser
import os
import argparse
from dbus.mainloop.glib import DBusGMainLoop

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
                            metavar='config',
                            default='~/.config/maxime.ini',
                            help='path to configuration file')
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


def main():
    """
    Main program logic. Wait for dbus events and go from there.
    """
    # Parse command-line arguments
    args = App.read_args()

    # Parse config file
    config = App.read_config_file(App.get_config_file_path(args))
    # @TODO There will probably be more configuration options to deal with.

    print config.get('bluetooth', 'adapter')

    # DBus setup
    DBusGMainLoop(set_as_default=True)

if __name__ == "__main__":
    main()
