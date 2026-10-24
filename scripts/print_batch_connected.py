"""Print a batch of labels using one persistent BLE connection.
The image conversion and print-command format come from dymo-bluetooth.
This script manages notification cleanup for repeated print jobs."""

import argparse
import asyncio
import re
from pathlib import Path

from dymo_bluetooth.bluetooth import (
    PRINT_REPLY_UUID,
    PRINT_REQUEST_UUID,
    create_image,
    discover_printers,
)
from dymo_bluetooth.printer import Result, command_print


EXPECTED_ADDRESS = "DC:54:75:41:55:B6"
DEFAULT_TIMEOUT = 10
STRETCH_FACTOR = 2


def natural_sort_key(path):
    """Sort numbered filenames in human order."""
    parts = re.split(r"(\d+)", path.name)
    return [
        (1, int(part)) if part.isdigit() else (0, part.lower())
        for part in parts
    ]


def get_printer_address(printer):
    """Read the address exposed by the upstream printer wrapper."""
    implementation = getattr(printer, "_impl", None)
    return getattr(implementation, "address", None)


async def print_one(printer, label_path):
    """Print one label and clean up its notification handler."""
    client = printer._client

    if not client.is_connected:
        raise RuntimeError("Printer is no longer connected.")

    print_request = client.services.get_characteristic(PRINT_REQUEST_UUID)
    print_reply = client.services.get_characteristic(PRINT_REPLY_UUID)

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    should_discard = False

    def reply_get(_, data):
        """Handle printer replies without completing the future twice."""
        nonlocal should_discard

        if future.done():
            return

        try:
            result = Result.from_bytes(data)
        except (ValueError, IndexError) as exc:
            future.set_exception(exc)
            return

        # Preserve the upstream driver's handling of its initial reply.
        if not should_discard and result.value in (0, 1):
            should_discard = True
            return

        future.set_result(result)

    try:
        await client.start_notify(print_reply, reply_get)

        canvas = create_image(label_path, dither=True)
        canvas = canvas.stretch(factor=STRETCH_FACTOR)

        for chunk in command_print(canvas):
            await client.write_gatt_char(print_request, chunk, True)

        # Wait for the final printer response.
        return await future

    finally:
        # Cancel an unfinished wait, then remove this job's notification
        # handler before another label is sent.
        if not future.done():
            future.cancel()

        try:
            await client.stop_notify(print_reply)
        except Exception as exc:
            print(f"Warning: could not stop notifications cleanly: {exc}")


async def print_batch(labels, timeout):
    """Connect once, then print labels until stopped or completed."""
    print(f"Searching for the printer ({EXPECTED_ADDRESS})...")
    printers = await discover_printers(timeout, False)

    printer = next(
        (
            candidate
            for candidate in printers
            if str(get_printer_address(candidate)).upper()
            == EXPECTED_ADDRESS.upper()
        ),
        None,
    )

    if printer is None:
        print("The expected printer was not found.")
        print("No labels have been sent.")
        return

    print(f"Found the expected printer: {EXPECTED_ADDRESS}")
    connected = False

    try:
        await printer.connect()
        connected = True
        print("Connected. The connection will be reused for this batch.")

        for index, label_path in enumerate(labels, start=1):
            print(f"\nLabel {index} of {len(labels)}: {label_path.name}")

            try:
                choice = input(
                    "Press Enter to print this label, or type q to stop: "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nQueue stopped by user.")
                break

            if choice == "q":
                print("Queue stopped. Remaining labels were not sent.")
                break

            if choice:
                print("Unrecognised choice. Queue stopped.")
                break

            print("Sending print job...")

            try:
                result = await print_one(printer, label_path)
            except Exception as exc:
                print(f"Printing failed: {type(exc).__name__}: {exc}")
                print("Queue stopped. Check the printer before retrying.")
                break

            print(f"Printer response: {result.name} ({result.value})")
            print("Please check the physical label before continuing.")

    finally:
        if connected:
            try:
                await printer.disconnect()
                print("\nBluetooth connection closed.")
            except Exception as exc:
                print(f"Disconnect warning: {exc}")


def main():
    """Validate the queue and request confirmation before connecting."""
    parser = argparse.ArgumentParser(
        description="Print a batch using one persistent BLE connection."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("output/batch"),
        help="Directory containing PNG labels",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Printer discovery timeout in seconds",
    )
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    if not args.input_dir.is_dir():
        parser.error(f"Directory not found: {args.input_dir}")

    labels = sorted(args.input_dir.glob("*.png"), key=natural_sort_key)

    if not labels:
        parser.error(f"No PNG files found in {args.input_dir}")

    print("\nDYMO LetraTag persistent print queue")
    print("-" * 36)
    print(f"Printer:     {EXPECTED_ADDRESS}")
    print(f"Directory:   {args.input_dir}")
    print(f"Label count: {len(labels)}")
    print(f"First label: {labels[0].stem}")
    print(f"Last label:  {labels[-1].stem}")

    for index, label in enumerate(labels, start=1):
        print(f"  {index:>3}. {label.name}")

    confirmation = input(
        "\nType PRINT to confirm this batch, or anything else to cancel: "
    )

    if confirmation != "PRINT":
        print("Batch cancelled. Nothing was sent to the printer.")
        return

    asyncio.run(print_batch(labels, args.timeout))


if __name__ == "__main__":
    main()