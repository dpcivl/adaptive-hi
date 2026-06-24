"""Claude inference via the official Anthropic SDK.

Plain (non-thinking) call so the comparison against a 7B local model is
apples-to-apples. Adaptive thinking can be enabled later for a separate
"quality ceiling" run — see README.
"""
import time

import anthropic

import config
from .base import LLMProvider, LLMResponse


class ClaudeProvider(LLMProvider):
    provider = "claude"

    def __init__(self, model: str):
        self.model = model
        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    def generate(self, system: str, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        start = time.perf_counter()
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        latency = time.perf_counter() - start
        text = next((b.text for b in resp.content if b.type == "text"), "")
        in_tok = resp.usage.input_tokens
        out_tok = resp.usage.output_tokens
        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_s=latency,
            cost_usd=config.compute_cost(self.model, in_tok, out_tok),
        )
