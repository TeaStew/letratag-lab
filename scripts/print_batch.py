"""Print a batch of PNG labels with explicit user confirmation."""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def natural_sort_key(path):
    """Sort filenames numerically, so SAMPLE-2 comes before SAMPLE-10."""
    parts = re.split(r"(\d+)", path.name)
    return [
        (1, int(part)) if part.isdigit() else (0, part.lower())
        for part in parts
    ]


def main():
    """Review a batch and print labels one at a time."""
    parser = argparse.ArgumentParser(
        description="Print PNG labels with confirmation between labels."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("output/batch"),
        help="Directory containing PNG labels (default: output/batch)",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        parser.error(f"Directory not found: {args.input_dir}")

    labels = sorted(
        args.input_dir.glob("*.png"),
        key=natural_sort_key,
    )

    if not labels:
        parser.error(f"No PNG files found in {args.input_dir}")

    print("\nDYMO LetraTag batch print queue")
    print("-" * 32)
    print(f"Directory:   {args.input_dir}")
    print(f"Label count: {len(labels)}")
    print(f"First label: {labels[0].stem}")
    print(f"Last label:  {labels[-1].stem}")
    print("\nLabels in queue:")

    for index, label in enumerate(labels, start=1):
        print(f"  {index:>3}. {label.name}")

    print("\nNo labels have been printed yet.")
    confirmation = input(
        "\nType PRINT to confirm this batch, or anything else to cancel: "
    )

    if confirmation != "PRINT":
        print("Batch cancelled. Nothing was sent to the printer.")
        return

    print("\nStarting controlled print queue.")
    print("Keep the printer powered on with its lid closed.\n")

    for index, label in enumerate(labels, start=1):
        print(f"\nLabel {index} of {len(labels)}: {label.name}")

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
            print("Unrecognised choice. Queue stopped for safety.")
            break

        print(f"Sending {label.name} to the printer...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "dymo_bluetooth",
                    str(label),
                ],
                check=False,
            )
        except KeyboardInterrupt:
            print("\nInterrupted. Check the printer before continuing.")
            break
        except OSError as exc:
            print(f"Could not start the print command: {exc}")
            break

        if result.returncode != 0:
            print(
                f"Print command failed with exit code {result.returncode}."
            )
            print("Queue stopped. Check the printer before retrying.")
            break

        print(
            "The print command finished. Check the physical label "
            "before proceeding."
        )

        if index < len(labels):
            print("The next label will not print until you confirm again.")

    print("\nPrint queue finished or stopped.")
    print("Check the physical output to confirm which labels printed.")


if __name__ == "__main__":
    main()