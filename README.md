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

## Setup

It's a standard poetry project

```bash
git clone https://github.com/squid1127/fake-con.git
cd fake-con
poetry install
```

API docs coming soon (never)

### Prerequisites

You need to have the following installed on your system:

- `dbus-python`
- `bluez` (the bluetooth stack for linux)
- `bluez-deprecated_tools` (for `hciconfig`) (I'll try to fix this sometime)

This project has been tested on Arch linux across two devices, both work fine, although your experience may vary depending on your bluetooth adapter and linux distribution.

### Bluetooth Service Configuration

WARNING! This will prevent you from using bluetooth input devices.

The bluetooth service must be reconfigured to restrict input plugins

```bash
sudo systemctl edit bluetooth
```

Then add the following lines to the `[Service]` section:

```toml
### Editing /etc/systemd/system/bluetooth.service.d/override.conf

[Service]
ExecStart=
ExecStart=/usr/lib/bluetooth/bluetoothd -C -P sap,input,avrcp
```

Restart systemd and the bluetooth service:

```bash
sudo systemctl daemon-reload && sudo systemctl restart bluetooth
```

To go back, you can restore the original configuration by running:

```bash
sudo systemctl revert bluetooth && sudo systemctl daemon-reload && sudo systemctl restart bluetooth
```
