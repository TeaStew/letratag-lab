"""Generate a content-sized test label for the DYMO LetraTag 200B."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path("output/sample-001.png")
LABEL_HEIGHT = 30
LABEL_TEXT = "SAMPLE-001"
HORIZONTAL_MARGIN = 8


def main():
    """Render a black-and-white sample label and save it."""

    # Load the font before creating the image, so we can measure the text.
    font_path = Path("C:/Windows/Fonts/arial.ttf")

    if font_path.exists():
        font = ImageFont.truetype(str(font_path), 21)
    else:
        font = ImageFont.load_default()

    # Measure the text using the selected font.
    text_bbox = font.getbbox(LABEL_TEXT)
    text_width = text_bbox[2] - text_bbox[0]

    # Make the image just wide enough for the text and its margins.
    label_width = text_width + (HORIZONTAL_MARGIN * 2)

    # Create the image now that we know its dimensions.
    image = Image.new(
        "RGB",
        (label_width, LABEL_HEIGHT),
        color="white",
    )
    draw = ImageDraw.Draw(image)

    # Account for the font's bounding-box offset when positioning text.
    text_height = text_bbox[3] - text_bbox[1]
    x = HORIZONTAL_MARGIN - text_bbox[0]
    y = (LABEL_HEIGHT - text_height) // 2 - text_bbox[1]

    draw.text(
        (x, y),
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
