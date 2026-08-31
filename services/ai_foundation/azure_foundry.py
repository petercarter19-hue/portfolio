"""Microsoft Foundry Responses adapter with an explicit fail-closed spend ledger.

Prompts and output exist only for the duration of ``answer``.  Usage callbacks
contain token counts and cost estimates, never request, source, or answer text.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from threading import Lock
from typing import Any, Protocol
from urllib.parse import urlsplit

from .contracts import AIRequest, SourceVersion
from .errors import ExecutionLimitError, ProviderUnavailableError

FOUNDRY_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
DEFAULT_DEPLOYMENT = "gpt-5.6-luna"
MAX_RESPONSE_BYTES = 1_000_000
_dumps_json = json.dumps


class TokenProvider(Protocol):
    def __call__(self) -> str: ...


class HTTPResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


class HTTPTransport(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: tuple[float, float],
    ) -> HTTPResponse: ...


@dataclass(frozen=True)
class _UrllibResponse:
    status_code: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect.

    ``urllib``'s default redirect handler keeps the ``Authorization`` header
    when it follows a 3xx, and performs no same-origin check on the new
    location.  The endpoint allowlist validates only the first hop, so a
    redirect would carry the Entra access token to an unvalidated host.  A
    single inference POST to an already-validated origin has no legitimate
    reason to redirect, so treat any 3xx as the provider being unavailable.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibTransport:
    """Small default transport so the provider adds no SDK dependency."""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: tuple[float, float],
    ) -> _UrllibResponse:
        request = urllib.request.Request(
            url,
            data=_dumps_json(json, separators=(",", ":")).encode("utf-8"),
            method="POST",
        )
        for name, value in dict(headers).items():
            # Unredirected headers are dropped by urllib before it follows a
            # hop, so the token cannot leak even if a redirect handler is
            # reintroduced later.
            request.add_unredirected_header(name, value)
        opener = urllib.request.build_opener(_NoRedirects)
        try:
            with opener.open(request, timeout=sum(timeout)) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ProviderUnavailableError(
                        "Foundry response exceeds the bounded response size"
                    )
                return _UrllibResponse(response.status, body)
        except urllib.error.HTTPError as error:
            # The adapter needs only the status.  Never retain or expose a
            # provider error body because it can echo input fragments.
            return _UrllibResponse(error.code, b"{}")


@dataclass(frozen=True)
class LunaPriceSchedule:
    """Safety schedule in micro-USD per one million tokens.

    These defaults are a deliberate OVER-estimate, not a measurement.  No paid
    Foundry call has been made by this package, so nothing here was observed on
    a live meter.

    They are bounded above the published Azure retail maximums for GPT-5.6 Luna
    so the estimate can only err high and the hard cap can only bind early:

        source: https://prices.azure.com/api/retail/prices
                filter contains(meterName,'luna'), read 2026-08-31
        highest published non-cached input meter   $0.44 per 1M tokens
        highest published output meter             $2.64 per 1M tokens
        defaults below                             $1.00 / $6.00 per 1M tokens

    That is roughly a 2.3x margin on both sides.  The margin exists because the
    exact meter a given deployment bills against (global vs data-zone, standard
    vs provisioned, short vs long context) is not known until activation.
    Activation must still recheck the actual meter and correct the repeat count
    from the first observed run, because a retail list price is not a bill.
    """

    input_micro_usd_per_million: int = 1_000_000
    output_micro_usd_per_million: int = 6_000_000
    schedule_ref: str = "retail-bounded-safety-schedule-2026-08-31"

    def __post_init__(self) -> None:
        if self.input_micro_usd_per_million < 1:
            raise ValueError("input token price must be positive")
        if self.output_micro_usd_per_million < 1:
            raise ValueError("output token price must be positive")
        if not self.schedule_ref.strip():
            raise ValueError("price schedule reference is required")

    def estimate_micro_usd(self, *, input_tokens: int, output_tokens: int) -> int:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts cannot be negative")
        numerator = (
            input_tokens * self.input_micro_usd_per_million
            + output_tokens * self.output_micro_usd_per_million
        )
        return (numerator + 999_999) // 1_000_000


@dataclass(frozen=True)
class FoundryUsage:
    deployment: str
    input_tokens: int
    output_tokens: int
    estimated_micro_usd: int
    price_schedule_ref: str


class SpendLedger:
    """Sequential/concurrent pre-call reservations with conservative failures."""

    def __init__(self, *, hard_cap_micro_usd: int, max_calls: int) -> None:
        if hard_cap_micro_usd < 1 or max_calls < 1:
            raise ValueError("spend cap and call cap must be positive")
        self.hard_cap_micro_usd = hard_cap_micro_usd
        self.max_calls = max_calls
        self._lock = Lock()
        self._calls = 0
        self._spent = 0
        self._reserved = 0

    def reserve(self, maximum_micro_usd: int) -> None:
        if maximum_micro_usd < 1:
            raise ValueError("call reservation must be positive")
        with self._lock:
            if self._calls >= self.max_calls:
                raise ExecutionLimitError("Foundry evaluation call ceiling reached")
            if (
                self._spent + self._reserved + maximum_micro_usd
                > self.hard_cap_micro_usd
            ):
                raise ExecutionLimitError("Foundry evaluation dollar ceiling reached")
            self._calls += 1
            self._reserved += maximum_micro_usd

    def settle(self, *, reserved_micro_usd: int, actual_micro_usd: int | None) -> None:
        with self._lock:
            if reserved_micro_usd > self._reserved:
                raise RuntimeError("spend reservation accounting mismatch")
            self._reserved -= reserved_micro_usd
            # A transport/provider failure may still be billed.  Fail closed by
            # charging the complete reservation when usage is unavailable.
            self._spent += (
                reserved_micro_usd if actual_micro_usd is None else actual_micro_usd
            )
            if self._spent > self.hard_cap_micro_usd:
                raise ExecutionLimitError(
                    "Foundry provider exceeded the dollar ceiling"
                )

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "calls": self._calls,
                "spent_micro_usd": self._spent,
                "reserved_micro_usd": self._reserved,
                "hard_cap_micro_usd": self.hard_cap_micro_usd,
                "max_calls": self.max_calls,
            }


def usd_to_micro_usd(value: str | Decimal) -> int:
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("USD amount must be numeric") from error
    if not amount.is_finite() or amount <= 0:
        raise ValueError("USD amount must be positive")
    return int((amount * 1_000_000).quantize(Decimal(1), rounding=ROUND_CEILING))


class AzureFoundryResponsesProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        token_provider: TokenProvider,
        deployment: str = DEFAULT_DEPLOYMENT,
        transport: HTTPTransport | None = None,
        price_schedule: LunaPriceSchedule | None = None,
        spend_ledger: SpendLedger,
        usage_sink: Callable[[FoundryUsage], None] | None = None,
        maximum_input_tokens: int = 1_500,
        maximum_output_tokens: int = 700,
    ) -> None:
        parsed_endpoint = urlsplit(endpoint)
        hostname = (parsed_endpoint.hostname or "").casefold()
        if (
            parsed_endpoint.scheme != "https"
            or parsed_endpoint.username is not None
            or parsed_endpoint.password is not None
            or parsed_endpoint.port not in (None, 443)
            or parsed_endpoint.path not in ("", "/")
            or parsed_endpoint.query
            or parsed_endpoint.fragment
            or not hostname.endswith(".openai.azure.com")
            or hostname == ".openai.azure.com"
        ):
            raise ValueError("Foundry endpoint must be an Azure OpenAI HTTPS origin")
        normalized = f"https://{hostname}"
        if not deployment.strip():
            raise ValueError("Foundry deployment is required")
        if maximum_input_tokens < 1 or maximum_output_tokens < 1:
            raise ValueError("token ceilings must be positive")
        self._url = f"{normalized}/openai/v1/responses"
        self._token_provider = token_provider
        self._deployment = deployment
        self._transport = transport or UrllibTransport()
        self._price = price_schedule or LunaPriceSchedule()
        self._ledger = spend_ledger
        self._usage_sink = usage_sink
        self._maximum_input_tokens = maximum_input_tokens
        self._maximum_output_tokens = maximum_output_tokens

    @staticmethod
    def _instructions() -> str:
        return (
            "Return one JSON object only. Preserve evidence and interpretation as "
            "separate claims. Cite only supplied source_version_key values and exact "
            "zero-based character spans. Unknowns must be explicit boundary claims. "
            "Required top-level fields: answer_id, state, summary, claims, "
            "follow_up_questions, handoff, model_name, prompt_contract_version."
        )

    @staticmethod
    def _input(request: AIRequest, sources: Sequence[SourceVersion]) -> str:
        payload = {
            "request": {
                "request_id": request.request_id,
                "product": request.product,
                "purpose": request.purpose.value,
                "audience": request.audience.value,
                "subject_key": request.subject_key,
                "question": request.question,
            },
            "sources": [
                {
                    "source_version_key": source.source_version_key,
                    "title": source.title,
                    "content": source.content,
                }
                for source in sources
            ],
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _output_text(payload: Mapping[str, Any]) -> str:
        output = payload.get("output")
        if not isinstance(output, Sequence) or isinstance(output, (str, bytes)):
            raise ProviderUnavailableError("Foundry response has no bounded output")
        texts: list[str] = []
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, Sequence) or isinstance(content, (str, bytes)):
                continue
            for part in content:
                if (
                    isinstance(part, Mapping)
                    and part.get("type") == "output_text"
                    and isinstance(part.get("text"), str)
                ):
                    texts.append(part["text"])
        if len(texts) != 1:
            raise ProviderUnavailableError(
                "Foundry response output is missing or ambiguous"
            )
        return texts[0]

    def answer(
        self,
        request: AIRequest,
        sources: tuple[SourceVersion, ...],
    ) -> Mapping[str, Any]:
        instructions = self._instructions()
        input_text = self._input(request, sources)
        # One model token cannot contain less than one UTF-8 byte.  Bounding
        # the complete UTF-8 input at the token reservation therefore makes
        # the pre-call reservation conservative without provider tokenization.
        input_bytes = len(instructions.encode("utf-8")) + len(
            input_text.encode("utf-8")
        )
        if input_bytes > self._maximum_input_tokens:
            raise ExecutionLimitError("Foundry input exceeds its prepaid ceiling")
        reservation = self._price.estimate_micro_usd(
            input_tokens=self._maximum_input_tokens,
            output_tokens=self._maximum_output_tokens,
        )
        self._ledger.reserve(reservation)
        settled = False
        try:
            token = self._token_provider()
            if not isinstance(token, str) or not token.strip():
                raise ProviderUnavailableError("Foundry bearer token is unavailable")
            response = self._transport.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._deployment,
                    "instructions": instructions,
                    "input": input_text,
                    "max_output_tokens": self._maximum_output_tokens,
                    "store": False,
                },
                timeout=(5.0, 90.0),
            )
            if response.status_code < 200 or response.status_code >= 300:
                raise ProviderUnavailableError(
                    f"Foundry request failed with HTTP {response.status_code}"
                )
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise ProviderUnavailableError("Foundry response is not an object")
            usage = payload.get("usage")
            if not isinstance(usage, Mapping):
                raise ProviderUnavailableError("Foundry response has no usage record")
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if (
                isinstance(input_tokens, bool)
                or not isinstance(input_tokens, int)
                or isinstance(output_tokens, bool)
                or not isinstance(output_tokens, int)
                or input_tokens < 0
                or output_tokens < 0
            ):
                raise ProviderUnavailableError("Foundry token usage is malformed")
            actual = self._price.estimate_micro_usd(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            settled = True
            self._ledger.settle(
                reserved_micro_usd=reservation,
                actual_micro_usd=actual,
            )
            if self._usage_sink is not None:
                try:
                    self._usage_sink(
                        FoundryUsage(
                            deployment=self._deployment,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            estimated_micro_usd=actual,
                            price_schedule_ref=self._price.schedule_ref,
                        )
                    )
                except Exception:  # noqa: BLE001,S110
                    # Diagnostics must not alter the provider result.
                    pass
            try:
                decoded = json.loads(self._output_text(payload))
            except (json.JSONDecodeError, TypeError) as error:
                raise ProviderUnavailableError("Foundry output is not JSON") from error
            if not isinstance(decoded, Mapping):
                raise ProviderUnavailableError("Foundry output JSON is not an object")
            return decoded
        except ProviderUnavailableError:
            raise
        except Exception as error:
            if isinstance(error, ExecutionLimitError):
                raise
            raise ProviderUnavailableError("Foundry provider is unavailable") from error
        finally:
            if not settled:
                self._ledger.settle(
                    reserved_micro_usd=reservation,
                    actual_micro_usd=None,
                )
