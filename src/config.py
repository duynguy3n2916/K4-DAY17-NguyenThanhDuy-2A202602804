from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from model_provider import ProviderConfig, normalize_provider


@dataclass
class LabConfig:
    """Student TODO: define the shared configuration for the lab.

    Hints:
    - Keep paths for the repo root, dataset directory, and state directory.
    - Add compact-memory settings such as threshold and number of messages to keep.
    - Add provider settings for `openai`, `custom`, `gemini`, `anthropic`, `ollama`, and `openrouter`.
    """

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Student TODO: load environment variables and return a LabConfig.

    Pseudocode:
    1. Resolve the repo root or default to the current file parent.
    2. Optionally load values from `.env`.
    3. Create `state/` if it does not exist.
    4. Return a populated LabConfig instance.
    """

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()

    # TODO: read env vars for one of the supported providers.
    # Example knobs:
    # - LLM_PROVIDER / LLM_MODEL
    # - OPENAI_API_KEY
    # - GEMINI_API_KEY
    # - ANTHROPIC_API_KEY
    # - OLLAMA_BASE_URL
    # - OPENROUTER_API_KEY
    # - CUSTOM_BASE_URL / CUSTOM_API_KEY
    # TODO: create `root / "state"`.
    # TODO: choose sensible defaults for compact memory.

    load_dotenv(root / ".env")
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    model_defaults = {
        "openai": "gpt-4o-mini",
        "custom": "custom-model",
        "gemini": "gemini-2.0-flash",
        "anthropic": "claude-3-5-haiku-latest",
        "ollama": "llama3.2",
        "openrouter": "openai/gpt-4o-mini",
    }
    key_env = {
        "openai": "OPENAI_API_KEY",
        "custom": "CUSTOM_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    url_env = {"custom": "CUSTOM_BASE_URL", "ollama": "OLLAMA_BASE_URL"}

    def provider_config(prefix: str, fallback_provider: str | None = None) -> ProviderConfig:
        provider = normalize_provider(os.getenv(f"{prefix}_PROVIDER", fallback_provider or "openai"))
        default_model = model_defaults[provider]
        if prefix == "JUDGE" and provider == model.provider:
            default_model = model.model_name
        return ProviderConfig(
            provider=provider,
            model_name=os.getenv(f"{prefix}_MODEL", default_model),
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", "0")),
            api_key=os.getenv(key_env[provider]) if provider in key_env else None,
            base_url=os.getenv(url_env[provider]) if provider in url_env else None,
        )

    model = provider_config("LLM")
    judge_model = provider_config("JUDGE", model.provider)
    compact_threshold_tokens = int(os.getenv("COMPACT_THRESHOLD_TOKENS", "1200"))
    compact_keep_messages = int(os.getenv("COMPACT_KEEP_MESSAGES", "4"))
    if compact_threshold_tokens <= 0 or compact_keep_messages < 1:
        raise ValueError("Compact threshold must be positive and keep_messages >= 1")

    return LabConfig(
        base_dir=root,
        data_dir=root / "data",
        state_dir=state_dir,
        compact_threshold_tokens=compact_threshold_tokens,
        compact_keep_messages=compact_keep_messages,
        model=model,
        judge_model=judge_model,
    )
