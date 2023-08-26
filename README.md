IDÅSEN Desk Home Assistant
==========================

A simple Home Assistant integration for the IKEA IDÅSEN desk. It may also work with other desks with Linak controllers and Bluetooth capability.

The integration is compatible with Home Assistant's new native [Bluetooth platform](https://www.home-assistant.io/integrations/bluetooth) (using the Bleak library), which means it should play nicely with other Bluetooth LE-based integrations using the same Bluetooth dongle. It provides a `cover` entity to control the desk, as well as sensors providing the current height and speed of the desk.

Setup
-----

1. Ensure that you have the [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth) set up in your Home Assistant instance with a compatible Bluetooth dongle
2. Install the IDÅSEN integration by placing it in your `custom_components` folder and restarting Home Assistant
3. Make sure that the desk is already paired to your Bluetooth dongle. You can do this e.g. by starting `bluetoothctl` and running `pair <MAC address of the desk>`. This is necessary because the IDÅSEN controller requires pairing before starting a Bluetooth connection, which Bleak [does not support yet](https://github.com/hbldh/bleak/issues/309).
4. Under *Settings > Devices & Services*, click on *Add Integration* and select the *Idasen Desk* integration. Your desk should appear in the list.


Optional: Linak Desk Card
-------------------------

You can set up the [Custom LinakDesk Lovelace Card](https://github.com/IhorSyerkov/linak-desk-card) using the "Relative Height" sensor and the cover entity provided by this integration.


Previous work
-------------

The implementation has been inspired by the existing Python implementations for the desk:
- [rhyst/idasen-controller](https://github.com/rhyst/idasen-controller)
- [newAM/idasen](https://github.com/newAM/idasen)
- [zifeo/idazen](https://github.com/zifeo/idazen)

There are even a couple of existing attempts at Home Assistant integrations for the same desk based on different approaches:
- [chvancooten/homeassistant-idasen-control](https://github.com/chvancooten/homeassistant-idasen-control) (uses a separate Python daemon with Flask instead of a native Home Assistant integration)
- [j5lien/esphome-idasen-desk-controller](https://github.com/j5lien/esphome-idasen-desk-controller) (requires an ESPHome device)