"""Env-driven settings plus factories for storage and model objects.

Moving from local to AWS, or from Gemini to Bedrock, changes these factories only.
Nothing else in the codebase should import boto3, google.genai, or sqlite3 directly.
"""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    storage: str              # "local" | "aws"
    model_provider: str       # "bedrock" | "gemini"
    model_fast: str
    model_strong: str
    model_orch: str
    gemini_api_key: str | None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        storage=os.environ.get("STORAGE", "local"),
        model_provider=os.environ.get("MODEL_PROVIDER", "gemini"),
        model_fast=os.environ.get("MODEL_FAST", "gemini-3.8-flash"),
        model_strong=os.environ.get("MODEL_STRONG", "gemini-pro-latest"),
        model_orch=os.environ.get("MODEL_ORCH", "gemini-3.8-flash"),
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
    )


def get_storage():
    """Returns the storage backend: storage/local.py (SQLite + disk) or storage/aws.py (DynamoDB + S3)."""
    settings = get_settings()
    if settings.storage == "local":
        from app.storage.local import LocalStorage
        return LocalStorage()
    from app.storage.aws import AwsStorage
    return AwsStorage()


# Hard limits (BUILD.md section 5, efficiency rule 4): every model call gets a
# token ceiling and temperature 0-0.2. orch gets more tokens for tool-call turns.
# Field name for the token ceiling differs per provider config: Bedrock uses
# max_tokens, Gemini's params dict maps onto GenerateContentConfig's max_output_tokens.
_TIER_LIMITS = {
    "fast": {"temperature": 0.1, "max_tokens": 1024},
    "strong": {"temperature": 0.1, "max_tokens": 1536},
    "orch": {"temperature": 0.2, "max_tokens": 1024},
}


def get_model(tier: str):
    """tier is 'fast', 'strong' or 'orch'. Returns a Strands model object for the configured provider.

    Verified against installed strands-agents==1.59.0:
    - BedrockModel(model_id=...) under strands.models.bedrock.
    - GeminiModel(client_args={"api_key": ...}, model_id=..., params={...}) under
      strands.models.gemini; model_id and params are part of GeminiConfig
      (**model_config), not direct constructor kwargs. params maps straight onto
      google.genai.types.GenerateContentConfig, so its keys are temperature and
      max_output_tokens. Requires the separate `google-genai` package.
    """
    settings = get_settings()
    model_id = {
        "fast": settings.model_fast,
        "strong": settings.model_strong,
        "orch": settings.model_orch,
    }[tier]
    limits = _TIER_LIMITS[tier]

    if settings.model_provider == "bedrock":
        from strands.models.bedrock import BedrockModel
        return BedrockModel(model_id=model_id, **limits)

    from strands.models.gemini import GeminiModel
    gemini_params = {"temperature": limits["temperature"], "max_output_tokens": limits["max_tokens"]}
    return GeminiModel(
        client_args={"api_key": settings.gemini_api_key},
        model_id=model_id,
        params=gemini_params,
    )
