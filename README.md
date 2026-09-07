# fake-con

A "fork" of [joycontrol](https://github.com/Poohl/joycontrol) since the original project was not working for some reason.

## Rev2

A complete rewrite of the original project, mainly to force it to be properly async and typed better, and because looking at the original code gave me a headache.

## Current Features

- Emulates a Pro Controller over Bluetooth Classic
- Requires root privileges on a linux to manipulate the Bluetooth stack and open a raw socket.
- Python API for scripting inputs

## Planned Features

- Standalone CLI
- Built-in keyboard and mouse remapping
- Macro system for automating inputs
- Support for Joy-Con and other controller types (they don't work yet)
