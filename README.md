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
* Connect/Disconnect from headphones.
* Automatic switching to/from headphones on connect.
* Desktop notifications.

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

## Installation
1) Copy the ``maxime.ini.example`` to ``~/.config/maxime.ini`` and edit appropriately
2) Copy the ``maxime.desktop`` to ``~/.config/autostart/`` (If you want it to start on boot)
3) Copy the other desktop files to ``~/.local/share/applications``
3) Copy the ``maxime.py`` to ``/usr/local/bin/maxime.py``

You can put it whever you want, just check the path in the .desktop file.

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
tab and setting Profile for your device to "High Fidelity Playback (A2DP Sink)"

### Audio not in sync
Bluetooth sucks. What more can I tell you? Best thing to do is run ``maxime.py --reconnect``
and hope for the best.

### You have too many desktop shortcut files
Launchy doesnt deal with multiple entries in desktop files well. Sorry bro.

## ToDo
* Does not error when device is not present. Should either barf or attempt to connect for you.
* Errors should produce a notification
* Switching profiles should reconnect
