"""Private installation composition of the app owner's bound Azure factory ports.

Adapted from the reviewed base/Speech/public adapters with explicit private owner
and separately allocated scopes. No root fixture capture or ledger is imported.
"""
from __future__ import annotations


import inspect

from services.resume_intake_service import ResumeIntakeService
from services.my_data_extraction_adapter import MyDataExtractionAdapter
from services.resume_recording_probe import ProbedResumeTranscriptionAdapter


class _ScopedBaseResumeIntakeService(ResumeIntakeService):
    def _extract_with_adapter(self, owner, plan):
        with self._sandbox_extraction_provider.owner_scope(owner):
            return super()._extract_with_adapter(owner, plan)

    def _transcribe_recording_once(
        self, *, owner, request_id, client_key, duration, moment, data,
        audio_sha256, content_type, digest, policy
    ):
        # Both values come from the real base transcribe_recording path after
        # its closed payload/request-ID validation, inside its owner/request lock.
        with self._sandbox_native_speech.owner_scope(owner, request_id):
            return super()._transcribe_recording_once(
                owner=owner, request_id=request_id, client_key=client_key,
                duration=duration, moment=moment, data=data,
                audio_sha256=audio_sha256, content_type=content_type,
                digest=digest, policy=policy,
            )


def build_base_intake_bridge(base_service, *, extraction_provider,
                             extraction_adapter, native_speech):
    """Return a shallow dependency-preserving base ResumeIntakeService clone.

    Root passes already-built actual provider/adapter/Speech port. Only the two
    explicit provider adapters are replaced. Repository, draft/catalog/original
    storage, selected policy, document/parser/interpreter/exclusion ports,
    recording locks and every other existing dependency remain the same objects.
    Root separately assigns returned bridge to its local fixture/app config.
    """
    if type(base_service) is not ResumeIntakeService:
        raise ValueError("Exact local base ResumeIntakeService required; no Hosted SQL adoption")
    extraction_parameters = tuple(inspect.signature(ResumeIntakeService._extract_with_adapter).parameters)
    recording_parameters = tuple(inspect.signature(ResumeIntakeService._transcribe_recording_once).parameters)
    if extraction_parameters != ("self", "owner", "plan") or recording_parameters != (
        "self", "owner", "request_id", "client_key", "duration", "moment", "data",
        "audio_sha256", "content_type", "digest", "policy",
    ):
        raise ValueError("Frozen base method interface changed; root must reconcile it")
    if (not isinstance(extraction_adapter, MyDataExtractionAdapter)
            or getattr(extraction_adapter, "_provider", None) is not extraction_provider
            or not callable(getattr(extraction_provider, "owner_scope", None))):
        raise ValueError("Actual extraction adapter must use the supplied scoped provider")
    if (not isinstance(getattr(native_speech, "adapter", None), ProbedResumeTranscriptionAdapter)
            or not callable(getattr(native_speech, "owner_scope", None))):
        raise ValueError("Actual decoded-duration Speech adapter and owner scope required")
    # Do not reconstruct through __init__: it would substitute defaults or
    # inadvertently introduce SQL/services instead of the owner's memory ports.
    bridge = _ScopedBaseResumeIntakeService.__new__(_ScopedBaseResumeIntakeService)
    bridge.__dict__ = base_service.__dict__.copy()
    bridge._extraction_adapter = extraction_adapter
    bridge.transcription_adapter = native_speech.adapter
    bridge._sandbox_extraction_provider = extraction_provider
    bridge._sandbox_native_speech = native_speech
    return bridge



from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

from .provider_budget import RESERVE, FINISH
from services.speech_transcription_service import (
    SpeechTranscriptionService, SpeechTranscriptionError, SPEECH_TOKEN_SCOPE,
)
from services.resume_recording_probe import ProbedResumeTranscriptionAdapter
from services.resume_intake_transcription_adapter import RecordingIntakeError
from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY


ENDPOINT = "https://peerslate-foundry.cognitiveservices.azure.com"
API_VERSION = "2025-10-15"
# These are root-selected qualification reservations, not a Speech price quote.


def _speech_binding(owner, request_id, expected_owner):
    if not isinstance(owner, str) or owner != expected_owner or not isinstance(request_id, str):
        raise SpeechTranscriptionError("speech_unavailable")
    try:
        return owner, str(UUID(request_id))
    except ValueError:
        raise SpeechTranscriptionError("speech_unavailable") from None


class _InjectedCredential:
    def __init__(self, token_provider):
        self.token_provider = token_provider

    def get_token(self, scope):
        if scope != SPEECH_TOKEN_SCOPE:
            raise SpeechTranscriptionError("speech_auth_failed")
        token = self.token_provider()
        if not isinstance(token, str) or not token.strip():
            raise SpeechTranscriptionError("speech_auth_failed")
        return SimpleNamespace(token=token)


