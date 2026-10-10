"""Env-driven settings plus factories for storage and model objects.

Moving from local to AWS, or between model providers, changes these factories
only. Nothing else in the codebase should import boto3, google.genai, openai,
or sqlite3 directly.

MODEL PROVIDER OVERRIDE: Gemini is the default provider (LLM_PROVIDER=gemini).
Qwen and Bedrock remain available by changing LLM_PROVIDER in config -- nothing
is hardcoded to Gemini outside this file. The Qwen path (via an OpenAI-compatible
endpoint) is wired here but UNTESTED: no Qwen API key or endpoint has been
verified against this code. Its default model IDs and base_url are guesses, not
confirmed, flagged as such below.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_dotenv_once() -> None:
    """Loads backend/../.env into os.environ (without overwriting real env vars)
    on first import, so `uvicorn app.main:app` works the same as the scripts that
    already did their own ad-hoc .env loading (hello_agent.py, run_demo.py).
    """
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv_once()


@dataclass(frozen=True)
class Settings:
    storage: str              # "local" | "aws"
    env: str                  # "local" | "production" -- gates dev-only tools
    llm_provider: str          # "gemini" | "bedrock" | "qwen"
    model_fast: str
    model_strong: str
    model_orch: str
    gemini_api_key: str | None
    qwen_api_key: str | None
    qwen_base_url: str

    @property
    def dev_tools_enabled(self) -> bool:
        """Gates demo-only tools (e.g. the ledger tamper endpoint). False whenever
        ENV=production, so a deployed environment never exposes them.
        """
        return self.env != "production"


@lru_cache
def get_settings() -> Settings:
    provider = os.environ.get("LLM_PROVIDER", "gemini")
    defaults_by_provider = {
        "gemini": {
            "fast": "gemini-3.8-flash", "strong": "gemini-pro-latest", "orch": "gemini-3.8-flash",
        },
        "bedrock": {
            "fast": "us.amazon.nova-lite-v1:0", "strong": "us.amazon.nova-pro-v1:0", "orch": "us.amazon.nova-lite-v1:0",
        },
        # UNVERIFIED: these Qwen model IDs are guesses (DashScope's Qwen-VL / Qwen-Plus
        # naming), not confirmed against a real account. VERIFY before relying on them.
        "qwen": {
            "fast": "qwen-vl-plus", "strong": "qwen-vl-max", "orch": "qwen-plus",
        },
    }
    tier_defaults = defaults_by_provider.get(provider, defaults_by_provider["gemini"])

    return Settings(
        storage=os.environ.get("STORAGE", "local"),
        env=os.environ.get("ENV", "local"),
        llm_provider=provider,
        model_fast=os.environ.get("MODEL_FAST", tier_defaults["fast"]),
        model_strong=os.environ.get("MODEL_STRONG", tier_defaults["strong"]),
        model_orch=os.environ.get("MODEL_ORCH", tier_defaults["orch"]),
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
        qwen_api_key=os.environ.get("QWEN_API_KEY"),
        # UNVERIFIED default: DashScope's OpenAI-compatible endpoint. Confirm before use.
        qwen_base_url=os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
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
# Field name for the token ceiling differs per provider config: Bedrock/OpenAI-style
# use max_tokens, Gemini's params dict maps onto GenerateContentConfig's max_output_tokens.
_TIER_LIMITS = {
    # fast/strong raised from an initial 1024/1536: a real run hit
    # MaxTokensReachedException on a single-item characterization (structured
    # output + reasoning text needs more headroom, especially with up to 4 items).
    "fast": {"temperature": 0.1, "max_tokens": 2048},
    "strong": {"temperature": 0.1, "max_tokens": 3072},
    "orch": {"temperature": 0.2, "max_tokens": 1024},
}


def get_model(tier: str):
    """tier is 'fast', 'strong' or 'orch'. Returns a Strands model object for the
    provider selected by LLM_PROVIDER (gemini by default).

    Verified against installed strands-agents==1.59.0:
    - BedrockModel(model_id=...) under strands.models.bedrock.
    - GeminiModel(client_args={"api_key": ...}, model_id=..., params={...}) under
      strands.models.gemini; params maps onto google.genai.types.GenerateContentConfig
      (temperature, max_output_tokens). Requires the `google-genai` package.
    - Qwen is routed through OpenAIModel(client_args={"api_key", "base_url"}, model_id=...)
      under strands.models.openai, since Strands has no dedicated Qwen provider and
      Qwen's DashScope endpoint is OpenAI-compatible. Requires the `openai` package.
      UNTESTED end to end -- no Qwen credentials available in this environment.
    """
    settings = get_settings()
    model_id = {
        "fast": settings.model_fast,
        "strong": settings.model_strong,
        "orch": settings.model_orch,
    }[tier]
    limits = _TIER_LIMITS[tier]

    if settings.llm_provider == "bedrock":
        from strands.models.bedrock import BedrockModel
        return BedrockModel(model_id=model_id, **limits)

    if settings.llm_provider == "qwen":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": settings.qwen_api_key, "base_url": settings.qwen_base_url},
            model_id=model_id,
            params=limits,
        )

    from strands.models.gemini import GeminiModel
    gemini_params = {"temperature": limits["temperature"], "max_output_tokens": limits["max_tokens"]}
    return GeminiModel(
        client_args={"api_key": settings.gemini_api_key},
        model_id=model_id,
        params=gemini_params,
    )
