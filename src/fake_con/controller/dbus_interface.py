"""
DBus Interface for the fake-con system.
"""

from logging import getLogger
from uuid import uuid4

from aiofiles import open as aio_open
from dbus import Boolean, Bus, Interface, String, SystemBus
from dbus.connection import ProxyObject

from ..models.config import FakeConConfig
from ..models.constants import (
    DBUS_INTERFACE_ADAPTER,
    DBUS_INTERFACE_DEVICE,
    DBUS_INTERFACE_OBJECT_MANAGER,
    DBUS_INTERFACE_PROFILE_MANAGER,
    DBUS_INTERFACE_PROPERTIES,
    DBUS_NAME,
    HID_PATH,
    HID_UUID,
    PROFILE_PATH,
    SWITCH_NAME,
)
from .utils import run_sync

logger = getLogger(__name__)


class DBusInterface:
    """DBus interface for the fake-con system."""

    def __init__(self, config: FakeConConfig, bus: Bus | None = None):
        """Initialize the DBus interface with the given bus.

        Args:
            config: The configuration for the fake-con system.
            bus: The DBus bus to use for communication.

        """
        self._bus = bus or SystemBus()
        self._config = config
        self._device: ProxyObject | None = None
        self._adapter: Interface | None = None
        self._properties: Interface | None = None

    async def auto(self):
        """Automatically discover the adapter and set it up."""
        await self.discover_adapter()
        await self.set_powered(True)
        await self.set_discoverable(True)
        await self.set_pairable(True)
        await self.set_alias(self._config.controller_type.device_name)
        await self.register_hid_profile()
        
        if await self.get_paired_devices():
            logger.warning(
                "There are already paired devices. Unpairing them..."
            )
            for device in await self.get_paired_devices():
                await self.remove_device(device)

        
    async def stop_advertising(self):
        """Stop advertising the controller."""
        await self.set_discoverable(False)
        await self.set_pairable(False)
        logger.info("Stopped advertising the controller.")

    async def get_address(self) -> str:
        """Get the Bluetooth address of the adapter.

        Returns:
            The Bluetooth address of the adapter.

        Raises:
            RuntimeError: If the adapter has not been discovered yet.
        """
        return await run_sync(self.properties.Get, DBUS_INTERFACE_ADAPTER, "Address")

    async def get_paired_devices(self) -> list[str]:
        """Get the list of paired switches.

        Returns:
            A list of paired switch addresses.
        """
        manager = Interface(
            self._bus.get_object(DBUS_NAME, "/"), DBUS_INTERFACE_OBJECT_MANAGER
        )
        objects = await run_sync(manager.GetManagedObjects)

        paired_devices = []
        for interfaces in objects.values():
            if DBUS_INTERFACE_DEVICE in interfaces:
                device_interface = interfaces[DBUS_INTERFACE_DEVICE]
                if device_interface.get("Name") == SWITCH_NAME:
                    paired_devices.append(device_interface.get("Address"))

        return paired_devices
    
    async def remove_device(self, address: str):
        """Remove a paired device by its address.

        Args:
            address: The Bluetooth address of the device to remove.
        """
        device_path = None
        manager = Interface(
            self._bus.get_object(DBUS_NAME, "/"), DBUS_INTERFACE_OBJECT_MANAGER
        )
        objects = await run_sync(manager.GetManagedObjects)

        for path, interfaces in objects.items():
            if DBUS_INTERFACE_DEVICE in interfaces:
                device_interface = interfaces[DBUS_INTERFACE_DEVICE]
                if device_interface.get("Address") == address:
                    device_path = path
                    break

        if device_path is not None:
            adapter_path = self.adapter.object_path
            adapter = Interface(
                self._bus.get_object(DBUS_NAME, adapter_path), DBUS_INTERFACE_ADAPTER
            )
            await run_sync(adapter.RemoveDevice, device_path)
            logger.info(f"Removed paired device with address {address}.")
        else:
            logger.warning(f"No paired device found with address {address}.")

    async def register_hid_profile(self):
        """Register the HID profile for the controller."""
        adapter_path = self.adapter.object_path
        logger.debug(f"Adapter path: {adapter_path}")
        profile_manager = Interface(
            await self._get_bus_object("/org/bluez"),
            DBUS_INTERFACE_PROFILE_MANAGER,
        )
        async with aio_open(PROFILE_PATH, "r") as f:
            sdp_record = await f.read()

        await run_sync(
            profile_manager.RegisterProfile,
            HID_PATH,
            str(uuid4()),
            {
                "ServiceRecord": sdp_record,
                "Role": "server",
                "Service": HID_UUID,
                "RequireAuthentication": False,
                "RequireAuthorization": False,
            },
        )
        logger.info("Registered HID profile.")

    async def set_powered(self, powered: bool):
        """Set the power state of the Bluetooth adapter.

        Args:
            powered: True to power on the adapter, False to power it off.
        """
        await run_sync(self.properties.Set, DBUS_INTERFACE_ADAPTER, "Powered", Boolean(powered))
        logger.info(f"Set adapter power state to {powered}")

    async def set_discoverable(self, discoverable: bool):
        """Set the discoverable state of the Bluetooth adapter.

        Args:
            discoverable: True to make the adapter discoverable, False to make it non-discoverable.
        """
        await run_sync(
            self.properties.Set, DBUS_INTERFACE_ADAPTER, "Discoverable", Boolean(discoverable)
        )
        logger.info(f"Set adapter discoverable state to {discoverable}")

    async def set_alias(self, alias: str):
        """Set the alias (name) of the Bluetooth adapter.

        Args:
            alias: The new alias for the adapter.
        """
        await run_sync(self.properties.Set, DBUS_INTERFACE_ADAPTER, "Alias", String(alias))
        logger.info(f"Set adapter alias to {alias}")

    async def set_pairable(self, pairable: bool):
        """Set the pairable state of the Bluetooth adapter.

        Args:
            pairable: True to make the adapter pairable, False to make it non-pairable.
        """
        await run_sync(
            self.properties.Set, DBUS_INTERFACE_ADAPTER, "Pairable", Boolean(pairable)
        )
        logger.info(f"Set adapter pairable state to {pairable}")

    async def discover_adapter(self):
        """Discover the first available Bluetooth adapter or first adapter that matches the configured device ID.

        Returns:
            The DBus proxy object for the discovered adapter.

        Raises:
            RuntimeError: If no Bluetooth adapter is found.
        """
        device_id = self._config.bluetooth_device_id
        manager = Interface(
            await self._get_bus_object("/"), DBUS_INTERFACE_OBJECT_MANAGER
        )
        objects = await run_sync(manager.GetManagedObjects)

        for path, interfaces in objects.items():
            if DBUS_INTERFACE_ADAPTER in interfaces:
                logger.info(f"Discovered Bluetooth adapter at {path}")
                if device_id is None or path.endswith(device_id):
                    logger.info(f"Using Bluetooth adapter at {path}")
                    device = await self._get_bus_object(path)
                    break
        else:
            raise RuntimeError("No Bluetooth adapter found.")

        self._adapter = Interface(device, DBUS_INTERFACE_ADAPTER)
        self._properties = Interface(device, DBUS_INTERFACE_PROPERTIES)
        self._device = device

    async def _get_bus_object(self, path: str, name: str = DBUS_NAME) -> ProxyObject:
        """Get a DBus proxy object for the given path.

        Args:
            path: The path of the DBus object to retrieve.

        Returns:
            The DBus proxy object for the given path.
        """
        return await run_sync(self._bus.get_object, name, path)

    @property
    def adapter(self) -> Interface:
        """Get the DBus interface for the Bluetooth adapter.

        Returns:
            The DBus interface for the Bluetooth adapter.

        Raises:
            RuntimeError: If the adapter has not been discovered yet.
        """
        if self._adapter is None:
            raise RuntimeError(
                "Bluetooth adapter has not been discovered yet. Call discover_adapter() first."
            )
        return self._adapter

    @property
    def properties(self) -> Interface:
        """Get the DBus interface for the Bluetooth adapter properties.

        Returns:
            The DBus interface for the Bluetooth adapter properties.

        Raises:
            RuntimeError: If the adapter properties have not been discovered yet.
        """
        if self._properties is None:
            raise RuntimeError(
                "Bluetooth adapter properties have not been discovered yet. Call discover_adapter() first."
            )
        return self._properties

    @property
    def device(self) -> ProxyObject:
        """Get the DBus proxy object for the Bluetooth adapter.

        Returns:
            The DBus proxy object for the Bluetooth adapter.

        Raises:
            RuntimeError: If the adapter has not been discovered yet.
        """
        if self._device is None:
            raise RuntimeError(
                "Bluetooth adapter has not been discovered yet. Call discover_adapter() first."
            )
        return self._device

    @property
    def adapter_name(self) -> str:
        """Get the DBus name of the Bluetooth adapter.

        Returns:
            The DBus name of the Bluetooth adapter.

        Raises:
            RuntimeError: If the adapter has not been discovered yet.
        """
        if self._device is None:
            raise RuntimeError(
                "Bluetooth adapter has not been discovered yet. Call discover_adapter() first."
            )
        return self._device.object_path.split("/")[-1]