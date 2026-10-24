"""Generate a batch of sequential DYMO LetraTag label images."""

import argparse
from pathlib import Path

from make_sample_label_cli import make_label


def main():
    """Parse batch settings and generate sequential label images."""
    parser = argparse.ArgumentParser(
        description="Generate sequential sample-ID label images."
    )
    parser.add_argument(
        "--prefix",
        default="SAMPLE-",
        help="Text before each number (default: SAMPLE-)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="First number in the sequence (default: 1)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=12,
        help="Number of labels to generate (default: 12)",
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=3,
        help="Minimum number of digits, including leading zeros (default: 3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/batch"),
        help="Directory for generated PNGs (default: output/batch)",
    )

    args = parser.parse_args()

    if args.start < 0:
        parser.error("--start must be zero or greater")

    if args.count < 1:
        parser.error("--count must be at least 1")

    if args.digits < 1:
        parser.error("--digits must be at least 1")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Prefix:      {args.prefix}")
    print(f"First ID:    {args.start}")
    print(f"Label count: {args.count}")
    print(f"Output:      {args.output_dir}")
    print()

    for offset in range(args.count):
        number = args.start + offset
        label_text = f"{args.prefix}{number:0{args.digits}d}"
        output_path = args.output_dir / f"{label_text}.png"

        make_label(label_text, output_path)

    print()
    print(f"Finished: generated {args.count} label images.")


if __name__ == "__main__":
    main()