class NativeSpeechPort:
    """Root hook exposes port.adapter to intake, port.owner_scope to caller.

    Alternatively owner_resolver() returns (actual server owner, request UUID)
    from the current authenticated request. No member-A default exists.
    """
    def __init__(self, *, database, token_provider, owner, profile, owner_resolver=None,
                 session=None, timeout_seconds=45):
        if not callable(token_provider) or (owner_resolver is not None and not callable(owner_resolver)):
            raise ValueError("Explicit token/owner callback required")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 180:
            raise ValueError("Explicit bounded Speech timeout required")
        self.database, self.owner_resolver = database, owner_resolver
        self.owner, self.profile = owner, dict(profile)
        self._owner_binding = ContextVar("local-native-speech-owner-" + str(id(self)), default=None)
        self._admitted = ContextVar("local-native-speech-admitted-" + str(id(self)), default=None)
        self._operation = ContextVar("local-native-speech-operation-" + str(id(self)), default=None)
        import requests
        self._session = session or requests.Session()
        self._service = SpeechTranscriptionService(
            endpoint=ENDPOINT, api_version=API_VERSION,
            credential=_InjectedCredential(token_provider), session=self,
            timeout_seconds=timeout_seconds,
        )
        port = self

        class GuardedProbedAdapter(ProbedResumeTranscriptionAdapter):
            def admit_bytes(self, content_type, data, duration_seconds, policy):
                if policy != SELECTED_RESUME_ONBOARDING_POLICY:
                    raise RecordingIntakeError("probe_unavailable")
                # Existing real child decoder validates MIME/container/samples,
                # actual duration<=300s, byte bounds before any reservation.
                validated = super().admit_bytes(content_type, data, duration_seconds, policy)
                port._admitted.set((sha256(validated.data).hexdigest(), validated.content_type,
                                    validated.duration_seconds, len(validated.data)))
                return validated

            def transcribe(self, validated, policy, *, transcribe=None):
                if transcribe is not None or policy != SELECTED_RESUME_ONBOARDING_POLICY:
                    raise RecordingIntakeError("probe_unavailable")
                return super().transcribe(validated, policy)

        self.adapter = GuardedProbedAdapter(service=self)
        self.policy = SELECTED_RESUME_ONBOARDING_POLICY

    @contextmanager
    def owner_scope(self, owner, request_id):
        # Caller must bind the server-derived owner, not a client owner field.
        token = self._owner_binding.set(_speech_binding(owner, request_id, self.owner))
        try:
            yield
        finally:
            self._owner_binding.reset(token)

    def _current_binding(self):
        bound = self._owner_binding.get()
        if bound is None and self.owner_resolver is not None:
            try:
                resolved = self.owner_resolver()
                if not isinstance(resolved, (tuple, list)) or len(resolved) != 2:
                    raise SpeechTranscriptionError("speech_unavailable")
                bound = _speech_binding(resolved[0], resolved[1], self.owner)
            except Exception:
                raise SpeechTranscriptionError("speech_unavailable") from None
        if bound is None:
            raise SpeechTranscriptionError("speech_unavailable")
        return bound

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        owner, request_id = self._current_binding()
        admitted = self._admitted.get()
        if (locale != "en-US" or not isinstance(audio_bytes, bytes) or not admitted
                or admitted[0] != sha256(audio_bytes).hexdigest() or admitted[1] != content_type
                or admitted[3] != len(audio_bytes) or not 0 < admitted[2] <= 300):
            raise SpeechTranscriptionError("speech_unavailable")
        parameters = [("@UserKey", owner), ("@Scope", self.profile["scope"]), ("@RequestId", request_id),
                      ("@ReservationMicroUsd", self.profile["reservation_micro_usd"]),
                      ("@MaximumCalls", self.profile["maximum_calls"]), ("@HardCapMicroUsd", self.profile["hard_cap_micro_usd"]),
                      ("@ConcurrentRequests", self.profile["concurrent_requests"])]
        try:
            reserved = self.database.first_row(RESERVE, parameters)
            if not isinstance(reserved, dict) or reserved.get("reserved") not in (True, 1):
                raise SpeechTranscriptionError("speech_unavailable")
            self._operation.set({"request": request_id, "owner": owner, "sent": False, "evidence": None})
            # The existing real service acquires credentials inside transcribe;
            # reservation has returned committed success before that call.
            result = self._service.transcribe(audio_bytes, content_type, locale=locale)
            if not isinstance(result, dict) or not isinstance(result.get("provider_transcript"), str) or not result["provider_transcript"].strip():
                raise SpeechTranscriptionError("speech_malformed")
            from .provider_budget import identity_digest
            import math
            evidence = self._operation.get()["evidence"]
            if (evidence is None or result.get("duration_seconds") != evidence["provider_seconds"]
                    or identity_digest(result.get("provider_request_id")) != evidence["identity_sha256"]):
                raise SpeechTranscriptionError("speech_unavailable")
            event = {"phase": 1, "identity_sha256": evidence["identity_sha256"],
                     "seconds": max(1, math.ceil(max(admitted[2], evidence["provider_seconds"])))}
            self.database.settle(owner, self.profile["scope"], request_id, [event])
            return result
        except SpeechTranscriptionError as error:
            # Credential/transport/provider/empty/malformed/finish errors keep
            # the reserved active uncertainty. No finish/refund/retry/reset.
            raise SpeechTranscriptionError(error.code) from None
        except Exception:
            raise SpeechTranscriptionError("speech_unavailable") from None

    def post(self, url, **kwargs):
        """Validate raw duration before SpeechTranscriptionService coerces it."""
        from .provider_budget import identity_digest
        import math
        state = self._operation.get()
        if not state or state["sent"] or url != ENDPOINT + "/speechtotext/transcriptions:transcribe":
            raise SpeechTranscriptionError("speech_unavailable")
        state["sent"] = True
        response = self._session.post(url, **kwargs)
        try:
            if type(response.status_code) is not int or not 200 <= response.status_code < 300:
                return response
            payload = response.json()
            # Match the existing service's precedence, but exclude bools and
            # non-finite values BEFORE any float conversion can obscure them.
            if type(payload) is not dict:
                raise ValueError("Raw duration unavailable")
            milliseconds = "durationMilliseconds" in payload
            raw = payload.get("durationMilliseconds" if milliseconds else "duration")
            if type(raw) not in (int, float) or not math.isfinite(raw) or raw <= 0:
                raise ValueError("Raw duration unavailable")
            seconds = float(raw) / 1000 if milliseconds else float(raw)
            event = {"phase": 1, "identity_sha256": identity_digest(
                response.headers.get("apim-request-id") or response.headers.get("x-ms-request-id")),
                "seconds": max(1, math.ceil(max(self._admitted.get()[2], seconds)))}
            self.database.observe_overrun(state["owner"], self.profile["scope"], state["request"], [event])
            if seconds > 300:
                raise ValueError("Provider duration exceeded admitted bound")
            state["evidence"] = {"identity_sha256": event["identity_sha256"], "provider_seconds": seconds}
            # Service validation must consume the same response whose duration
            # was observed, without a second independently decoded document.
            return SimpleNamespace(status_code=response.status_code, headers=response.headers,
                                   json=lambda: payload)
        except Exception:
            raise SpeechTranscriptionError("speech_malformed") from None


def build_native_speech_port(*, database, token_provider, owner, profile, owner_resolver=None,
                             session=None, timeout_seconds=45):
    """Return NativeSpeechPort with .adapter, .policy and .owner_scope(owner,id).

    Root supplies the EXISTING SQLite port and credential callback at admission.
    This factory performs no reservation, token acquisition or provider call.
    """
    return NativeSpeechPort(database=database, token_provider=token_provider, owner=owner, profile=profile,
                            owner_resolver=owner_resolver, session=session,
                            timeout_seconds=timeout_seconds)


from contextvars import ContextVar
import hashlib
import json as json_codec
from threading import Lock
from uuid import uuid4

from services.ai_foundation.azure_foundry import UrllibTransport
from services.ai_foundation.errors import ProviderUnavailableError
from services.member_visitor_ai_service import OperationalRefusal, SingleProcessVisitorProtections
FOUNDRY_ENDPOINT = "https://peerslate-foundry.openai.azure.com"
from .provider_budget import RESERVE, FINISH

PUBLIC_PHASE_RESERVATION_MICRO_USD = 164_864
PUBLIC_ANSWER_RESERVATION_MICRO_USD = 329_728
PUBLIC_WIRE_BYTES = 65_536
PUBLIC_INPUT_TOKENS = 66_560
PUBLIC_OUTPUT_TOKENS = 16_384
_CURRENT = ContextVar('private_installation_public_lease', default=None)
_READ_ONLY = ContextVar('private_installation_read_only_runtime', default=None)


