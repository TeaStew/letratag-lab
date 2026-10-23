"""Generate a content-sized DYMO LetraTag label from command-line text."""

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


LABEL_HEIGHT = 30
HORIZONTAL_MARGIN = 8
FONT_SIZE = 21


def load_font():
    """Load Arial if available, otherwise use Pillow's default font."""
    font_path = Path("C:/Windows/Fonts/arial.ttf")

    if font_path.exists():
        return ImageFont.truetype(str(font_path), FONT_SIZE)

    return ImageFont.load_default()


def make_label(text, output_path):
    """Render text into a content-sized, monochrome-compatible PNG."""
    font = load_font()

    # Measure the text before creating the image.
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    label_width = text_width + (HORIZONTAL_MARGIN * 2)

    # Create a white canvas at the required printer image height.
    image = Image.new(
        "RGB",
        (label_width, LABEL_HEIGHT),
        color="white",
    )
    draw = ImageDraw.Draw(image)

    # Position the text, accounting for the font's bounding-box offset.
    x = HORIZONTAL_MARGIN - bbox[0]
    y = (LABEL_HEIGHT - text_height) // 2 - bbox[1]

    draw.text((x, y), text, fill="black", font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)

    print(f"Saved label: {output_path}")
    print(f"Image dimensions: {image.width} x {image.height}")
    print(f"Label text: {text}")


def main():
    """Parse command-line arguments and generate a label."""
    parser = argparse.ArgumentParser(
        description="Generate an image for a DYMO LetraTag label."
    )
    parser.add_argument(
        "text",
        help="Text to print on the label, e.g. SAMPLE-002",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output PNG path (default: output/<label-text>.png)",
    )

    args = parser.parse_args()

    # Turn the text into a safe, simple default filename.
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", args.text).strip("_")
    if not filename:
        filename = "label"

    output_path = args.output or Path("output") / f"{filename}.png"

    make_label(args.text, output_path)


if __name__ == "__main__":
    main()