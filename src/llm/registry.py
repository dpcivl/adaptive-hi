"""Build the set of providers to compare, honouring available API keys."""
import os

import config
from .base import LLMProvider


def build_providers(which: tuple[str, ...] = ("ollama", "claude", "openai")) -> list[LLMProvider]:
    """Instantiate the requested providers.

    Cloud providers are skipped (with a printed note) when their API key is
    missing, so the harness still runs with whatever is configured.
    """
    providers: list[LLMProvider] = []

    if "ollama" in which:
        from .ollama_provider import OllamaProvider

        providers.append(OllamaProvider(config.OLLAMA_MODEL, host=config.OLLAMA_HOST))

    if "claude" in which:
        if os.getenv("ANTHROPIC_API_KEY"):
            from .claude_provider import ClaudeProvider

            providers.append(ClaudeProvider(config.CLAUDE_MODEL))
        else:
            print("[registry] ANTHROPIC_API_KEY not set — skipping Claude.")

    if "openai" in which:
        if os.getenv("OPENAI_API_KEY"):
            from .openai_provider import OpenAIProvider

            providers.append(OpenAIProvider(config.OPENAI_MODEL))
        else:
            print("[registry] OPENAI_API_KEY not set — skipping GPT.")

    return providers
