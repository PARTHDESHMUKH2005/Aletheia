"""Shared upload limits and path validation for every storage backend."""
import re
from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PHOTOS = 4
_KEY = re.compile(r"(?:[A-Za-z0-9_-]{1,80}/)?[A-Za-z0-9][A-Za-z0-9_-]{0,127}\.(?:jpg|jpeg|png|webp)")


def validate_upload_key(key: str) -> str:
    if not isinstance(key, str) or not _KEY.fullmatch(key):
        raise ValueError("invalid photo key")
    return key


def validate_image(data: bytes, key: str | None = None) -> str:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("photo must be between 1 byte and 5 MiB")
    try:
        with Image.open(BytesIO(data)) as photo:
            if photo.format not in ("JPEG", "PNG", "WEBP") or photo.width * photo.height > 16_000_000:
                raise ValueError("use a JPEG, PNG or WebP image with at most 16 million pixels")
            media_type = Image.MIME[photo.format]
            if key is not None:
                expected = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}.get(key.rsplit(".", 1)[-1])
                if photo.format != expected:
                    raise ValueError("photo format does not match its upload key")
            photo.verify()
            return media_type
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("invalid image") from exc
