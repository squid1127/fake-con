# fake-con

A "fork" of [joycontrol](https://github.com/Poohl/joycontrol) since the original project was not working for some reason.

## Changes

- Made into a poetry project
- Restructured the thing a bit
- Fixed a lot of weird bugs I kept running into (WHY IS IT LIKE THIS WHO MADE THIS (no offense i was kidding you're really awesome twin))

## Async API

Scripts can import `fake_con` and use the controller without starting the CLI:

```python
import asyncio

from fake_con import Controller, FakeCon, connect


async def main():
	controller = await connect(Controller.PRO_CONTROLLER, reconnect_bt_addr="auto")
	try:
		await controller.tap("a")
		await controller.press("zl")
		await controller.set_stick("left", h=2048, v=2048)
		await controller.release("zl")
	finally:
		await controller.close()


asyncio.run(main())
```

The same lifecycle can be written with an async context manager:

```python
async with FakeCon(Controller.PRO_CONTROLLER) as controller:
	await controller.tap("home")
```

`connect()` waits until the Switch has accepted the controller and all input
methods are asynchronous. Use `reconnect_bt_addr` to reconnect to an already
paired console, or omit it for initial pairing.

To let the script accept BlueZ pairing requests automatically, pass
`auto_pairing=True`. This requires the system `dbus-python` and GLib bindings:

```python
controller = await connect(
	Controller.PRO_CONTROLLER,
	reconnect_bt_addr="auto",
	auto_pairing=True,
)
```