class NativePublicPort:
    scope = "single_process"
    persistence_label = "private_sqlite_completed_usage"

    def __init__(self, *, database, token_provider, owner, profile, transport=None, diagnostic=None):
        if not callable(token_provider):
            raise ValueError("Explicit deferred token callback required")
        self.database, self.owner, self.profile = database, owner, dict(profile)
        self._token, self._transport = token_provider, transport or UrllibTransport()
        self._local = SingleProcessVisitorProtections()
        self._leases, self._lock = {}, Lock()
        self.completed_metadata, self.transport = [], self
        self.diagnostic = diagnostic

    def reserve(self, client_key, limits):
        if limits.concurrent_requests != 1 or limits.cost_units_per_request != PUBLIC_ANSWER_RESERVATION_MICRO_USD:
            raise OperationalRefusal(unavailable=True)
        from dataclasses import replace
        # The durable ledger owns money. This local window only bounds request
        # count/concurrency; permanently prepaying worst-case window costs here
        # would reintroduce a six-use limit after successful low-usage settlement.
        counters = replace(limits, cost_units_per_request=1,
                           aggregate_cost_units_per_window=limits.requests_per_client_window * limits.maximum_clients)
        local, request = self._local.reserve(client_key, counters), str(uuid4())
        try:
            if not self.database.reserve({"@UserKey": self.owner, "@Scope": self.profile["scope"],
                    "@RequestId": request, "@ReservationMicroUsd": self.profile["reservation_micro_usd"],
                    "@MaximumCalls": self.profile["maximum_calls"], "@HardCapMicroUsd": self.profile["hard_cap_micro_usd"],
                    "@ConcurrentRequests": 1}):
                raise ValueError("Reservation refused")
        except Exception:
            self._local.release(local)
            raise OperationalRefusal(unavailable=True) from None
        state = {"port": self, "request_id": request, "local": local, "active": True,
                 "tokens": 0, "transports": 0, "events": [], "uncertain": False,
                 "runtime_completed": False, "source": None, "zero": False}
        if self.diagnostic is not None:
            try:
                self.diagnostic.claim(state)
            except Exception:
                self._local.release(local)
                raise OperationalRefusal(unavailable=True) from None
        with self._lock:
            self._leases[request] = state
        _CURRENT.set(state)
        return request

    def _state(self):
        state = _CURRENT.get()
        if _READ_ONLY.get() is not None or state is None or state["port"] is not self or not state["active"]:
            raise ProviderUnavailableError("Exact public reservation required")
        return state

    def token_provider(self):
        state = self._state()
        if state["uncertain"] or state["tokens"] >= 2 or state["tokens"] != len(state["events"]):
            state["uncertain"] = True
            raise ProviderUnavailableError("Public phase ceiling reached")
        state["tokens"] += 1
        try:
            return self._token()
        except Exception:
            state["uncertain"] = True
            raise ProviderUnavailableError("Public credentials unavailable") from None

    def post(self, url, *, headers, json, timeout):
        from .provider_budget import identity_digest, natural
        state = self._state()
        if (state["uncertain"] or state["tokens"] != state["transports"] + 1 or state["transports"] >= 2
                or url != FOUNDRY_ENDPOINT + "/openai/v1/responses" or json.get("model") != "gpt-6-luna"
                or json.get("store") is not False or json.get("max_output_tokens") != PUBLIC_OUTPUT_TOKENS
                or json.get("background", False) is not False or json.get("stream", False) is not False
                or json.get("reasoning") != {"effort": "low"}
                or len(json_codec.dumps(json, separators=(",", ":")).encode("utf-8")) > PUBLIC_WIRE_BYTES):
            state["uncertain"] = True
            raise ProviderUnavailableError("Public wire binding unavailable")
        state["transports"] += 1
        try:
            response = self._transport.post(url, headers=headers, json=json, timeout=timeout)
            payload = response.json()
            if self.diagnostic is not None:
                self.diagnostic.capture(state, {"phase": state["transports"], "wire": json,
                    "http_status": response.status_code, "native_response": payload})
            if (type(response.status_code) is not int or response.status_code != 200 or type(payload) is not dict
                    or payload.get("status") != "completed" or payload.get("model") != "gpt-6-luna"):
                raise ValueError("Native public completion unavailable")
            event = {"phase": len(state["events"]) + 1, "identity_sha256": identity_digest(payload.get("id")),
                     "input_tokens": natural(payload["usage"]["input_tokens"]),
                     "output_tokens": natural(payload["usage"]["output_tokens"])}
            state["events"].append(event)
            self.database.observe_overrun(self.owner, self.profile["scope"], state["request_id"], state["events"])
            _, overrun = self.database.usage(self.profile["scope"], state["events"])
            if overrun:
                raise ValueError("Native public envelope exceeded")
            return response
        except Exception:
            state["uncertain"] = True
            raise ProviderUnavailableError("Public transport accounting unavailable") from None

    def finish(self, lease):
        # This callback also runs during exception cleanup. It is never completion
        # authority; only CompletionRuntime can latch the full successful path.
        with self._lock:
            if lease not in self._leases:
                raise OperationalRefusal(unavailable=True)

    def release(self, lease):
        with self._lock:
            state = self._leases.pop(lease, None)
        if state is None:
            return
        try:
            if state["runtime_completed"] and not state["uncertain"]:
                self.database.settle(self.owner, self.profile["scope"], state["request_id"],
                                     state["events"], zero_completion=state["zero"])
        except Exception:
            raise OperationalRefusal(unavailable=True) from None
        finally:
            state["active"] = False
            self._local.release(state["local"])
            self.completed_metadata.append({"request_id": state["request_id"], "credential_attempts": state["tokens"],
                "transport_attempts": state["transports"], "native_events": state["events"],
                "uncertain": state["uncertain"], "completed": state["runtime_completed"]})
            if self.diagnostic is not None:
                self.diagnostic.capture(state, {"terminal": True, "uncertain": state["uncertain"],
                    "runtime_completed": state["runtime_completed"], "transports": state["transports"]})


class BoundPublicSources:
    """Delegate source authority unchanged, recording only this invocation's load."""
    def __init__(self, source, port):
        self.source, self.port = source, port

    def __getattr__(self, name):
        return getattr(self.source, name)

    def _load(self, method, argument):
        from services.member_visitor_ai_sources import EligibleSources
        from services.resume_publication_contracts import UsePurpose
        read_only = _READ_ONLY.get() is self.port
        state = None if read_only else self.port._state()
        bundle = getattr(self.source, method)(argument)
        if (type(bundle) is not EligibleSources or bundle.context.subject_key != self.port.owner
                or bundle.context.purpose not in {UsePurpose.VISITOR_AI, UsePurpose.OWNER_VISITOR_AI_PREVIEW}
                or (state is not None and state["source"] is not None)):
            if state is not None:
                state["uncertain"] = True
            raise OperationalRefusal(unavailable=True)
        if state is not None:
            state["source"] = bundle
        return bundle

    def load_guest(self, slug):
        return self._load("load_guest", slug)

    def load_preview(self, binding):
        return self._load("load_preview", binding)


from services.member_visitor_ai_service import VisitorAiRuntime, VisitorAnswer, ResultState
from services.resume_publication_contracts import ReadState


