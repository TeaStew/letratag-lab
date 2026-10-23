"""Generate a test label image for the DYMO LetraTag 200B."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path("output/sample-001.png")
LABEL_HEIGHT = 30
LABEL_WIDTH = 240
LABEL_TEXT = "SAMPLE-001"


def main():
    """Render a black-and-white sample label and save it."""
    image = Image.new(
        "RGB",
        (LABEL_WIDTH, LABEL_HEIGHT),
        color="white",
    )
    draw = ImageDraw.Draw(image)

    font_path = Path("C:/Windows/Fonts/arial.ttf")
    if font_path.exists():
        font = ImageFont.truetype(str(font_path), 21)
    else:
        font = ImageFont.load_default()

    # Centre the text vertically and leave a small left margin.
    bbox = draw.textbbox((0, 0), LABEL_TEXT, font=font)
    text_height = bbox[3] - bbox[1]
    y = (LABEL_HEIGHT - text_height) // 2 - bbox[1]

    draw.text(
        (3, y),
        LABEL_TEXT,
        fill="black",
        font=font,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT)

    print(f"Saved label: {OUTPUT}")
    print(f"Image dimensions: {image.width} x {image.height}")
    print(f"Label text: {LABEL_TEXT}")


if __name__ == "__main__":
    main()
