"""characterize_waste tool: the tool-less characterizer, structured output,
cheap-then-strong escalation, image-hash cache, compact output. BUILD.md section 5.
"""
import hashlib
import json
import logging
import time
from typing import TypedDict

from app.config import get_model, get_retry_strategy, get_settings
from strands.types.exceptions import MaxTokensReachedException

from app.models import Characterization

logger = logging.getLogger("loopback.characterize")

CONFIDENCE_ESCALATION_THRESHOLD = 0.7
MAX_PHOTOS = 4


class PhotoBlock(TypedDict):
    format: str  # "jpeg" | "png" | "gif" | "webp"
    bytes: bytes


def compute_image_hash(photos: list[PhotoBlock]) -> str:
    """sha256 over the resized image bytes, in submission order. Cache key for repeat demos."""
    hasher = hashlib.sha256()
    for photo in photos:
        hasher.update(photo["bytes"])
    return hasher.hexdigest()


def _build_prompt(photos: list[PhotoBlock], note: str, quantity_kg: float | None) -> list[dict]:
    text = "Characterize every distinct waste item visible across these photos. Return every field in the schema for each item. List any visible contaminants in 'contaminants' (for example 'steel pieces mixed in', 'oil stains', 'plastic labels'); use an empty list if none are visible. Do not invent contaminants, and do not give a purity percentage. "
    if note:
        text += f"Submitter note: {note}. "
    if quantity_kg is not None:
        text += f"Submitter-stated total quantity: {quantity_kg} kg. "
    else:
        text += "No quantity was stated; estimate it and set quantity_basis to 'estimated'. "

    blocks: list[dict] = [{"text": text}]
    for photo in photos:
        blocks.append({"image": {"format": photo["format"], "source": {"bytes": photo["bytes"]}}})
    return blocks


def _run_model(tier: str, prompt: list[dict]) -> Characterization:
    from strands import Agent

    settings = get_settings()
    model_id = {"fast": settings.model_fast, "strong": settings.model_strong}[tier]

    start = time.monotonic()
    agent = Agent(model=get_model(tier), tools=[], retry_strategy=get_retry_strategy())
    result = agent(prompt, structured_output_model=Characterization)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    usage = dict(result.metrics.accumulated_usage) if result.metrics.accumulated_usage else {}
    logger.info(json.dumps({
        "step": "characterize",
        "tier": tier,
        "model_id": model_id,
        "ms": elapsed_ms,
        **usage,
    }))
    return result.structured_output


def characterize_waste(
    photos: list[PhotoBlock],
    note: str = "",
    quantity_kg: float | None = None,
    storage=None,
) -> Characterization:
    """All photos for one stream go into a single call (max 4). Cheap model first;
    if overall_confidence < 0.7, run the strong model once. Never loops. Cached by
    sha256 of the combined image bytes, so repeat demos cost nothing.
    """
    if not photos:
        raise ValueError("characterize_waste requires at least one photo")
    photos = photos[:MAX_PHOTOS]

    if storage is None:
        from app.config import get_storage
        storage = get_storage()

    image_hash = compute_image_hash(photos)
    cached = storage.get_cached_characterization(image_hash)
    if cached is not None:
        logger.info(json.dumps({"step": "characterize", "cache_hit": True, "image_sha": image_hash}))
        return Characterization.model_validate(cached)

    prompt = _build_prompt(photos, note, quantity_kg)
    try:
        characterization = _run_model("fast", prompt)
        if characterization.overall_confidence < CONFIDENCE_ESCALATION_THRESHOLD:
            characterization = _run_model("strong", prompt)
    except MaxTokensReachedException:
        # The cheap tier ran out of output budget; the stronger tier has more. Still one retry, never a loop.
        logger.info(json.dumps({"step": "characterize", "max_tokens_retry": True}))
        characterization = _run_model("strong", prompt)

    storage.set_cached_characterization(image_hash, characterization.model_dump())
    return characterization
