"""Constants for the fake-con system."""

from importlib.resources import files

# Path to the SDP record XML file for the HID profile.
PROFILE_PATH = str(files(__package__) / ".." / "profile" / "sdp_record_hid.xml")

# Bluetooth socket options
BT_SECURITY = 4
BT_SECURITY_LOW = 1
DEVICE_CLASS_LEGACY = " 0x002508"

# Pairing Agent
AGENT_PATH = "/fake_con/agent"
AGENT_CAPABILITY = "DisplayYesNo"

# D-Bus constants
HID_UUID = "00001124-0000-1000-8000-00805f9b34fb"
HID_PATH = "/bluez/switch/hid"
SWITCH_NAME = "Nintendo Switch"
DBUS_NAME = "org.bluez"
DBUS_INTERFACE_OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
DBUS_INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties"
DBUS_INTERFACE_ADAPTER = "org.bluez.Adapter1"
DBUS_INTERFACE_DEVICE = "org.bluez.Device1"
DBUS_INTERFACE_AGENT = "org.bluez.Agent1"
DBUS_INTERFACE_PROFILE_MANAGER = "org.bluez.ProfileManager1"