class CompletionRuntime(VisitorAiRuntime):
    """Retain the original deadlines/authorization/close lifecycle and prove success."""
    @classmethod
    def adopt(cls, runtime, source):
        from dataclasses import replace
        if type(runtime) is not VisitorAiRuntime:
            raise ValueError("Exact public runtime required")
        result = cls.__new__(cls)
        result.__dict__ = runtime.__dict__.copy()
        result.source = source
        read_limits = replace(runtime.limits, cost_units_per_request=1,
            aggregate_cost_units_per_window=runtime.limits.requests_per_client_window * runtime.limits.maximum_clients)
        result.read_runtime = VisitorAiRuntime(read_limits, SingleProcessVisitorProtections(), scope="single_process")
        return result

    def run_response(self, callback, finalizer, *, client_key):
        from flask import has_request_context, request
        if _READ_ONLY.get() is not None:
            raise OperationalRefusal(unavailable=True)
        # These source/citation reads have no inference path. Their normal
        # deadline/concurrency controls remain; they cannot consume AI allowance.
        if has_request_context() and request.method == "GET" and request.endpoint in {
                "resume_publication.preview_ai_sources", "resume_publication.preview_ai_citation",
                "resume_publication.guest_ai_citation"}:
            def read_context(function):
                def invoke(*args):
                    token = _READ_ONLY.set(self.protections)
                    try:
                        return function(*args)
                    finally:
                        _READ_ONLY.reset(token)
                return invoke
            return self.read_runtime.run_response(read_context(callback), read_context(finalizer), client_key=client_key)
        return super().run_response(callback, finalizer, client_key=client_key)

    def _bounded(self, callback, finalizer, *, client_key):
        bound = {}
        def completed_callback():
            state = self.protections._state()
            bound["state"] = state
            value = callback()
            if (type(value) is not VisitorAnswer or value.state not in {
                    ResultState.SUPPORTED, ResultState.UNSUPPORTED, ResultState.AMBIGUOUS}
                    or state["source"] is None or state["uncertain"]):
                raise OperationalRefusal(unavailable=True)
            if not state["events"]:
                if (state["tokens"] != 0 or state["transports"] != 0 or state["source"].sources
                        or value.state is not ResultState.UNSUPPORTED):
                    raise OperationalRefusal(unavailable=True)
                state["zero"] = True
            elif not (1 <= len(state["events"]) <= 2
                      and state["tokens"] == state["transports"] == len(state["events"])):
                raise OperationalRefusal(unavailable=True)
            return value
        def completed_finalizer(value):
            state = bound["state"]
            if self.source.recheck(state["source"]) is not ReadState.CURRENT:
                raise OperationalRefusal(unavailable=True)
            response = finalizer(value)
            if type(getattr(response, "status_code", None)) is not int or response.status_code != 200:
                raise OperationalRefusal(unavailable=True)
            return response
        # The route wraps its callback and finalizer separately. Our additional
        # source fence must also retain the authenticated request context while
        # it runs on the worker, before entering the route's wrapped finalizer.
        from flask import copy_current_request_context, has_request_context
        if has_request_context():
            completed_finalizer = copy_current_request_context(completed_finalizer)
        try:
            result, release = super()._bounded(completed_callback, completed_finalizer, client_key=client_key)
            # Parent returned after callback, finalizer AND its last deadline.
            # Cleanup on timeout never reaches this latch, even if worker finishes.
            bound["state"]["runtime_completed"] = True
            return result, release
        except Exception:
            if "state" in bound:
                bound["state"]["uncertain"] = True
            raise

    def close(self):
        super().close()
        self.read_runtime.close()



def build_native_public_port(*, database, token_provider, owner, profile, transport=None):
    return NativePublicPort(database=database, token_provider=token_provider, owner=owner, profile=profile, transport=transport)


ALLOCATION_SHA256 = "0fb360b1315fa7b7695f41881bdbfc4f89dfccd2b1eb2a8ae6a15eeea931965e"
FACTORY_SHA256 = "4c4f9275478de86523004c9865f258a59c8bd0ecb386fa0229be89f3cddcb54e"
SUCCESSOR_FACTORY_SHA256 = "5450a759955bf8be6f4766e785410fe7271ae0f110764fff29eab70a99929ae8"
ONBOARDING_FACTORY_SHA256 = "d5d09972f68ad646c0c059161fcedf131b2d77cfe4c5c022d294e71c28de95e6"
CONVERSATION_FACTORY_SHA256 = "17d249320fd0c951438cafb728c17e9672107454f539cd4d4866c77168c3512b"
ONGOING_BINDINGS = {
    "allocation_sha256": ALLOCATION_SHA256,
    "contract_sha256": "8e47bfa88ce4a46f0e11d78a056b2865710957d8325b378e68dc8d892c63a8dd",
    "zero_dispatch_addendum_sha256": "ad3c55ac01a9453f14484010c0adc64bf5f3608fcf950132f5d2c691ff623a16",
}
AZURE_SUBSCRIPTION = "bd0ecf48-6940-4fd3-9687-3eaf72469d67"


def ordinary_configuration_bytes(path):
    """Take one byte snapshot from an ordinary configuration path."""
    from pathlib import Path
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("Ordinary bound configuration file required")
    return path.read_bytes()


def bound_document(path, expected):
    """Read reviewed bytes, not an editable claim that their hash was checked."""
    data = ordinary_configuration_bytes(path)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Reviewed configuration binding changed")
    return json_codec.loads(data)


def bound_factory(data, *, for_promotion=False):
    allowed = (SUCCESSOR_FACTORY_SHA256, ONBOARDING_FACTORY_SHA256, CONVERSATION_FACTORY_SHA256,
               PRIVATE_DELIVERY_FACTORY_SHA256, PRIVATE_DIAGNOSTIC_DELIVERY_FACTORY_SHA256,
               PRIVATE_FIELD_CONTRACT_DELIVERY_FACTORY_SHA256, PRIVATE_D01_BINDING_DELIVERY_FACTORY_SHA256,
               PRIVATE_PREVIEW_FENCE_DELIVERY_FACTORY_SHA256, PRIVATE_CORRECTED_DELIVERY_FACTORY_SHA256,
               PRIVATE_SLICE_1A_DELIVERY_FACTORY_SHA256, PRIVATE_TESTER_ROUND_DELIVERY_FACTORY_SHA256,
               PRIVATE_ROUND2_DELIVERY_FACTORY_SHA256)
    if not for_promotion:
        allowed += (FACTORY_SHA256,)
    if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() not in allowed:
        raise ValueError("Reviewed factory binding changed")
    return json_codec.loads(data)


