"""One bounded Luna selection call for public Ask Pete evidence."""

from dataclasses import asdict
import json
from pathlib import Path
from time import monotonic

from services.ai_foundation import AnswerState, GroundedAnswer
from services.ai_foundation.azure_foundry import (
    AzureFoundryResponsesProvider, LunaPriceSchedule, SpendLedger, UrllibTransport,
)
from services.ai_foundation.citation_validator import validate_grounded_answer
from services.ai_foundation.errors import ProviderUnavailableError

from .diagnostics import observed_phase, failure_reason, emit_safely
from .fact_selection import (
    build_selection_document, private_or_override_request, render_selection,
)
from .quality import validate_product_quality


DEPLOYMENT = "gpt-6-luna"
REASONING_EFFORT = "low"
PROMPT_VERSION = "ask-pete-foundry-fact-selection.v1"
MAX_INPUT_BYTES = 60_000
MAX_INPUT_TOKENS = 61_024  # conservative byte reservation plus framing
MAX_ANSWER_TOKENS = 1_024
# Compatibility for the older, separately governed qualification runner. This
# is not reserved or called by the public runtime's one-call provider.
MAX_SUPPORT_TOKENS = 2_048

SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {"type": "string", "enum": ["answer", "unknown", "clarify", "refuse"]},
        "atom_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["mode", "atom_ids"],
    "additionalProperties": False,
}


class _DeadlineTransport:
    def __init__(self, transport, deadline):
        self.transport, self.deadline = transport, deadline
        self.calls = 0
        self.observe = None

    def post(self, url, *, headers, json, timeout):
        remaining = self.deadline.remaining()
        connect = min(5.0, remaining / 4)
        if self.observe:
            self.observe("transport")
        self.calls += 1
        result = self.transport.post(
            url, headers=headers, json=json, timeout=(connect, remaining - connect),
        )
        if self.observe:
            self.observe("response_validation", result.status_code)
        self.deadline.remaining()
        return result


class _Phase(AzureFoundryResponsesProvider):
    def __init__(self, *, instructions, document, event, **kwargs):
        self.instructions, self.document, self.event = instructions, document, event
        super().__init__(**kwargs)

    def _instructions(self):
        return self.instructions

    def _input(self, _request, _sources):
        return json.dumps(self.document, ensure_ascii=False, separators=(",", ":"))

    def _output_text(self, payload):
        status = payload.get("status")
        self.event["completion_status"] = status if status in {
            "completed", "incomplete", "failed", "cancelled", "queued", "in_progress"
        } else "unknown"
        details = (payload.get("usage") or {}).get("output_tokens_details") or {}
        reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
        if type(reasoning) is int and 0 <= reasoning <= payload["usage"]["output_tokens"]:
            self.event["reasoning_tokens"] = reasoning
        if status != "completed":
            self.event["reason"] = "completion_incomplete"
            raise ProviderUnavailableError("Foundry response did not complete")
        return super()._output_text(payload)


class FoundryGroundedProvider:
    def __init__(self, *, endpoint, token_provider, subject_display_name,
                 prompt_path: Path, deadline, transport=None, event_sink=None,
                 spend_ledger=None):
        self.endpoint, self.token_provider = endpoint, token_provider
        self.subject_display_name = subject_display_name
        self.prompt = prompt_path.read_text(encoding="utf-8")
        self.deadline = deadline
        self.transport = _DeadlineTransport(transport or UrllibTransport(), deadline)
        self.event_sink = event_sink
        self.price = LunaPriceSchedule()
        cap = self.price.estimate_micro_usd(
            input_tokens=MAX_INPUT_TOKENS, output_tokens=MAX_ANSWER_TOKENS,
        )
        self.ledger = spend_ledger or SpendLedger(
            hard_cap_micro_usd=cap, max_calls=1,
        )

    def _emit(self, event):
        emit_safely(self.event_sink, event)

    def _call(self, request, sources, document):
        self.deadline.remaining()
        started = monotonic()
        calls_before = self.transport.calls
        event = {
            "request_id": request.request_id, "phase": "generation",
            "deployment": DEPLOYMENT, "reasoning_effort": REASONING_EFFORT,
            "usage_available": False, "outcome": "unavailable", "stage": "request",
        }

        def observe(stage, status=None):
            event["stage"] = stage
            if type(status) is int and 100 <= status <= 599:
                event["http_status"] = status
            self._emit({
                "request_id": request.request_id, "phase": "stage",
                "operation": "generation", "stage": stage, "outcome": "started",
            })

        def token():
            observe("credential")
            return self.token_provider()

        def usage(record):
            event.update(asdict(record))
            event["usage_available"] = True

        self.transport.observe = observe
        try:
            provider = _Phase(
                endpoint=self.endpoint, deployment=DEPLOYMENT, token_provider=token,
                transport=self.transport, price_schedule=self.price, spend_ledger=self.ledger,
                usage_sink=usage, maximum_input_tokens=MAX_INPUT_TOKENS,
                maximum_input_bytes=MAX_INPUT_BYTES,
                maximum_output_tokens=MAX_ANSWER_TOKENS,
                answer_reasoning_effort=REASONING_EFFORT,
                answer_json_schema=SELECTION_SCHEMA,
                instructions=self.prompt, document=document, event=event,
            )
            result = provider.answer(request, sources)
            self.deadline.remaining()
            event["outcome"] = "completed"
            return result
        except Exception as error:
            default = {"credential": "credential_unavailable",
                       "transport": "transport_unavailable"}.get(
                           event["stage"], "response_validation_unknown")
            if not 200 <= event.get("http_status", 200) < 300:
                default = "http_non_success"
            event["reason"] = failure_reason(error, event.get("reason", default))
            raise
        finally:
            self.transport.observe = None
            event["provider_calls"] = self.transport.calls - calls_before
            event["duration_ms"] = round((monotonic() - started) * 1000)
            self._emit(event)

    def answer(self, request, sources):
        # The fixed privacy refusal can finish before any credential or paid
        # request. Sources still passed the gateway's authorization beforehand.
        if private_or_override_request(request.question):
            return GroundedAnswer(
                answer_id=f"{request.request_id}:answer", state=AnswerState.REFUSED,
                summary="I can discuss only approved public professional information. I cannot answer that request.",
                model_name=DEPLOYMENT, prompt_contract_version=PROMPT_VERSION,
            )

        document, atoms = build_selection_document(
            request=request, sources=sources,
            subject_display_name=self.subject_display_name,
        )
        raw = self._call(request, sources, document)
        with observed_phase(self.event_sink, request.request_id,
                            "grounding_quality", "answer_contract"):
            answer = render_selection(
                raw=raw, atoms=atoms, request=request,
                subject_display_name=self.subject_display_name,
                model_name=DEPLOYMENT, prompt_version=PROMPT_VERSION,
            )
            answer = validate_grounded_answer(request, sources, answer)
            validate_product_quality(request.purpose, answer)
            self.deadline.remaining()
        return answer
