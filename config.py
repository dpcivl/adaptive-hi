"""Central configuration: model selection and pricing for cost comparison."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Model selection (override via .env) ---
# EXAONE 3.5 (LG, Korean-specialized) — chosen after qwen2.5:7b bled Chinese on
# Korean FEMS answers even at low temperature (model-level language bias).
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "exaone3.5:7.8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

OLLAMA_HOST = os.getenv("OLLAMA_HOST")  # None -> default http://localhost:11434

# --- RAG paths ---
DOCS_DIR = os.getenv("DOCS_DIR", "data/documents")
CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
# Drop chunks whose readable-char ratio (Hangul + ASCII) falls below this —
# filters TOC dot-leader noise and font-garble. Observed in THIS corpus: bad
# chunks <=0.25, clean prose >=0.94; 0.5 sits in that wide gap with margin against
# false-positives on punctuation-dense text. Not a guaranteed property of the
# metric (see documents.readable_ratio). Tunable via env.
MIN_READABLE_RATIO = float(os.getenv("MIN_READABLE_RATIO", "0.5"))

# --- Energy data ---
ENERGY_CSV = os.getenv("ENERGY_CSV", "data/energy/plant_energy.csv")
STEEL_CSV = os.getenv("STEEL_CSV", "data/real_energy/steel_industry.csv")

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
