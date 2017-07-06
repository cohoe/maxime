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
complicate things, I use the LADSPA Equalizer Plugin to do some system-wide
EQ (shut up all your audiophilites, I truly do not care). The plugin requires
defining a master sink in the configuration file. This hinder any automatic
switching between devices as the headphones come on and off.

This utility is built to deal with that case.

## Primary Features
* Automatic switching to/from headphones on (dis)connect.
* Desktop notifications.
* Resync audio stream.

## Under the Hood
Maxime listens to DBus for events, particularly when the headphones
(dis)connect. It will then determine which outputs (only the EQ right now) 
it needs to reroute to (or from) the headphones.

Connect management uses a wrapper around bluetoothctl to manage the connection
state of the wireless device. You must have already paired and trusted your
device for this to work. Goes something like
```
~ # bluetoothctl
[bluetooth]# pair DE:AD:BE:EF:CA:FE
[bluetooth]# trust DE:AD:BE:EF:CA:FE
```

## Prerequisites
System stuff
* A Fedora-based linux box (it might work with others? idk)
* PulseAudio
* Bluez

The following python modules are needed (Fedora package names in ()'s):
* dbus (dbus-python)
* pexpect (python2-pexpect)
* gobject-base (python-gobject-base)
* pulsectl (No package available)

## Installation

1) Copy the ``maxime.ini.example`` to ``~/.config/maxime.ini`` and edit appropriately
2) Copy the ``maxime.desktop`` to ``~/.config/autostart/`` (If you want it to start on boot)
3) Copy the other desktop files to ``~/.local/share/applications``
3) Copy the ``maxime.py`` to ``/usr/local/bin/maxime.py``

You can put it wherever you want, just check the path in the .desktop file.

_Optional:_
The QC35's identify a computer by name, which with Linux defaults to the hostname. 
If your system has a FQDN as a hostname (ie, ``hostname`` spits out something like 
``foo.example.com``). This can be obnoxious because the onboard speech engine has
to say (or spell) out the entire name. You can shorten this by specifying a 
``PRETTY_HOSTNAME=something`` in ``/etc/machine-info`` and restarting the Bluetooth
service. See [this repo](https://github.com/cohoe/workstation/blob/master/roles/bluetooth/tasks/main.yml) for an example.

Note that if you have already paired/trusted the headphones you'll need to wipe them out
to change the registered name.

## Usage
```
usage: maxime.py [-h] [-c CONFIG] [-d] [-l LOGFILE] [--route ROUTE]
                 [--connect] [--disconnect] [--listen] [--toggle]
                 [--reconnect] [--status]

Bluetooth/Pulse audio routing manager.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        path to configuration file (defaults to
                        ~/.config/maxime.ini)
  -d, --debug           enable debug logging
  -l LOGFILE, --logfile LOGFILE
                        path to log file (otherwise logs to STDOUT)
  --route ROUTE         send audio to a device (wireless, headset, speakers)
  --connect             trigger a wireless connect event
  --disconnect          trigger a wireless disconnect event
  --listen              Listen for events but do not act on them
  --toggle              toggle between speakers/wireless
  --resync              resync the wireless audio stream
  --status              show the current output device
```

## Buttons
Since the multi-function button is pretty useless on Linux, I'm going to
take its functions and use them for something useful.
* Single-tap (XF86AudioPlay): Mute
* Double-tap (XF86AudioNext): Switch to speakers
* Triple-tap (XF86AudioPrev): Force-reconnect

See [this repo](https://github.com/cohoe/workstation/blob/master/roles/xfce/tasks/keyboard.yml) for implementation.

## Problems
### Crappy dial-up quality audio
Your system probably enabled the HSP "headset" profile instead of the A2DP "high quality audio".
You can change this by opening pavucontrol (Pulse Volume Control), going to the Configuration
tab and setting Profile for your device to "High Fidelity Playback (A2DP Sink)".

### Audio not in sync
Best thing to do is run ``maxime.py --resync`` and hope for the best. Maybe don't walk so far away
and/or re-orient your antenna. Bluetooth kinda sucks.

### No audio and/or controls not working
The QC35's can be connected to multiple devices at the same time. You probably have a device
that has taken precedence (usually the first one if you slide the BT switch on the headphones).
Unfortunately Bose has not given you a sane way to easily disconnect someone from the device
itself, so you have to do it from that device. ``maxime.py --disconnect``

### You have too many desktop shortcut files
Launchy doesnt deal with multiple entries in desktop files well. Sorry bro.

## ToDo
* Does not error when device is not present. Should either barf or attempt to connect for you.
* Errors should produce a notification
* Switching profiles should reconnect
* Specify wireless fallback device.
* Multiple speakers???
