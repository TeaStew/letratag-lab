
"""Print a batch of labels, reconnecting after Bluetooth standby. 
The image conversion and print-command format come from dymo-bluetooth."""

import argparse
import asyncio
import re
from pathlib import Path
from letratag_lab.printer import print_one
from letratag_lab.print_results import describe_print_error, handle_print_result
from dymo_bluetooth.bluetooth import discover_printers

EXPECTED_ADDRESS = "DC:54:75:41:55:B6"
DEFAULT_TIMEOUT = 10

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
                if not handle_print_result(result):
                    break

            except Exception as exc:
                summary, technical_detail = describe_print_error(exc)

                print(f"\n{summary}")
                print(f"Technical detail: {technical_detail}")

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
                    if not handle_print_result(result):
                        break
                
                except Exception as retry_exc:
                    summary, technical_detail = describe_print_error(retry_exc)

                    print(f"\nRetry failed. {summary}")
                    print(f"Technical detail: {technical_detail}")
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