PRIVATE_DELIVERY_FACTORY_SHA256 = "e64b1454dfc7bddb1c86a149c5914a47191e69ffceb2c9eeede07d7332edb64e"
PRIVATE_DIAGNOSTIC_DELIVERY_FACTORY_SHA256 = "02da9db67c221ec6a0a80f31d9859c2b4e5f8f4b6686c4658f65c3cb9246fdf4"
PRIVATE_FIELD_CONTRACT_DELIVERY_FACTORY_SHA256 = "88432919501a4d6e1a3abc2270464cc5c221aa3a4c1708ebe554aa4c3b4c0042"
PRIVATE_D01_BINDING_DELIVERY_FACTORY_SHA256 = "0c583fa6cd6ad4891c2426de5ec648f1d5ef0418b88a210eaaffda062cf2bf37"
PRIVATE_PREVIEW_FENCE_DELIVERY_FACTORY_SHA256 = "1936626c77d1df8fcfd10c5a24ad1a84294e268a2fe755757ca16401324b27ac"
PRIVATE_CORRECTED_DELIVERY_FACTORY_SHA256 = "4dcaa73704388596c6aa6f7614bc6756fb6b8b26ff934ec05b07bfc96abd523d"
PRIVATE_SLICE_1A_DELIVERY_FACTORY_SHA256 = "7fa07b67f316fa9543e77073628ffd9a0a54bec8d9133d9d2284fa1db58ad028"
PRIVATE_TESTER_ROUND_DELIVERY_FACTORY_SHA256 = "2c37f07791e095fa1fbb0506304ca4178be8349ba1516170cbc77264482eef7d"
PRIVATE_ROUND2_DELIVERY_FACTORY_SHA256 = "cc121dfe7beb2c77175da79f223e5d2e4b0e845b482f72a65f2e11dd6a96c3d4"
PRIVATE_ONBOARDING_QUALIFICATION = {
    "schema": 1,
    "reviewed_source_sha": "4f699d76077d1b8698e1e2c46f959d9b0251cc5a",
    "accepted_source_sha": "7b42199aefbdb0bb37fc9739d73ef350e8c3ae6d",
    "source_review_receipt_sha256": "cdd12dfc0cf010d52bd2affa9c8cd909449de78b872490027e03f6d32943b2a1",
    "behaviors": ["bound_credential_details", "monotonic_composer_lifecycle"],
    "resume_ocr": {
        "manifest_path": r"X:\PeerSlate\runtimes\ocr\resume-ocr-v1.json",
        "manifest_sha256": "1d6a2b63053a8c85bf2aae15448491d115c75b941ec0af63a0c7fd8269e9794b",
    },
}


PRIVATE_DIAGNOSTIC_ONBOARDING_QUALIFICATION = {
    **PRIVATE_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "a3285353bbe8e5fab634086c833e14c5fbef58f5",
    "accepted_source_sha": "3207460df1738e71486e92db338787bce53fea29",
    "source_review_receipt_sha256": "aa6c670bab60fe4487ea1097b05acfb4f52a413c7089d0bb40d6f3651eb0c086",
}


PRIVATE_FIELD_CONTRACT_ONBOARDING_QUALIFICATION = {
    **PRIVATE_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "11934962e3b52f5096bd9084478001a0ab8df9b0",
    "accepted_source_sha": "3e2ac536e316e628212fe2d411d7591dd4a15440",
    "source_review_receipt_sha256": "dfd73a477d65675568917bcc29f757941e04bcc53ae408513d4900d8ec469bef",
}


PRIVATE_D01_BINDING_ONBOARDING_QUALIFICATION = {
    **PRIVATE_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "3a1df028d1ca49b74a227c3fbe9ce1b5726cfbc6",
    "accepted_source_sha": "a473701ac57fe182107ec74584396c7b28b94757",
    "source_review_receipt_sha256": "e33e7abc1c00ac6f7abe15a83cfd6b14398f27552a35dc5fa72dd0f5e42b4149",
}


PRIVATE_PREVIEW_FENCE_ONBOARDING_QUALIFICATION = {
    **PRIVATE_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "2d2b4f6356a31a0f1d7e89705b42c63d7c647fde",
    "accepted_source_sha": "34157f292b106a6cb7c75d4081d6ae8fa1874806",
    "source_review_receipt_sha256": "d62140c001c505a1bd7d217ca0471f3d669228008851484002d86573b97ffdf8",
}


PRIVATE_CORRECTED_ONBOARDING_QUALIFICATION = {
    **PRIVATE_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "5185ffb931dce9676516e8ded28334ff1b8ba05c",
    "accepted_source_sha": "7e7905c1d972fb842b697aa4884051005f6a206c",
    "source_review_receipt_sha256": "670c8bdf1bfb46b634000f1c4a0fb02c212a8ee55cc315626bec978468a92461",
    "behaviors": ["bound_credential_details", "monotonic_composer_lifecycle", "contextual_exclusion_recovery"],
}


PRIVATE_SLICE_1A_ONBOARDING_QUALIFICATION = {
    **PRIVATE_CORRECTED_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "194283cf8d6190a7e71790b0af04053f024da41b",
    "accepted_source_sha": "5454f3c73b3b0a188b86caa24e9e79fcd1f58a02",
    "source_review_receipt_sha256": "191eb6fde3174be620223464c3ec51da1c8635a33e6cb97fe81cb0de806deb75",
}


PRIVATE_TESTER_ROUND_ONBOARDING_QUALIFICATION = {
    **PRIVATE_SLICE_1A_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "c4c33f79946d696e4ba2a51260bdf79c5efdd507",
    "accepted_source_sha": "a91a78da1c656d80c3b0d311b52c211171c8ade4",
    "source_review_receipt_sha256": "8374ac6b5f8d5b3843de8e529931a4619a2f61f9d844f71f4fe48fc10b531ebe",
}


PRIVATE_ROUND2_ONBOARDING_QUALIFICATION = {
    **PRIVATE_TESTER_ROUND_ONBOARDING_QUALIFICATION,
    "reviewed_source_sha": "7461d6dd73a4b3f5de017be0c27afbe78a91df31",
    "accepted_source_sha": "08c3c5ffe65ae2eacb35c15e0cb2820da2890d50",
    "source_review_receipt_sha256": "de2ba86eed5c559c1c428a1546514f381ddbee49426004953b467bbf521e65f0",
}


def onboarding_qualification(interface):
    proof = interface.get("private_onboarding_qualification")
    if proof is None:
        return None
    if proof not in (PRIVATE_ONBOARDING_QUALIFICATION, PRIVATE_DIAGNOSTIC_ONBOARDING_QUALIFICATION,
                     PRIVATE_FIELD_CONTRACT_ONBOARDING_QUALIFICATION, PRIVATE_D01_BINDING_ONBOARDING_QUALIFICATION,
                     PRIVATE_PREVIEW_FENCE_ONBOARDING_QUALIFICATION, PRIVATE_CORRECTED_ONBOARDING_QUALIFICATION,
                     PRIVATE_SLICE_1A_ONBOARDING_QUALIFICATION, PRIVATE_TESTER_ROUND_ONBOARDING_QUALIFICATION,
                     PRIVATE_ROUND2_ONBOARDING_QUALIFICATION):
        raise ValueError("Reviewed private onboarding qualification changed")
    return proof


