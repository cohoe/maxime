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

## Under the Hood
Maxime listens to DBus for events, particularly when the headphones
(dis)connect. It will then determine which outputs (only the EQ right now) 
it needs to reroute to (or from) the headphones.

## Extra Features
Since the multi-function button is pretty useless on Linux, I'm going to
take its functions and use them for something useful.
* Single-tap: Mute
* Double-tap: Switch to speakers
* Triple-tap: Force-reconnect
