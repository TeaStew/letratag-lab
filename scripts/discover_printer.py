"""Discover nearby Bluetooth Low Energy devices."""

import asyncio

from bleak import BleakScanner


async def main():
    """Scan for BLE devices and display their advertised information."""
    print("Scanning for Bluetooth LE devices for 10 seconds...")
    print("Make sure the LetraTag 200B is switched on.\n")

    devices = await BleakScanner.discover(
        timeout=10.0,
        return_adv=True,
    )

    if not devices:
        print("No BLE devices found.")
        return

    for device, advertisement in devices.values():
        print(f"Name: {device.name or '(unnamed)'}")
        print(f"Address: {device.address}")
        print(f"RSSI: {advertisement.rssi} dBm")
        print(f"Advertised services: {advertisement.service_uuids}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
