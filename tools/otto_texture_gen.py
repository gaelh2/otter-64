#!/usr/bin/env python3
"""Generate original Otto UI textures for the US text reskin."""

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT / "textures/segment2/otto_hud_head.rgba16.png",
    ROOT / "levels/menu/otto_save_button.rgba16.png",
    ROOT / "levels/menu/otto_new_button.rgba16.png",
    ROOT / "levels/menu/otto_menu_face1.ia8.png",
    ROOT / "levels/menu/otto_menu_face2.ia8.png",
)

OUTLINE = (36, 24, 18, 255)
AMBER = (200, 122, 60, 255)
CREAM = (242, 227, 201, 255)


def draw_pixel_face(image, box, scale=1, greyscale=False):
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box
    w, h = x1 - x0 + 1, y1 - y0 + 1
    sx = w / 32
    sy = h / 32

    def shape(coords, fill, outline=None, width=1):
        scaled = tuple(
            round((x0 + x * sx) if i % 2 == 0 else (y0 + x * sy))
            for i, x in enumerate(coords)
        )
        draw.ellipse(scaled, fill=fill, outline=outline, width=width)

    colors = {
        "outline": OUTLINE,
        "amber": AMBER,
        "cream": CREAM,
        "eye": OUTLINE,
        "nose": OUTLINE,
        "mouth": OUTLINE,
    }
    if greyscale:
        colors = {
            key: (int(sum(color[:3]) / 3),) * 3 + (color[3],)
            for key, color in colors.items()
        }
        colors["outline"] = (102, 106, 99, 255)
        colors["amber"] = (180, 185, 177, 255)
        colors["cream"] = (199, 203, 195, 255)
        colors["eye"] = (120, 124, 117, 255)
        colors["nose"] = (112, 116, 109, 255)
        colors["mouth"] = (118, 122, 115, 255)

    # Rounded ears sit behind the head.
    shape((2, 2, 12, 13), colors["outline"])
    shape((4, 4, 10, 12), colors["amber"])
    shape((20, 2, 30, 13), colors["outline"])
    shape((22, 4, 28, 12), colors["amber"])

    # Head, muzzle and features use the same compact silhouette at every size.
    shape((3, 5, 29, 31), colors["outline"])
    shape((4, 6, 28, 30), colors["amber"])
    shape((7, 19, 25, 29), colors["outline"])
    shape((8, 20, 24, 28), colors["cream"])
    shape((8, 12, 11, 16), colors["eye"])
    shape((21, 12, 24, 16), colors["eye"])
    shape((14, 18, 18, 21), colors["nose"])
    draw.line(
        (round(x0 + 16 * sx), round(y0 + 21 * sy),
         round(x0 + 16 * sx), round(y0 + 23 * sy)),
        fill=colors["mouth"],
        width=max(1, round(scale)),
    )
    draw.line(
        (round(x0 + 12 * sx), round(y0 + 24 * sy),
         round(x0 + 16 * sx), round(y0 + 26 * sy),
         round(x0 + 20 * sx), round(y0 + 24 * sy)),
        fill=colors["mouth"],
        width=max(1, round(scale)),
    )


def hud_head():
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((1, 1, 6, 7), fill=OUTLINE)
    draw.ellipse((2, 2, 5, 6), fill=AMBER)
    draw.ellipse((9, 1, 14, 7), fill=OUTLINE)
    draw.ellipse((10, 2, 13, 6), fill=AMBER)
    draw.ellipse((1, 3, 14, 15), fill=OUTLINE)
    draw.ellipse((2, 4, 13, 14), fill=AMBER)
    draw.ellipse((4, 9, 11, 14), fill=OUTLINE)
    draw.ellipse((5, 10, 10, 13), fill=CREAM)
    draw.point((5, 7), fill=OUTLINE)
    draw.point((10, 7), fill=OUTLINE)
    draw.point((7, 9), fill=OUTLINE)
    draw.line((8, 10, 8, 11), fill=OUTLINE)
    draw.line((6, 12, 8, 13, 10, 12), fill=OUTLINE)
    return image


def stone_texture(seed=64032):
    rng = random.Random(seed)
    image = Image.new("RGBA", (64, 32))
    pixels = image.load()
    base = (184, 194, 176)
    for y in range(32):
        for x in range(64):
            noise = rng.randint(-8, 8)
            pixels[x, y] = tuple(max(0, min(255, channel + noise)) for channel in base) + (255,)

    cracks = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(cracks)
    for points in (
        [(4, 5), (9, 7), (13, 11), (18, 12)],
        [(47, 3), (43, 8), (45, 13), (41, 18)],
        [(8, 27), (12, 24), (17, 25), (20, 22)],
        [(55, 27), (50, 23), (47, 20), (44, 20)],
    ):
        draw.line(points, fill=(91, 105, 91, 58), width=1)
        draw.line([(x, y + 1) for x, y in points], fill=(239, 242, 225, 58), width=1)
    image.alpha_composite(cracks.filter(ImageFilter.GaussianBlur(0.45)))
    return image


def card_face(greyscale=False):
    image = stone_texture()
    draw_pixel_face(image, (17, 0, 46, 31), scale=1, greyscale=greyscale)
    if greyscale:
        # Soft directional shading turns the low-contrast face into a relief.
        emboss = Image.new("RGBA", image.size, (0, 0, 0, 0))
        mask = Image.new("L", image.size, 0)
        draw_pixel_face_mask(mask, (17, 0, 46, 31))
        emboss.paste((233, 237, 226, 90), (0, 0, 64, 32), mask)
        shifted = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shifted.paste((95, 105, 95, 65), (1, 1, 65, 33), mask)
        image.alpha_composite(emboss)
        image.alpha_composite(shifted)
    return image


def draw_pixel_face_mask(mask, box):
    face = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    draw_pixel_face(face, box)
    mask.paste(face.getchannel("A"))


def menu_face_halves():
    image = Image.new("RGBA", (16, 8), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, 5, 5), fill=(255, 255, 255, 255))
    draw.ellipse((10, 0, 15, 5), fill=(255, 255, 255, 255))
    draw.ellipse((1, 1, 14, 7), fill=(255, 255, 255, 255))
    return image.crop((0, 0, 8, 8)), image.crop((8, 0, 16, 8))


def generate(preview_path=None):
    images = [hud_head(), card_face(), card_face(greyscale=True), *menu_face_halves()]
    for path, image in zip(OUT, images):
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, format="PNG", optimize=False)

    if preview_path:
        preview = Image.new("RGBA", (64 * 24, 32 * 8), (47, 53, 49, 255))
        positions = ((0, 0), (64 * 8, 0), (64 * 16, 0), (64 * 16, 16 * 8), (64 * 17, 16 * 8))
        for image, position in zip(images, positions):
            thumb = image.resize((image.width * 8, image.height * 8), Image.Resampling.NEAREST)
            preview.alpha_composite(thumb, position)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview.save(preview_path, format="PNG")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, help="optional path for an 8x nearest-neighbor contact sheet")
    args = parser.parse_args()
    generate(args.preview)


if __name__ == "__main__":
    main()