def selected_configuration(root, configuration_id=None, *, original=False):
    """The manifest atomically selects a private app/configuration pair."""
    from pathlib import Path
    root = Path(root)
    if original and configuration_id is not None:
        raise ValueError("Choose one explicit private configuration pair")
    manifest_path = root / "installation.json"
    selected = configuration_id is not None
    if not selected and not original and manifest_path.exists():
        manifest = json_codec.loads(manifest_path.read_text(encoding="utf-8"))
        selected = "provider_configuration" in manifest
        configuration_id = manifest.get("provider_configuration")
    if selected:
        if not isinstance(configuration_id, str) or not __import__("re").fullmatch("[0-9a-f]{64}", configuration_id):
            raise ValueError("Invalid private configuration identity")
        pair = bound_document(root / "data" / "provider-configurations" / (configuration_id + ".json"), configuration_id)
        if not isinstance(pair, dict) or set(pair) != {"live_ai", "factory_utf8"} or not isinstance(pair["factory_utf8"], str):
            raise ValueError("Invalid private configuration snapshot")
        return pair["live_ai"], bound_factory(pair["factory_utf8"].encode("utf-8"))
    path = root / "live-ai.json"
    if not path.is_file() or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("Explicit private AI configuration required")
    factory_path = root / "ai-factory.json"
    if not factory_path.is_file() or any(p.is_symlink() or p.is_junction() for p in (factory_path, *factory_path.parents)):
        raise ValueError("Ordinary bound factory file required")
    return json_codec.loads(path.read_text(encoding="utf-8")), bound_factory(factory_path.read_bytes())


def load_configuration(root, identity, source, *, configuration_id=None, original=False):
    """Read explicit installed configuration; never discover or create budgets."""
    from pathlib import Path
    from .provider_budget import validate_allocation
    config, interface = selected_configuration(root, configuration_id, original=original)
    onboarding_qualification(interface)
    if not isinstance(config, dict) or set(config) != {
        "allocation_sha256", "owner", "profiles", "factory", "signing_key"
    }:
        raise ValueError("Invalid private AI configuration")
    if config["allocation_sha256"] != ALLOCATION_SHA256 or config["owner"] != identity.owner:
        raise ValueError("Private owner/allocation binding changed")
    allocation = bound_document(Path(root) / "ai-allocation.json", ALLOCATION_SHA256)
    if interface.get("ongoing_budget_port") != ONGOING_BINDINGS:
        raise ValueError("Accepted ongoing factory interface required")
    if config["profiles"] != allocation["profiles"] or config["factory"] != {
        key: interface[key] for key in ("files_sha256", "profile_contract", "limits_maxima")
    }:
        raise ValueError("Private AI settings differ from the reviewed allocation/factory")
    validate_allocation(identity.owner, ALLOCATION_SHA256, config["profiles"])
    if not isinstance(config["signing_key"], str) or not __import__("re").fullmatch("[0-9a-f]{64}", config["signing_key"]):
        raise ValueError("Persistent private confirmation key required")
    factory = config["factory"]
    if not isinstance(factory, dict) or set(factory) != {"files_sha256", "profile_contract", "limits_maxima"}:
        raise ValueError("Bound application factory configuration required")
    for relative, expected in factory["files_sha256"].items():
        path = Path(source) / relative
        if (not isinstance(relative, str) or not path.is_relative_to(Path(source))
                or ".." in Path(relative).parts or not path.is_file()
                or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                       for p in (path, *path.parents))):
            raise ValueError("Factory source path unavailable")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Application factory changed; explicit compatibility update required")
    for name in ("interview", "extraction", "synthesis"):
        qualified, allocated = factory["profile_contract"][name], config["profiles"][name]
        if (qualified["model"] != allocated["model"] or qualified["effort"] != allocated["reasoning_effort"]
                or qualified["tier"] != allocated["service_tier"]):
            raise ValueError("Allocated model profile differs from qualified factory")
    return config


def selected_ocr_configuration(root, *, configuration_id=None, original=False):
    """The exact reviewed factory alone selects native local processing."""
    _, interface = selected_configuration(root, configuration_id, original=original)
    proof = onboarding_qualification(interface)
    if proof is None:
        return None
    binding = proof["resume_ocr"]
    from pathlib import Path
    manifest = Path(binding["manifest_path"])
    if not manifest.is_absolute():
        raise ValueError("Absolute reviewed OCR manifest required")
    raw = ordinary_configuration_bytes(manifest)
    if hashlib.sha256(raw).hexdigest() != binding["manifest_sha256"]:
        raise ValueError("Reviewed OCR manifest changed")
    from services.resume_onboarding_document_reader import load_ocr_configuration
    verified = load_ocr_configuration(str(manifest))
    if (verified["manifest_sha256"] != binding["manifest_sha256"]
            or len(verified["settings"]["files_sha256"]) != 219):
        raise ValueError("Reviewed OCR dependency binding changed")
    return str(manifest)


