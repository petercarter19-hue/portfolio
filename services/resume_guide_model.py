"""One provisional Guide selection; explicit ledger-purpose ceilings, no funding."""
from types import MappingProxyType

from services.ai_foundation.contracts import guide_model_variant,validate_guide_variant_bindings,STRUCTURED_MODEL_SOL61


GUIDE_DEFAULT_VARIANTS = MappingProxyType({"interview":"turn.sol61_medium","extraction":"organize.sol61_medium"})
_PURPOSE_CEILINGS = MappingProxyType({
    "acceptance":MappingProxyType({"interview":105000000,"extraction":30000000}),
    "evaluation":MappingProxyType({"interview":65000000,"extraction":65000000}),
})


def selected_guide_variant(profile, *, variant=None):
    if profile not in GUIDE_DEFAULT_VARIANTS:
        raise ValueError("Closed Guide profile required")
    return guide_model_variant(GUIDE_DEFAULT_VARIANTS[profile] if variant is None else variant,profile=profile)


def guide_budget_ceiling(profile, variant, *, purpose="acceptance"):
    record = selected_guide_variant(profile,variant=variant)
    if not isinstance(purpose,str) or purpose not in _PURPOSE_CEILINGS:
        raise ValueError("Explicit approved Guide ledger purpose required")
    if record.model_name != STRUCTURED_MODEL_SOL61:
        return 5000000 if profile=="interview" else 6000000
    return _PURPOSE_CEILINGS[purpose][profile]


def validate_guide_settings(profile, settings, *, purpose="acceptance"):
    """Validate runtime data; the injected ongoing port must prove real funding."""
    if type(settings) is not dict or set(settings) != {"variant","endpoint","deployment","provider","prices","budget"}:
        raise ValueError("Closed named Guide settings required")
    record = selected_guide_variant(profile,variant=settings["variant"])
    budget = settings["budget"]
    if type(budget) is not dict:
        raise ValueError("Explicit Guide budget required")
    contract = {"variant":record.name,"model":record.model_name,"model_version":record.model_version,
        "alias":record.deployment,"effort":record.reasoning_effort,"tier":"default","wire_bytes":record.wire_bytes,
        "input_tokens":record.input_tokens,"output_tokens":record.output_tokens,
        "safety_prices_per_million_micro_usd":[record.input_micro_usd_per_million,record.output_micro_usd_per_million]}
    allocation = {"variant":record.name,"model":record.model_name,"model_version":record.model_version,
        "reasoning_effort":record.reasoning_effort,"service_tier":"default","input_tokens":record.input_tokens,
        "output_tokens":record.output_tokens,"input_micro_usd_per_million":record.input_micro_usd_per_million,
        "output_micro_usd_per_million":record.output_micro_usd_per_million,
        "reservation_micro_usd":record.reservation_micro_usd,**budget}
    validate_guide_variant_bindings(record.name,profile=profile,settings=settings,allocation=allocation,contract=contract)
    if budget["hard_cap_micro_usd"] > guide_budget_ceiling(profile,record.name,purpose=purpose):
        raise ValueError("Guide cap exceeds its ledger-purpose ceiling")
    return record
