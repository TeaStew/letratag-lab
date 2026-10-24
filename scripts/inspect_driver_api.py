"""Inspect the installed DYMO driver API without printing anything."""

import asyncio
import inspect
from importlib.metadata import version

import dymo_bluetooth
from dymo_bluetooth import Canvas, discover_printers


def show_signature(label, obj):
    """Print an object's signature when Python can inspect it."""
    try:
        print(f"{label}{inspect.signature(obj)}")
    except (TypeError, ValueError):
        print(f"{label}: signature unavailable")


async def main():
    print("Installed package version:")
    print(version("dymo-bluetooth"))

    print("\nPackage location:")
    print(dymo_bluetooth.__file__)

    print("\nCanvas constructor:")
    show_signature("Canvas", Canvas)

    print("\nCanvas methods:")
    for name, member in inspect.getmembers(Canvas):
        if not name.startswith("_") and callable(member):
            show_signature(f"Canvas.{name}", member)

    print("\nDiscovering printer (no connection or printing)...")
    printers = await discover_printers()

    if not printers:
        print("No compatible printer found.")
        return

    printer = printers[0]
    printer_class = type(printer)

    print(f"\nPrinter class: {printer_class.__module__}.{printer_class.__name__}")

    for name in ("connect", "disconnect", "print"):
        method = getattr(printer_class, name, None)
        if method is not None:
            print(f"\n{name} method:")
            show_signature(f"{printer_class.__name__}.{name}", method)

            try:
                print(inspect.getsource(method))
            except (OSError, TypeError):
                print("Source unavailable.")

    print("\nInspection complete. No print job was sent.")


if __name__ == "__main__":
    asyncio.run(main())