def azure_cli_token_callback():
    """Use the existing local Azure sign-in, only when the caller dispatches AI."""
    def token():
        import shutil
        import subprocess
        try:
            executable = shutil.which("az.cmd")
            if not executable:
                raise ValueError("Azure CLI unavailable")
            result = subprocess.run([
                executable, "account", "get-access-token", "--subscription", AZURE_SUBSCRIPTION,
                "--resource", "https://cognitiveservices.azure.com", "--query", "accessToken",
                "--output", "tsv", "--only-show-errors"
            ], capture_output=True, text=True, timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            value = result.stdout.strip()
            if result.returncode or not value or any(character.isspace() for character in value):
                raise ValueError("Azure identity unavailable")
            return value
        except Exception:
            # Neither stdout/stderr nor tokens enter diagnostics or exceptions.
            raise ProviderUnavailableError("Private AI identity unavailable") from None
    return token


class OngoingPrivateBudgetPort:
    """A native observation can stage evidence; only StructuredResult can settle."""
    def __init__(self, database, factory):
        self.database, self.factory = database, factory
        self.context = ContextVar("private-budget-" + str(id(self)), default=None)
        self.validated = {}

    def validate_profile(self, *, profile, settings, reservation):
        from services.resume_intake_runtime import PRIVATE_ASSISTANCE_PROFILES
        from services.ai_foundation.azure_foundry import NATIVE_LUNA_MODEL_VERSION
        if profile not in {"extraction", "interview", "synthesis"}:
            raise ValueError("Closed private profile required")
        selected, allocated = self.factory["profile_contract"][profile], self.database.profiles[profile]
        expected = make_private_settings(selected, allocated)
        from .provider_budget import encoded
        if (encoded(settings) != encoded(expected) or type(reservation) is not int or reservation != allocated["reservation_micro_usd"]
                or allocated["maximum_calls"] != 100
                or allocated["model"] != selected["model"] or allocated["reasoning_effort"] != selected["effort"]
                or allocated["service_tier"] != selected["tier"]
                or any(allocated[key] != selected[key] for key in ("input_tokens", "output_tokens"))
                or [allocated["input_micro_usd_per_million"], allocated["output_micro_usd_per_million"]]
                != selected["safety_prices_per_million_micro_usd"]):
            raise ValueError("Private profile differs from immutable allocation")
        version = NATIVE_LUNA_MODEL_VERSION if profile == "extraction" else PRIVATE_ASSISTANCE_PROFILES[profile]["version"]
        self.validated[allocated["scope"]] = (profile, selected, version)
        return True

    def reserve(self, owner, request_id, settings, reservation):
        try:
            selected = self.validated[settings["scope"]]
            allocated = self.database.profiles[selected[0]]
            if settings != {key: allocated[key] for key in ("scope", "maximum_calls", "hard_cap_micro_usd", "concurrent_requests")}:
                raise ValueError("Allocation changed")
            values = {"@UserKey": owner, "@RequestId": request_id, "@Scope": settings["scope"],
                      "@ReservationMicroUsd": reservation, "@MaximumCalls": settings["maximum_calls"],
                      "@HardCapMicroUsd": settings["hard_cap_micro_usd"], "@ConcurrentRequests": settings["concurrent_requests"]}
            if not self.database.reserve(values):
                raise ValueError("Reservation refused")
            self.context.set({"owner": owner, "request": request_id, "scope": settings["scope"],
                              "selected": selected, "credential_attempts": 0, "dispatched": False, "event": None})
        except Exception:
            raise ProviderUnavailableError("Private AI reservation unavailable") from None

    def credential(self, names, acquire):
        state = self.context.get()
        if not state or state["selected"][0] not in names or state["credential_attempts"]:
            raise ProviderUnavailableError("Exact private reservation required")
        state["credential_attempts"] += 1
        return acquire()

    def before_dispatch(self, url, payload):
        state = self.context.get()
        if not state or state["dispatched"] or state["credential_attempts"] != 1:
            raise ProviderUnavailableError("Exact private dispatch required")
        name, selected, _ = state["selected"]
        schema = "my_data_intake_extraction_v2" if name == "extraction" else "resume_" + name + "_v1"
        if (url != FOUNDRY_ENDPOINT + "/openai/v1/responses" or payload.get("model") != selected["alias"]
                or payload.get("reasoning") != {"effort": selected["effort"]} or payload.get("service_tier") != selected["tier"]
                or payload.get("store") is not False or payload.get("max_output_tokens") != selected["output_tokens"]
                or payload.get("text", {}).get("format", {}).get("name") != schema
                or len(json_codec.dumps(payload, separators=(",", ":")).encode("utf-8")) > selected["wire_bytes"]):
            raise ProviderUnavailableError("Private wire binding unavailable")
        state["dispatched"] = True

    def observe(self, response):
        from .provider_budget import identity_digest, natural
        state = self.context.get()
        try:
            if not state or not state["dispatched"] or state["credential_attempts"] != 1 or state["event"] is not None:
                raise ValueError("Exact single native observation required")
            payload = response.json()
            if (type(response.status_code) is not int or response.status_code != 200 or type(payload) is not dict
                    or payload.get("status") != "completed" or payload.get("model") != state["selected"][1]["alias"]
                    or payload.get("model_version") not in (None, state["selected"][2])):
                raise ValueError("Native completion binding unavailable")
            event = {"phase": 1, "identity_sha256": identity_digest(payload.get("id")),
                     "input_tokens": natural(payload["usage"]["input_tokens"]),
                     "output_tokens": natural(payload["usage"]["output_tokens"])}
            self.database.observe_overrun(state["owner"], state["scope"], state["request"], [event])
            state["event"], state["response_version"] = event, payload.get("model_version")
        except Exception:
            raise ProviderUnavailableError("Native completion accounting unavailable") from None

    def settle_completed(self, owner, request_id, scope, result):
        from services.ai_foundation.contracts import StructuredResult
        from services.ai_foundation.azure_foundry import RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT
        from .provider_budget import natural
        state = self.context.get()
        try:
            if not state or (owner, request_id, scope) != (state["owner"], state["request"], state["scope"]):
                raise ValueError("Completion context differs")
            name, selected, version = state["selected"]
            schema = "my_data_intake_extraction_v2" if name == "extraction" else "resume_" + name + "_v1"
            event = state["event"]
            if (type(result) is not StructuredResult or event is None or result.request_id != request_id
                    or result.schema_name != schema or result.model_name != selected["model"]
                    or result.deployment_name != selected["alias"] or result.configured_model_version != version
                    or result.response_model_name != selected["alias"] or result.response_model_version != state["response_version"]
                    or result.response_identity_source != RESPONSE_IDENTITY_CONFIGURED_DEPLOYMENT
                    or natural(result.input_tokens) != event["input_tokens"]
                    or natural(result.output_tokens) != event["output_tokens"]):
                raise ValueError("Structured completion differs from native observation")
            self.database.settle(owner, scope, request_id, [event])
        except Exception:
            raise ProviderUnavailableError("Private completion accounting unavailable") from None


def make_private_settings(selected, allocated):
    return {"endpoint": FOUNDRY_ENDPOINT, "deployment": selected["alias"],
        "provider": {"maximum_input_bytes": selected["wire_bytes"], "maximum_input_tokens": selected["input_tokens"],
                     "maximum_output_tokens": selected["output_tokens"]},
        "prices": {"input_micro_usd_per_million": selected["safety_prices_per_million_micro_usd"][0],
                   "output_micro_usd_per_million": selected["safety_prices_per_million_micro_usd"][1],
                   "schedule_ref": "private-test-conservative-reservation-not-invoice"},
        "budget": {key: allocated[key] for key in ("scope", "maximum_calls", "hard_cap_micro_usd", "concurrent_requests")}}


class ContentFreeTransport:
    """Keep numerical usage only; never capture prompts, documents or answers."""
    def __init__(self, root, transport, accounting=None):
        from pathlib import Path
        self.path, self.transport = Path(root) / "logs" / "provider-usage.jsonl", transport
        self.lock = Lock()
        self.accounting = accounting

    def post(self, url, *, headers, json, timeout):
        if self.accounting is not None:
            self.accounting.before_dispatch(url, json)
        response = self.transport.post(url, headers=headers, json=json, timeout=timeout)
        try:
            document = response.json()
            response = SimpleNamespace(status_code=response.status_code, json=lambda: document)
        except Exception:
            # Mandatory staging or the app will reject malformed native output.
            # Do not issue a second HTTP request or record the response body.
            pass
        if self.accounting is not None:
            # This is mandatory accounting staging, separate from optional logs.
            self.accounting.observe(response)
        try:
            document = response.json()
            usage = document.get("usage") if isinstance(document, dict) else None
            event = {"model": json.get("model") if json.get("model") in {
                "gpt-6-luna", "eval0930-gpt-6-sol", "peerslate-resume-sol61"} else "unknown",
                "http_status": response.status_code if type(response.status_code) is int else None}
            for name in ("input_tokens", "output_tokens"):
                value = usage.get(name) if isinstance(usage, dict) else None
                event[name] = value if type(value) is int and value >= 0 else None
            with self.lock:
                self.path.parent.mkdir(exist_ok=True)
                with self.path.open("a", encoding="utf-8") as output:
                    output.write(json_codec.dumps(event, separators=(",", ":")) + "\n")
        except Exception:
            # Optional telemetry failure must not replay or alter a paid call.
            pass
        return response


class PublicDiagnostic:
    """Explicit one-shot operator capture under already verified private ACLs.

    Never captures credentials/headers. The claim is consumed even if this call
    fails before transport. Subsequent operations never capture content.
    """
    def __init__(self, root, database):
        from pathlib import Path
        self.directory, self.database = Path(root) / "logs" / "public-diagnostic", database

    def claim(self, state):
        scope = self.database.profiles["public"]["scope"]
        calls = self.database.snapshot(scope)["budget"]["dispatched_calls"]
        directory = self.directory / ("operation-" + str(calls))
        if not directory.exists():
            directory = self.directory  # Preserve the first legacy one-shot capture.
        path = directory / "armed.json"
        if not path.exists():
            return
        self.database._ordinary(path)
        permit = json_codec.loads(path.read_text(encoding="utf-8"))
        expected = {"owner": self.database.owner, "allocation_sha256": self.database.expected["allocation_sha256"],
                    "scope": scope, "previous_calls": calls - 1}
        if permit != expected or (directory / "claimed.json").exists():
            raise ProviderUnavailableError("One-shot diagnostic binding changed")
        path.rename(directory / "claimed.json")
        state["diagnostic"] = directory
        self.capture(state, {"claimed": True, "request_id": state["request_id"]})

    def capture(self, state, envelope):
        if not state.get("diagnostic"):
            return
        # Each phase has a distinct exclusive file; no append replay or overwrite.
        name = "terminal" if envelope.get("terminal") else "claim" if envelope.get("claimed") else "phase-" + str(envelope["phase"])
        data = json_codec.dumps(envelope, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(data) > 2_000_000:
            raise ProviderUnavailableError("Diagnostic response exceeds bounded capture")
        path = state["diagnostic"] / (name + ".json")
        self.database._ordinary(path)
        with path.open("xb") as output:
            output.write(data)


def configure_private_providers(fixture, app, root, identity, configuration, *,
                                token_provider=None, transport=None, speech_session=None, workspace=None):
    """Compose actual app factories with this installation's existing ledger."""
    from pathlib import Path
    from itsdangerous import URLSafeTimedSerializer
    from .provider_budget import ProviderBudget
    from services.resume_intake_runtime import BoundedResumeExtractionProvider, build_private_resume_assistance
    from services.member_visitor_ai_service import build_configured_visitor_ai
    profiles, factory = configuration["profiles"], configuration["factory"]
    onboarding_context = None
    if workspace is not None and workspace.namespace is not None:
        if workspace.key != "onboarding":
            raise ValueError("Only server-owned onboarding may use test funding")
        onboarding_context = {"installation": json_codec.loads((Path(root) / "installation.json").read_bytes())["installation"],
                              "namespace": workspace.namespace}
    database = ProviderBudget(Path(root) / "data" / "provider-budget-v1.sqlite3",
                              owner=identity.owner, allocation_sha256=configuration["allocation_sha256"], profiles=profiles,
                              onboarding_context=onboarding_context)
    acquire = token_provider or azure_cli_token_callback()
    ongoing = OngoingPrivateBudgetPort(database, factory)
    trace = ContentFreeTransport(root, transport or UrllibTransport(), ongoing)

    def reserved_token(*names):
        def token():
            if names != ("speech",):
                return ongoing.credential(names, acquire)
            if not database.has_active([profiles[name]["scope"] for name in names]):
                raise ProviderUnavailableError("Committed private AI reservation required")
            return acquire()
        return token

    def settings(name):
        return make_private_settings(factory["profile_contract"][name], profiles[name])

    extraction_settings = settings("extraction")
    extraction = BoundedResumeExtractionProvider(settings=extraction_settings, database=database,
        token_provider=reserved_token("extraction"), transport=trace, ongoing_budget_port=ongoing)
    speech = build_native_speech_port(database=database, token_provider=reserved_token("speech"),
                                      owner=identity.owner, profile=profiles["speech"], session=speech_session)
    bridge = build_base_intake_bridge(fixture.intake, extraction_provider=extraction,
        extraction_adapter=MyDataExtractionAdapter(provider=extraction), native_speech=speech)
    private_settings = {"profiles": {name: settings(name) for name in ("synthesis", "interview")},
                        "limits": factory["limits_maxima"]}
    private = build_private_resume_assistance({"RESUME_PRIVATE_ASSISTANCE_CONFIGURATION": private_settings,
        "RESUME_INTAKE_PROVIDER_CONFIGURATION": extraction_settings}, draft_service=fixture.shared.draft,
        catalog=fixture.shared.canonical, policy_repository=fixture.shared.policy.repository,
        database=database, token_provider=reserved_token("synthesis", "interview"), transport=trace,
        ongoing_budget_port=ongoing,
        signer=URLSafeTimedSerializer(bytes.fromhex(configuration["signing_key"]), salt="resume-private-assistance-v1"))
    public_port = build_native_public_port(database=database, token_provider=acquire, owner=identity.owner,
        profile=profiles["public"], transport=ContentFreeTransport(root, transport or UrllibTransport()))
    public_port.diagnostic = PublicDiagnostic(root, database)
    public_settings = {"endpoint": FOUNDRY_ENDPOINT, "deployment": "gpt-6-luna", "scope": "single_process",
        "limits": {"maximum_request_bytes": 16000, "maximum_question_characters": 1000, "concurrent_requests": 1,
                   "timeout_seconds": 180, "window_seconds": 3600, "requests_per_client_window": 100, "maximum_clients": 50,
                   "cost_units_per_request": PUBLIC_ANSWER_RESERVATION_MICRO_USD,
                   "aggregate_cost_units_per_window": profiles["public"]["hard_cap_micro_usd"]},
        "provider": {"maximum_input_bytes": PUBLIC_WIRE_BYTES, "maximum_input_tokens": PUBLIC_INPUT_TOKENS,
                     "maximum_output_tokens": PUBLIC_OUTPUT_TOKENS},
        "prices": {"input_micro_usd_per_million": 1000000, "output_micro_usd_per_million": 6000000,
                   "schedule_ref": "private-test-conservative-reservation-not-invoice"},
        "citation_capacity": 100, "citation_lifetime_seconds": 600}
    public, runtime = build_configured_visitor_ai(fixture.ai.sources, public_settings,
        token_provider=public_port.token_provider, transport=public_port.transport, protections=public_port)
    original_sources = public.sources
    public.sources = BoundPublicSources(original_sources, public_port)
    runtime = CompletionRuntime.adopt(runtime, original_sources)
    public.names = fixture.ai.names
    fixture.stack.callback(runtime.close)
    fixture.intake, fixture.ai, fixture.ai_runtime = bridge, public, runtime
    app.config.update(RESUME_INTAKE_SERVICE=bridge, RESUME_PRIVATE_ASSISTANCE_SERVICE=private,
                      RESUME_PRIVATE_ASSISTANCE_CONFIGURATION=private_settings,
                      PEERSLATE_RESUME_SYNTHESIS_ENABLED=True, PEERSLATE_RESUME_INTERVIEW_ENABLED=True,
                      MEMBER_VISITOR_AI_SERVICE=public, MEMBER_VISITOR_AI_RUNTIME=runtime)
    fixture.private_provider_budget, fixture.private_public_port = database, public_port
    return database
