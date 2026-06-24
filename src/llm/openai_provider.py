"""GPT inference via the official OpenAI SDK."""
import time

from openai import OpenAI

import config
from .base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    provider = "openai"

    def __init__(self, model: str):
        self.model = model
        self._client = OpenAI()  # reads OPENAI_API_KEY

    def generate(self, system: str, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        latency = time.perf_counter() - start
        text = resp.choices[0].message.content or ""
        in_tok = resp.usage.prompt_tokens
        out_tok = resp.usage.completion_tokens
        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_s=latency,
            cost_usd=config.compute_cost(self.model, in_tok, out_tok),
        )
