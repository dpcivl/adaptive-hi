"""Common interface so Ollama / Claude / GPT are interchangeable and comparable.

The whole project hinges on this: every backend takes the same (system, prompt)
and returns the same LLMResponse carrying the metrics we compare on — quality
(text), speed (latency), and cost (tokens -> USD).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    provider: str  # "ollama" | "claude" | "openai"
    model: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    cost_usd: float  # 0.0 for local inference (no per-token API charge)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def tokens_per_sec(self) -> float:
        return self.output_tokens / self.latency_s if self.latency_s > 0 else 0.0


class LLMProvider(ABC):
    """A single text-in / text-out backend that reports tokens, latency, and cost."""

    provider: str
    model: str

    @abstractmethod
    def generate(self, system: str, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        """Run one completion and return the answer plus its metrics."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
