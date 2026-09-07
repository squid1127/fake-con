"""Pairing agent for the fake-con server."""

import threading

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from ..models.constants import AGENT_CAPABILITY, AGENT_PATH, DBUS_INTERFACE_AGENT


class _Agent(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, AGENT_PATH)

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="", out_signature="")
    def Release(self):
        # BlueZ requires this callback when the agent is released.
        pass

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        return "0000"

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        # The display-only callback needs no response.
        pass

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        return dbus.UInt32(0)

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        # The display-only callback needs no response.
        pass

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        # Returning successfully accepts the confirmation automatically.
        pass

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        # Returning successfully authorizes the pairing request.
        pass

    @dbus.service.method(DBUS_INTERFACE_AGENT, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        # Returning successfully authorizes the HID service.
        pass


class PairingAgent:
    """Register a default BlueZ agent that automatically accepts pairing."""

    def __init__(self):
        self._ready = threading.Event()
        self._error = None
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._loop = None
        self._bus = None
        self._agent = None
        self._thread.start()
        self._ready.wait()
        if self._error is not None:
            raise self._error

    def _run(self):
        try:
            DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SystemBus()
            self._agent = _Agent(self._bus)
            manager = dbus.Interface(
                self._bus.get_object("org.bluez", "/org/bluez"),
                "org.bluez.AgentManager1",
            )
            manager.RegisterAgent(AGENT_PATH, AGENT_CAPABILITY)
            manager.RequestDefaultAgent(AGENT_PATH)
            self._loop = GLib.MainLoop()
        except Exception as error:
            self._error = error
        finally:
            self._ready.set()

        if self._loop is not None:
            self._loop.run()

    def close(self):
        """Unregister the agent and stop its D-Bus loop."""
        if self._loop is None or self._closed:
            return
        self._closed = True

        def stop():
            manager = dbus.Interface(
                self._bus.get_object("org.bluez", "/org/bluez"),
                "org.bluez.AgentManager1",
            )
            try:
                manager.UnregisterAgent(AGENT_PATH)
            finally:
                self._loop.quit()

        GLib.idle_add(stop)
        self._thread.join()
