"""
image_parser.py — Extract and prepare images for CLIP embedding.

Returns the PIL Image object which will be processed by OpenCLIP.
"""
from PIL import Image
from pathlib import Path


def parse_image(file_path: str) -> Image.Image:
    """
    Load an image file and return a PIL Image object.
    OpenCLIP will handle the preprocessing (resize, normalize, etc.).
    """
    try:
        img = Image.open(file_path)
        # Convert to RGB if needed (handles RGBA, grayscale, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        raise ValueError(f"Failed to load image {file_path}: {e}")


def get_image_metadata(file_path: str) -> dict:
    """Extract basic metadata from an image file."""
    try:
        img = Image.open(file_path)
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
        }
    except Exception as e:
        return {"error": str(e)}
