#!/usr/bin/env python3
"""Isolate the public avatar, enhance grayscale contrast, and composite on white."""

import argparse
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageOps
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]

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
    alpha = subject.getchannel("A")
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
