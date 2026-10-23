"""Connect to the LetraTag and inspect its BLE GATT services."""

import asyncio

from bleak import BleakClient


PRINTER_ADDRESS = "DC:54:75:41:55:B6"


async def main():
    """Connect to the printer and list its GATT structure."""
    print(f"Connecting to printer at {PRINTER_ADDRESS}...")

    try:
        async with BleakClient(PRINTER_ADDRESS, timeout=20.0) as client:
            print(f"Connected: {client.is_connected}")
            print("\nDiscovered GATT services:\n")

            for service in client.services:
                print(f"Service: {service.uuid}")
                print(f"  Description: {service.description}")

                for characteristic in service.characteristics:
                    print(f"  Characteristic: {characteristic.uuid}")
                    print(f"    Properties: {', '.join(characteristic.properties)}")

                    for descriptor in characteristic.descriptors:
                        print(f"    Descriptor: {descriptor.uuid}")

                print()

    except Exception as exc:
        print(f"Connection or inspection failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())