#!/usr/bin/env python3
"""Isolate the public avatar, enhance grayscale contrast, and composite on white."""

import argparse
from hashlib import sha256
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]

# Pixel-art scenery defeats the photographic segmentation models: U2-Net
# includes the binary backdrop and erases the black shirt. This traced matte
# belongs only to this exact decoded avatar, never to a replacement photo.
ILLUSTRATED_AVATAR_SHA256 = "1e8c7a53a45bf4d332025a18c96d2a5b6d7424caa07dd7815ad3d24ebaf4e8b5"
ILLUSTRATED_SILHOUETTE = (
    (174, 43), (193, 35), (219, 32), (247, 34), (275, 39),
    (299, 50), (318, 65), (333, 83), (345, 105), (349, 122),
    (372, 134), (372, 149), (362, 154), (373, 163), (365, 173),
    (368, 183), (354, 190), (348, 213), (334, 227), (332, 249),
    (320, 277), (321, 300), (338, 309), (365, 317), (387, 335),
    (402, 352), (414, 374), (415, 405), (399, 408),
    (417, 426), (430, 460), (137, 460), (135, 424), (139, 395),
    (139, 377), (140, 341), (127, 329), (114, 301), (104, 278),
    (103, 238), (91, 224), (78, 221), (76, 207), (84, 196),
    (77, 190), (81, 175), (90, 153), (101, 133), (119, 110),
    (137, 89), (153, 64),
)


def corrected_alpha(original: Image.Image, inferred: Image.Image) -> Image.Image:
    """Use the reviewed matte only when the entire decoded source matches."""
    if original.size != (460, 460) or sha256(original.tobytes()).hexdigest() != ILLUSTRATED_AVATAR_SHA256:
        return inferred
    scale = 4
    matte = Image.new("L", (original.width * scale, original.height * scale), 0)
    ImageDraw.Draw(matte).polygon([(x * scale, y * scale) for x, y in ILLUSTRATED_SILHOUETTE], fill=255)
    matte = matte.resize(original.size, Image.Resampling.LANCZOS)
    print("Applied reviewed silhouette matte for the current illustrated avatar")
    return Image.fromarray(np.minimum(np.asarray(matte), np.asarray(original.getchannel("A"))))


def prepare(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise ValueError(f"Input image does not exist: {source}")
    try:
        with Image.open(source) as image:
            original = ImageOps.exif_transpose(image).convert("RGBA")
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read input image {source}: {error}") from error

    # Select U2-Net explicitly rather than inheriting rembg's changing default.
    subject = remove(original, session=new_session("u2net")).convert("RGBA")
    alpha = corrected_alpha(original, subject.getchannel("A"))
    if not np.any(np.asarray(alpha) > 16):
        raise ValueError("Background removal produced an empty subject mask")

    # Keep the source's colors; only the segmentation alpha should change them.
    luminance = np.asarray(original.convert("L"))
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(luminance)
    white = Image.new("L", subject.size, 255)
    white.paste(Image.fromarray(enhanced), (0, 0), alpha)
    width, height = white.size
    side = min(width, height)
    left, top = (width - side) // 2, (height - side) // 2
    prepared = white.crop((left, top, left + side, top + side))

    # Replace only after encoding succeeds; preserve any previous valid output.
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".png", delete=False) as handle:
            temporary = Path(handle.name)
        prepared.save(temporary, format="PNG")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Prepared {destination.name}: {side}x{side}, grayscale L")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=ROOT / "source-photo.png")
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "source-prepped.png")
    args = parser.parse_args()
    try:
        prepare(args.input, args.output)
    except Exception as error:
        parser.exit(1, f"Portrait preparation failed: {error}\n")


if __name__ == "__main__":
    main()
