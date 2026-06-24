"""Day-1 smoke test: confirm each configured backend answers and reports metrics.

Run:  python -m scripts.smoke_test
"""
from src.llm import build_providers

SYSTEM = "You are an energy-management assistant for a factory (FEMS)."
PROMPT = (
    "In one sentence, what is the single most effective way to reduce a "
    "factory's electricity peak-demand charges?"
)


def main() -> None:
    providers = build_providers()
    if not providers:
        print("No providers available. Start Ollama and/or set API keys in .env.")
        return

    print(f"{'provider':<10} {'latency':>8} {'in':>6} {'out':>6} {'cost($)':>10}")
    print("-" * 46)
    for p in providers:
        try:
            r = p.generate(SYSTEM, PROMPT, max_tokens=256)
        except Exception as e:  # noqa: BLE001 - smoke test: report and continue
            print(f"{p.provider:<10} ERROR: {e}")
            continue
        print(
            f"{r.provider:<10} {r.latency_s:>7.2f}s {r.input_tokens:>6} "
            f"{r.output_tokens:>6} {r.cost_usd:>10.5f}"
        )
        print(f"  -> {r.text.strip()[:200]}\n")


if __name__ == "__main__":
    main()
