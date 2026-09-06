import dbus

dbus.Dictionary(
    {
        dbus.String("Address"): dbus.String("50:C3:F2:37:BD:A9", variant_level=1),
        dbus.String("AddressType"): dbus.String("random", variant_level=1),
        dbus.String("Alias"): dbus.String("50-C3-F2-37-BD-A9", variant_level=1),
        dbus.String("Paired"): dbus.Boolean(False, variant_level=1),
        dbus.String("Bonded"): dbus.Boolean(False, variant_level=1),
        dbus.String("Trusted"): dbus.Boolean(False, variant_level=1),
        dbus.String("Blocked"): dbus.Boolean(False, variant_level=1),
        dbus.String("LegacyPairing"): dbus.Boolean(False, variant_level=1),
        dbus.String("CablePairing"): dbus.Boolean(False, variant_level=1),
        dbus.String("RSSI"): dbus.Int16(-84, variant_level=1),
        dbus.String("Connected"): dbus.Boolean(False, variant_level=1),
        dbus.String("UUIDs"): dbus.Array(
            [], signature=dbus.Signature("s"), variant_level=1
        ),
        dbus.String("Adapter"): dbus.ObjectPath("/org/bluez/hci0", variant_level=1),
        dbus.String("ManufacturerData"): dbus.Dictionary(
            {
                dbus.UInt16(76): dbus.Array(
                    [
                        dbus.Byte(16),
                        dbus.Byte(6),
                        dbus.Byte(53),
                        dbus.Byte(30),
                        dbus.Byte(129),
                        dbus.Byte(206),
                        dbus.Byte(184),
                        dbus.Byte(153),
                    ],
                    signature=dbus.Signature("y"),
                    variant_level=1,
                )
            },
            signature=dbus.Signature("qv"),
            variant_level=1,
        ),
        dbus.String("TxPower"): dbus.Int16(11, variant_level=1),
        dbus.String("ServicesResolved"): dbus.Boolean(False, variant_level=1),
        dbus.String("AdvertisingFlags"): dbus.Array(
            [dbus.Byte(26)], signature=dbus.Signature("y"), variant_level=1
        ),
        dbus.String("PreferredBearer"): dbus.String("last-used", variant_level=1),
    },
    signature=dbus.Signature("sv"),
)
