"""Local inference via Ollama. No API cost; latency reflects the 6GB-VRAM box."""
import time

import ollama

from .base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    provider = "ollama"

    def __init__(self, model: str, host: str | None = None):
        self.model = model
        self._client = ollama.Client(host=host) if host else ollama.Client()

    def generate(self, system: str, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        start = time.perf_counter()
        resp = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            options={"num_predict": max_tokens},
        )
        latency = time.perf_counter() - start
        return LLMResponse(
            text=resp["message"]["content"],
            provider=self.provider,
            model=self.model,
            input_tokens=resp.get("prompt_eval_count", 0) or 0,
            output_tokens=resp.get("eval_count", 0) or 0,
            latency_s=latency,
            cost_usd=0.0,  # local: electricity only, tracked separately if needed
        )
