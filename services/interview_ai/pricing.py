"""Integer-exact pricing for Interview AI telemetry (interview-ai-pricing@1).

The immutable pricing table is a committed file; its identity
(`pricing_schedule_id`) is the SHA-256 of the file's exact bytes. Floating
point is prohibited on this path. When usage is absent, malformed, or not
unambiguously priceable, cost and pricing identity stay null while valid
token counts are preserved (frozen contract §4.4).
"""

import json
from pathlib import Path

from services.interview_ai.identity import sha256_hex

ROOT = Path(__file__).resolve().parents[2]
PRICING_TABLE_PATH = (
    ROOT / "prompts" / "interview" / "contracts" / "interview-ai-pricing-1.json"
)

_cached_table = None


def _load_table():
    global _cached_table
    if _cached_table is None:
        raw = PRICING_TABLE_PATH.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
        entries = {}
        for entry in parsed["entries"]:
            input_rate = entry["input_microusd_per_token"]
            output_rate = entry["output_microusd_per_token"]
            if not isinstance(input_rate, int) or not isinstance(output_rate, int):
                raise ValueError("pricing rates must be integers")
            entries[entry["model"]] = (input_rate, output_rate)
        _cached_table = {"schedule_id": sha256_hex(raw), "entries": entries}
    return _cached_table


def reset_pricing_cache():
    global _cached_table
    _cached_table = None


def _usage_component(usage, name):
    value = getattr(usage, name, None)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return False  # malformed
    return value


def price_usage(model, usage):
    """Return (provider_usage, cost_microusd, pricing_schedule_id).

    ``provider_usage`` is {"input_tokens", "output_tokens"} whenever the
    provider returned a valid usage object, independently of priceability;
    cost and schedule id are non-null together iff the usage is
    synchronously and unambiguously priceable from the table.
    """
    if usage is None:
        return None, None, None
    input_tokens = _usage_component(usage, "input_tokens")
    output_tokens = _usage_component(usage, "output_tokens")
    if (
        input_tokens is None or input_tokens is False or input_tokens < 0
        or output_tokens is None or output_tokens is False or output_tokens < 0
    ):
        return None, None, None
    provider_usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}

    # Any nonzero usage component outside plain input/output makes the row
    # ambiguous under this table (e.g. cache tokens); tokens are preserved,
    # cost stays null and is never patched later.
    for extra in ("cache_creation_input_tokens", "cache_read_input_tokens"):
        extra_value = _usage_component(usage, extra)
        if extra_value is False or (isinstance(extra_value, int) and extra_value != 0):
            return provider_usage, None, None

    table = _load_table()
    rates = table["entries"].get(model)
    if rates is None:
        return provider_usage, None, None
    cost = input_tokens * rates[0] + output_tokens * rates[1]
    if cost < 0 or cost > 2**63 - 1:
        return provider_usage, None, None
    return provider_usage, cost, table["schedule_id"]
