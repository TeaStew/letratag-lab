
"""Print a batch of labels, reconnecting after Bluetooth standby. 
The image conversion and print-command format come from dymo-bluetooth."""

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
REPLY_TIMEOUT_SECONDS = 30


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


async def find_expected_printer(timeout):
    """Discover the printer by its known Bluetooth address."""
    printers = await discover_printers(timeout, False)

    return next(
        (
            candidate
            for candidate in printers
            if str(get_printer_address(candidate)).upper()
            == EXPECTED_ADDRESS.upper()
        ),
        None,
    )


async def connect_with_retries(current_printer, timeout):
    """Create a fresh connection, prompting if the printer is unavailable."""
    if current_printer is not None:
        try:
            await current_printer.disconnect()
        except Exception:
            # A disconnected or stale client may not disconnect cleanly.
            pass

    while True:
        print(f"Searching for the printer ({EXPECTED_ADDRESS})...")

        try:
            printer = await find_expected_printer(timeout)

            if printer is None:
                print("Printer not found.")
            else:
                await printer.connect()

                if printer._client.is_connected:
                    print("Connected to the printer.")
                    return printer

                print("The Bluetooth connection did not become active.")

        except Exception as exc:
            print(f"Connection attempt failed: {type(exc).__name__}: {exc}")

        try:
            choice = input(
                "Check that the printer is switched on and ready.\n"
                "Press Enter to search again, or type q to stop: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped by user.")
            return None

        if choice == "q":
            print("Stopped. No new print job was sent.")
            return None


async def print_one(printer, label_path):
    """Print one label and clean up its notification handler."""
    client = printer._client

    # This check occurs before any print commands are sent.
    if not client.is_connected:
        raise RuntimeError("PRECHECK_DISCONNECTED")

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

        # Preserve the upstream driver's initial-reply behaviour.
        if not should_discard and result.value in (0, 1):
            should_discard = True
            return

        future.set_result(result)

    try:
        await client.start_notify(print_reply, reply_get)

        canvas = create_image(label_path, dither=True)
        canvas = canvas.stretch(factor=STRETCH_FACTOR)

        # Once this loop begins, a communication failure may leave the
        # physical outcome uncertain. Never automatically resend that job.
        for chunk in command_print(canvas):
            await client.write_gatt_char(print_request, chunk, True)

        return await asyncio.wait_for(
            future,
            timeout=REPLY_TIMEOUT_SECONDS,
        )

    finally:
        if not future.done():
            future.cancel()

        # The connection may already have disappeared during standby.
        if client.is_connected:
            try:
                await client.stop_notify(print_reply)
            except Exception as exc:
                print(f"Warning: notification cleanup failed: {exc}")


async def print_batch(labels, timeout):
    """Print a queue while recovering connections lost between labels."""
    printer = await connect_with_retries(None, timeout)

    if printer is None:
        return

    try:
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

            # Recover a connection lost while the queue was waiting for input.
            if not printer._client.is_connected:
                print("\nThe previous Bluetooth connection has been lost.")
                printer = await connect_with_retries(printer, timeout)

                if printer is None:
                    break

            print("Sending print job...")

            try:
                result = await print_one(printer, label_path)

            except Exception as exc:
                print(f"Printing failed: {type(exc).__name__}: {exc}")
                print("The printer may have powered off.")

                try:
                    outcome = input(
                        "Did this label physically print? "
                        "Type y (yes), n (no), or u (unsure): "
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\nQueue stopped. Check the physical label.")
                    break

                if outcome == "y":
                    print("Treating this label as printed; continuing.")
                    continue

                if outcome != "n":
                    print(
                        "Queue stopped because the print outcome is "
                        "uncertain. No automatic retry was attempted."
                    )
                    break

                print("Confirmed not printed. Reconnecting before retry.")

                printer = await connect_with_retries(printer, timeout)

                if printer is None:
                    print("Could not reconnect. The label remains unprinted.")
                    break

                print("Retrying the unprinted label once...")

                try:
                    result = await print_one(printer, label_path)
                except Exception as retry_exc:
                    print(
                        f"Retry failed: {type(retry_exc).__name__}: "
                        f"{retry_exc}"
                    )
                    print(
                        "Queue stopped. Check the physical label "
                        "before attempting another print."
                    )
                    break
 
    finally:
        if printer is not None:
            try:
                await printer.disconnect()
                print("\nBluetooth connection closed.")
            except Exception as exc:
                print(f"Disconnect warning: {exc}")


def main():
    """Validate the queue and request confirmation before connecting."""
    parser = argparse.ArgumentParser(
        description="Print a batch with Bluetooth reconnection support."
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

    print("\nDYMO LetraTag reconnecting print queue")
    print("-" * 38)
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