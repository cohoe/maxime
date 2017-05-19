Maxime
======

A utility for sanely utilizing Bluetooth headphones with PulseAudio.

## Background
A friend of mine (Maxime) worked at Bose and got me a pair of QC35 heaphones.
Spoiler alert: They're pretty great! Unfortunately three words that still
cause old unix-beards blood pressure to rise: Linux, Bluetooth, Audio. Turns
out this is still true.

Fedora 25 (at the time of this writing) supports Bluetooth audio devices
out of the box, so getting audio out of them is pretty easy. But to
complicate things, I use the LADSPA Equailizer Plugin to do some system-wide
EQ (shut up all your audiophilites, I truly do not care). The plugin requires
defining a master sink in the configuration file. This hinder any automatic
switching between devices as the headphones come on and off.

This utility is built to deal with that case.

## Primary Features
* Automatic switching to/from headphones on connect.
* Desktop notifications

## Under the Hood
Maxime listens to DBus for events, particularly when the headphones
(dis)connect. It will then determine which outputs (only the EQ right now) 
it needs to reroute to (or from) the headphones.

## Installation
1) Copy the ``maxime.ini.example`` to ``~/.config/maxime.ini`` and edit appropriately
2) Copy the ``maxime.desktop`` to ``~/.config/autostart/`` (If you want it to start on boot)
3) Copy the ``maxime.py`` to ``/usr/local/bin/maxime.py``

You can put it whever you want, just check the path in the .desktop file.

By default it will log to ``/var/tmp/maxime_$USER.log``.

## Buttons
Since the multi-function button is pretty useless on Linux, I'm going to
take its functions and use them for something useful.
* Single-tap (XF86AudioPlay): Mute
* Double-tap (XF86AudioNext): Switch to speakers
* Triple-tap (XF86AudioPrev): Force-reconnect

See [this repo](https://github.com/cohoe/workstation/blob/master/roles/xfce/tasks/keyboard.yml) for implementation.

## ToDo
* Does not error when device is not present. Should either barf or attempt to connect for you.
* Errors should produce a notification
* Switching profiles should reconnect
