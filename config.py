"""Central configuration: model selection and pricing for cost comparison."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Model selection (override via .env) ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

OLLAMA_HOST = os.getenv("OLLAMA_HOST")  # None -> default http://localhost:11434

# --- Pricing: USD per 1,000,000 tokens, as (input_rate, output_rate). ---
# Claude rates are current as of this project. VERIFY OpenAI rates at
# https://openai.com/api/pricing/ before quoting them — they change.
PRICING = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """USD cost for one request. Returns 0.0 for unknown (e.g. local) models."""
    if model not in PRICING:
        return 0.0
    in_rate, out_rate = PRICING[model]
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
