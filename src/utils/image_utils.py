"""
Image processing utilities for compression and optimization
"""

import io
from PIL import Image
from typing import Union, Tuple
from utils.logger import logger


# Voyage AI limits
MAX_PIXELS = 8_000_000  # 8M pixels
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# Target resolution (1080p)
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_MAX_PIXELS = TARGET_WIDTH * TARGET_HEIGHT  # ~2M pixels


def calculate_target_size(width: int, height: int, max_pixels: int) -> Tuple[int, int]:
  """
  Calculate target size while maintaining aspect ratio.

  Args:
      width: Original width
      height: Original height
      max_pixels: Maximum allowed pixels

  Returns:
      Tuple of (new_width, new_height)
  """
  current_pixels = width * height

  if current_pixels <= max_pixels:
    return width, height

  # Calculate scale factor
  scale = (max_pixels / current_pixels) ** 0.5

  new_width = int(width * scale)
  new_height = int(height * scale)

  return new_width, new_height


def compress_image(
  image_bytes: Union[bytes, io.BytesIO],
  target_max_pixels: int = TARGET_MAX_PIXELS,
  quality: int = 85,
  format: str = "JPEG",
) -> bytes:
  """
  Compress image to meet Voyage AI requirements.

  - Resizes to target resolution (default 1080p) while maintaining aspect ratio
  - Compresses to reduce file size
  - Converts to JPEG for better compression

  Args:
      image_bytes: Image as bytes or BytesIO
      target_max_pixels: Maximum pixels (default ~2M for 1080p)
      quality: JPEG quality (1-100, default 85)
      format: Output format (default JPEG)

  Returns:
      Compressed image as bytes
  """
  try:
    # Open image
    if isinstance(image_bytes, io.BytesIO):
      img = Image.open(image_bytes)
    else:
      img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA to RGB if needed (for JPEG compatibility)
    if img.mode in ("RGBA", "LA", "P"):
      # Create white background
      background = Image.new("RGB", img.size, (255, 255, 255))
      if img.mode == "P":
        img = img.convert("RGBA")
      background.paste(
        img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
      )
      img = background
    elif img.mode not in ("RGB", "L"):
      img = img.convert("RGB")

    original_size = img.size
    original_pixels = img.width * img.height

    # Calculate target size
    new_width, new_height = calculate_target_size(
      img.width, img.height, target_max_pixels
    )

    # Resize if needed
    if (new_width, new_height) != original_size:
      img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
      logger.info(
        f"Resized image: {original_size[0]}x{original_size[1]} "
        f"({original_pixels:,} pixels) → {new_width}x{new_height} "
        f"({new_width * new_height:,} pixels)"
      )

    # Compress to bytes
    output = io.BytesIO()
    img.save(output, format=format, quality=quality, optimize=True)
    compressed_bytes = output.getvalue()

    # Log compression ratio
    original_bytes = len(
      image_bytes.getvalue() if isinstance(image_bytes, io.BytesIO) else image_bytes
    )
    compression_ratio = (1 - len(compressed_bytes) / original_bytes) * 100

    logger.info(
      f"Compressed image: {original_bytes / 1024:.1f}KB → "
      f"{len(compressed_bytes) / 1024:.1f}KB "
      f"({compression_ratio:.1f}% reduction)"
    )

    # If still too large, reduce quality iteratively
    if len(compressed_bytes) > MAX_SIZE_BYTES:
      logger.warning(
        f"Image still too large ({len(compressed_bytes) / 1024 / 1024:.1f}MB), reducing quality..."
      )

      for reduced_quality in [75, 65, 55, 45]:
        output = io.BytesIO()
        img.save(output, format=format, quality=reduced_quality, optimize=True)
        compressed_bytes = output.getvalue()

        logger.info(
          f"Trying quality={reduced_quality}: {len(compressed_bytes) / 1024 / 1024:.2f}MB"
        )

        if len(compressed_bytes) <= MAX_SIZE_BYTES:
          break

    return compressed_bytes

  except Exception as e:
    logger.error(f"Error compressing image: {e}")
    raise


def validate_image_for_voyage(image_bytes: bytes) -> Tuple[bool, str]:
  """
  Check if image meets Voyage AI requirements.

  Args:
      image_bytes: Image as bytes

  Returns:
      Tuple of (is_valid, error_message)
  """
  try:
    img = Image.open(io.BytesIO(image_bytes))
    pixels = img.width * img.height
    size_mb = len(image_bytes) / 1024 / 1024

    if pixels > MAX_PIXELS:
      return False, f"Image too large: {pixels:,} pixels (max {MAX_PIXELS:,})"

    if len(image_bytes) > MAX_SIZE_BYTES:
      return False, f"File too large: {size_mb:.1f}MB (max 20MB)"

    return True, "OK"

  except Exception as e:
    return False, f"Invalid image: {str(e)}"


def get_image_info(image_bytes: Union[bytes, io.BytesIO]) -> dict:
  """Get image metadata."""
  try:
    if isinstance(image_bytes, io.BytesIO):
      img = Image.open(image_bytes)
    else:
      img = Image.open(io.BytesIO(image_bytes))

    size_bytes = len(
      image_bytes.getvalue() if isinstance(image_bytes, io.BytesIO) else image_bytes
    )

    return {
      "width": img.width,
      "height": img.height,
      "pixels": img.width * img.height,
      "format": img.format,
      "mode": img.mode,
      "size_bytes": size_bytes,
      "size_mb": size_bytes / 1024 / 1024,
    }
  except Exception as e:
    return {"error": str(e)}
