"""Record the PS-INTERVIEW-AI-EXTRACT-001 parity oracle.

Runs the four legacy Interview AI routes against a deterministic capture
fake in place of ``client.messages.create`` and writes one JSON fixture per
case under ``tests/interview_ai/fixtures/parity/``. The fixtures are the
byte-level oracle the extraction must reproduce: provider-call count and
order, the exact explicit keyword set, model and max_tokens, exact UTF-8
system and user-message bytes, the deterministic fake reply, validator
outcome, exact response body bytes, HTTP status, content type,
signed-context semantics under a fixed clock, provider-free refusals, and
persistence effects (none).

Recording is only valid against the legacy Interview source checkpoint
(73c4e63dc74a2e67fb6bed0ed4c3d9e58e3525c5 — byte-identical Interview code at
branch base 5322f105). Regenerating fixtures after the extraction lands
would record the candidate, not the oracle, and is prohibited.

No live provider call, no Anthropic traffic, no paid evaluation, and no
production member data are involved; candidate content is synthetic and the
profile context is the repository's own fixture profile.
"""

import base64
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Deterministic environment. The Interview context signing key derives from
# ANTHROPIC_API_KEY when INTERVIEW_CONTEXT_SIGNING_KEY is unset, so both are
# pinned before the app module is imported.
FIXED_ANTHROPIC_KEY = "parity-oracle-fixed-key"
FIXED_SIGNING_KEY = "parity-oracle-interview-context-signing-key"
FIXED_CLOCK = 1755648000  # 2026-08-20T00:00:00Z, frozen for token parity.

os.environ["ANTHROPIC_API_KEY"] = FIXED_ANTHROPIC_KEY
os.environ["INTERVIEW_CONTEXT_SIGNING_KEY"] = FIXED_SIGNING_KEY
os.environ.pop("PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED", None)

import anthropic  # noqa: E402
import httpx  # noqa: E402

import app as app_module  # noqa: E402
from services import database_service as database_service_module  # noqa: E402

FIXTURE_DIR = ROOT / "tests" / "interview_ai" / "fixtures" / "parity"
SOURCE_CHECKPOINT = "73c4e63dc74a2e67fb6bed0ed4c3d9e58e3525c5"


def _b64(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("ascii")


def make_provider_exception(spec):
    """Build one pinned-SDK exception from a content-free spec name."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    if spec == "timeout":
        return anthropic.APITimeoutError(request=request)
    if spec == "connection":
        return anthropic.APIConnectionError(
            message="Connection error.", request=request
        )
    status_by_spec = {
        "rate_limited": 429,
        "overloaded": 529,
        "server_error": 500,
        "bad_request": 400,
    }
    status = status_by_spec[spec]
    response = httpx.Response(status, request=request, content=b"{}")
    classes = {
        429: anthropic.RateLimitError,
        400: anthropic.BadRequestError,
    }
    cls = classes.get(status, anthropic.InternalServerError)
    return cls("provider error", response=response, body=None)


class CaptureFake:
    """Deterministic stand-in for client.messages.create."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if not self.replies:
            raise AssertionError("provider called more times than scripted")
        reply = self.replies.pop(0)
        if "raise" in reply:
            raise make_provider_exception(reply["raise"])

        class _Block:
            def __init__(self, text):
                self.type = "text"
                self.text = text

        class _Usage:
            def __init__(self, input_tokens, output_tokens):
                self.input_tokens = input_tokens
                self.output_tokens = output_tokens

        class _Response:
            pass

        response = _Response()
        response.content = [_Block(reply["text"])]
        response.stop_reason = reply.get("stop_reason", "end_turn")
        usage = reply.get("usage")
        if usage is not None:
            response.usage = _Usage(usage["input_tokens"], usage["output_tokens"])
        return response


def serialize_calls(calls):
    out = []
    for kwargs in calls:
        entry = {
            "kwargs_keys": sorted(kwargs.keys()),
            "model": kwargs.get("model"),
            "max_tokens": kwargs.get("max_tokens"),
            "system_b64": _b64(kwargs.get("system", "")),
            "messages": [
                {
                    "role": message.get("role"),
                    "content_b64": _b64(message.get("content", "")),
                }
                for message in kwargs.get("messages", [])
            ],
        }
        out.append(entry)
    return out


def run_case(name, steps, auth=None, provenance=None):
    """Execute one fixture case and write its record.

    ``auth`` switches the request into the authenticated-Studio surface for
    every step: the flag is set on app.config, ``get_current_identity``
    returns the recorded synthetic identity, and ``is_owner`` answers the
    recorded owner bit — the exact context-construction seams the live
    authenticated path uses, driven by synthetic data only. The auth spec
    is stored in the fixture so replay reproduces the identical context.
    """
    from types import SimpleNamespace

    recorded_steps = []
    context = {}
    for step in steps:
        replies = step.get("provider_replies", [])
        fake = CaptureFake(json.loads(json.dumps(replies)))
        database_calls = []

        def record_db(procedure_name, parameters=None):
            database_calls.append(procedure_name)
            raise AssertionError(
                "legacy interview routes must not touch the database"
            )

        payload = step["request"].get("json")
        if payload is not None and "context_token" in payload:
            token_ref = payload["context_token"]
            if token_ref == "__STEP1_CONTEXT_TOKEN__":
                payload = dict(payload)
                payload["context_token"] = context["context_token"]

        from contextlib import ExitStack

        with ExitStack() as stack:
            stack.enter_context(patch.object(
                app_module.client.messages, "create", new=fake,
            ))
            stack.enter_context(patch.object(
                database_service_module.database_service,
                "execute_procedure",
                new=record_db,
            ))
            stack.enter_context(patch(
                "itsdangerous.timed.time.time", return_value=FIXED_CLOCK,
            ))
            if auth is not None:
                identity = SimpleNamespace(**auth["identity"])
                stack.enter_context(patch.object(
                    app_module, "get_current_identity",
                    new=lambda: identity,
                ))
                stack.enter_context(patch.object(
                    app_module, "is_owner",
                    new=lambda candidate: auth["owner"],
                ))
                stack.enter_context(patch.dict(
                    app_module.app.config,
                    {"PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED": True},
                ))
            test_client = app_module.app.test_client()
            request_spec = step["request"]
            kwargs = {"base_url": "http://localhost"}
            if payload is not None:
                kwargs["json"] = payload
            if "data" in request_spec:
                kwargs["data"] = request_spec["data"]
            response = test_client.post(request_spec["path"], **kwargs)

        body = response.get_data()
        # Record the placeholder, never the substituted signed token: replay
        # chains its own step-1 token, and a recorded field named *token*
        # with a high-entropy value would read as a secret to scanners.
        recorded_payload = step["request"].get("json")
        step_record = {
            "request": {
                "path": request_spec["path"],
                "json": recorded_payload,
                "data": request_spec.get("data"),
            },
            "provider_replies": replies,
            "provider_calls": serialize_calls(fake.calls),
            "provider_call_count": len(fake.calls),
            "unconsumed_replies": len(fake.replies),
            "response": {
                "status": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "body_b64": _b64(body),
            },
            "database_calls": database_calls,
        }
        recorded_steps.append(step_record)
        if response.status_code == 200:
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = {}
            if isinstance(parsed, dict) and "contextToken" in parsed:
                context["context_token"] = parsed["contextToken"]

    record = {
        "fixture": name,
        "source_checkpoint": SOURCE_CHECKPOINT,
        "clock": FIXED_CLOCK,
        "env": {
            "ANTHROPIC_API_KEY": FIXED_ANTHROPIC_KEY,
            "INTERVIEW_CONTEXT_SIGNING_KEY": FIXED_SIGNING_KEY,
            "PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED": None,
        },
        "steps": recorded_steps,
    }
    if auth is not None:
        record["auth"] = auth
        record["env"]["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = "true"
    if provenance is not None:
        record["provenance"] = provenance
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / (name + ".json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=1, sort_keys=True)
        handle.write("\n")
    status = recorded_steps[-1]["response"]["status"]
    calls = sum(step["provider_call_count"] for step in recorded_steps)
    print(f"recorded {name}: status={status} provider_calls={calls}")


def review_reply(evidence_ids, family="behavioral", suggestions=0, drop=None,
                 fence=False):
    dimensions = [
        {
            "key": key,
            "status": "developing",
            "rationale": "Synthetic rationale for %s." % key,
            "nextAction": "Synthetic next step for %s." % key,
        }
        for key in app_module.INTERVIEW_FAMILY_DIMENSIONS[family]
    ]
    reply = {
        "verdict": "Solid synthetic start",
        "encouragement": "Synthetic encouragement sentence for the oracle.",
        "whatCameThroughClearly": ["Synthetic clear observation."],
        "strengths": ["Synthetic strength."],
        "improvements": ["Synthetic improvement."],
        "strongerApproach": "Synthetic stronger approach for this question.",
        "focusedFollowUp": "Synthetic focused follow-up prompt.",
        "dimensions": dimensions,
        "evidenceSuggestions": [
            {
                "opportunity": "Synthetic opportunity %d." % index,
                "suggestedUse": "Synthetic truthful use %d." % index,
                "evidenceId": evidence_ids[index],
            }
            for index in range(suggestions)
        ],
    }
    if drop:
        reply.pop(drop)
    text = json.dumps(reply)
    if fence:
        text = "```json\n" + text + "\n```"
    return {"text": text, "usage": {"input_tokens": 900, "output_tokens": 400}}


def improvement_reply(evidence_ids, markers=True):
    draft = (
        "I led the synthetic migration and cut processing time."
        " [Describe the specific outcome you achieved.]"
        " We then scaled the result. [Add the name of the stakeholder.]"
        if markers
        else "I led the synthetic migration and cut processing time in half."
    )
    return {
        "text": json.dumps(
            {
                "draft": draft,
                "changes": ["Tightened the opening.", "Added a concrete metric."],
                "evidenceIds": evidence_ids,
            }
        ),
        "usage": {"input_tokens": 700, "output_tokens": 300},
    }


def nudge_reply(count=2):
    hints = [
        "Synthetic hint one about structure.",
        "Synthetic hint two about outcomes.",
        "Synthetic hint three about delivery.",
    ][:count]
    return {
        "text": json.dumps({"hints": hints}),
        "usage": {"input_tokens": 200, "output_tokens": 90},
    }


def model_answer_reply(evidence_ids, status="answered", cite=True):
    if status == "insufficient":
        payload = {"status": "insufficient", "answer": "", "whyItWorks": [],
                   "evidenceIds": []}
    else:
        payload = {
            "status": "answered",
            "answer": "Synthetic sixty-second grounded answer to the question.",
            "whyItWorks": ["Synthetic factor one.", "Synthetic factor two."],
            "evidenceIds": list(evidence_ids) if cite else [],
        }
    return {
        "text": json.dumps(payload),
        "usage": {"input_tokens": 800, "output_tokens": 350},
    }


def main():
    profile, evidence = app_module._interview_page_context("petec")
    evidence_ids = [item["id"] for item in evidence]
    if len(evidence_ids) < 2:
        raise SystemExit("fixture profile carries too little evidence")

    app_module.limiter.enabled = False

    question = "Tell me about a time you led a project under pressure."
    answer = (
        "At my last role I coordinated a three-person team to deliver a"
        " reporting tool two weeks early despite a mid-project scope change."
    )
    opportunity = "Synthetic role context for a data analyst opening."
    base_review = {
        "question": question,
        "answer": answer,
        "level": "experienced",
        "family": "behavioral",
        "competency": "Leadership",
        "profile_slug": "petec",
    }

    run_case("coach_success_minimal", [{
        "request": {"path": "/api/interview/review", "json": base_review},
        "provider_replies": [review_reply(evidence_ids)],
    }])
    run_case("coach_success_with_context_and_suggestions", [{
        "request": {"path": "/api/interview/review", "json": dict(
            base_review, opportunity_context=opportunity)},
        "provider_replies": [review_reply(evidence_ids, suggestions=2)],
    }])
    run_case("coach_success_markdown_fence", [{
        "request": {"path": "/api/interview/review", "json": base_review},
        "provider_replies": [review_reply(evidence_ids, fence=True)],
    }])
    run_case("coach_success_family_situational", [{
        "request": {"path": "/api/interview/review", "json": dict(
            base_review, family="situational")},
        "provider_replies": [review_reply(evidence_ids, family="situational")],
    }])
    run_case("coach_invalid_json_502", [{
        "request": {"path": "/api/interview/review", "json": base_review},
        "provider_replies": [{"text": "the coach rambled with no JSON"}],
    }])
    run_case("coach_missing_field_502", [{
        "request": {"path": "/api/interview/review", "json": base_review},
        "provider_replies": [review_reply(evidence_ids, drop="verdict")],
    }])
    run_case("coach_unauthorized_evidence_502", [{
        "request": {"path": "/api/interview/review", "json": base_review},
        "provider_replies": [review_reply(["fabricated-evidence-id"],
                                          suggestions=1)],
    }])
    run_case("coach_provider_timeout_500", [{
        "request": {"path": "/api/interview/review", "json": base_review},
        "provider_replies": [{"raise": "timeout"}],
    }])
    run_case("coach_refusal_not_json_415", [{
        "request": {"path": "/api/interview/review", "data": "question=x"},
        "provider_replies": [],
    }])
    run_case("coach_refusal_missing_answer_400", [{
        "request": {"path": "/api/interview/review",
                    "json": {"question": question}},
        "provider_replies": [],
    }])
    run_case("coach_refusal_unknown_profile_404", [{
        "request": {"path": "/api/interview/review", "json": dict(
            base_review, profile_slug="ghost")},
        "provider_replies": [],
    }])
    run_case("coach_refusal_long_context_400", [{
        "request": {"path": "/api/interview/review", "json": dict(
            base_review, opportunity_context="x" * 4001)},
        "provider_replies": [],
    }])

    base_improve = {
        "question": question,
        "answer": answer,
        "family": "behavioral",
        "improvements": ["Name the stakeholder.", "Quantify the outcome."],
        "evidence_ids": evidence_ids[:2],
        "additional_context": "I later presented the result to leadership.",
        "profile_slug": "petec",
    }
    run_case("revision_success_full", [{
        "request": {"path": "/api/interview/improve", "json": dict(
            base_improve, opportunity_context=opportunity)},
        "provider_replies": [improvement_reply(evidence_ids[:1])],
    }])
    run_case("revision_success_no_selected_evidence", [{
        "request": {"path": "/api/interview/improve", "json": dict(
            base_improve, evidence_ids=[], additional_context="")},
        "provider_replies": [improvement_reply([], markers=False)],
    }])
    run_case("revision_refusal_unknown_evidence_403", [{
        "request": {"path": "/api/interview/improve", "json": dict(
            base_improve, evidence_ids=["fabricated-evidence-id"])},
        "provider_replies": [],
    }])
    run_case("revision_invalid_reply_502", [{
        "request": {"path": "/api/interview/improve", "json": base_improve},
        "provider_replies": [{"text": json.dumps({"draft": "", "changes": []})}],
    }])
    run_case("revision_provider_rate_limited_500", [{
        "request": {"path": "/api/interview/improve", "json": base_improve},
        "provider_replies": [{"raise": "rate_limited"}],
    }])

    base_nudge = {
        "question": question,
        "level": "experienced",
        "family": "behavioral",
        "competency": "Leadership",
        "practice_mode": "me",
        "profile_slug": "petec",
    }
    run_case("nudge_success_two_hints", [{
        "request": {"path": "/api/interview/nudge", "json": base_nudge},
        "provider_replies": [nudge_reply(2)],
    }])
    run_case("nudge_success_three_hints_video", [{
        "request": {"path": "/api/interview/nudge", "json": dict(
            base_nudge, practice_mode="video",
            opportunity_context=opportunity)},
        "provider_replies": [nudge_reply(3)],
    }])
    run_case("nudge_invalid_single_hint_502", [{
        "request": {"path": "/api/interview/nudge", "json": base_nudge},
        "provider_replies": [nudge_reply(1)],
    }])
    run_case("nudge_refusal_missing_question_400", [{
        "request": {"path": "/api/interview/nudge",
                    "json": dict(base_nudge, question="")},
        "provider_replies": [],
    }])

    base_model = {
        "question": question,
        "level": "experienced",
        "family": "behavioral",
        "mode": "member_history",
        "profile_slug": "petec",
    }
    run_case("grounded_success", [{
        "request": {"path": "/api/interview/model-answer", "json": base_model},
        "provider_replies": [model_answer_reply(evidence_ids[:2])],
    }])
    run_case("grounded_insufficient_200", [{
        "request": {"path": "/api/interview/model-answer", "json": base_model},
        "provider_replies": [model_answer_reply([], status="insufficient")],
    }])
    run_case("grounded_no_citation_502", [{
        "request": {"path": "/api/interview/model-answer", "json": base_model},
        "provider_replies": [model_answer_reply([], cite=False)],
    }])
    run_case("grounded_provider_overloaded_500", [{
        "request": {"path": "/api/interview/model-answer", "json": base_model},
        "provider_replies": [{"raise": "overloaded"}],
    }])
    run_case("generic_success", [{
        "request": {"path": "/api/interview/model-answer", "json": dict(
            base_model, mode="best_practice")},
        "provider_replies": [model_answer_reply([], cite=False)],
    }])
    run_case("generic_cites_evidence_502", [{
        "request": {"path": "/api/interview/model-answer", "json": dict(
            base_model, mode="best_practice")},
        "provider_replies": [model_answer_reply(evidence_ids[:1])],
    }])
    run_case("compare_success", [{
        "request": {"path": "/api/interview/model-answer", "json": dict(
            base_model, mode="compare", opportunity_context=opportunity)},
        "provider_replies": [
            model_answer_reply(evidence_ids[:2]),
            model_answer_reply([], cite=False),
        ],
    }])
    run_case("compare_grounded_fails_short_circuit_502", [{
        "request": {"path": "/api/interview/model-answer", "json": dict(
            base_model, mode="compare")},
        "provider_replies": [
            {"text": "no json here"},
            model_answer_reply([], cite=False),
        ],
    }])
    run_case("compare_generic_fails_502", [{
        "request": {"path": "/api/interview/model-answer", "json": dict(
            base_model, mode="compare")},
        "provider_replies": [
            model_answer_reply(evidence_ids[:2]),
            {"text": "no json here"},
        ],
    }])
    run_case("followup_member_history_success", [
        {
            "request": {"path": "/api/interview/model-answer",
                        "json": base_model},
            "provider_replies": [model_answer_reply(evidence_ids[:2])],
        },
        {
            "request": {"path": "/api/interview/model-answer", "json": dict(
                base_model,
                follow_up="What would you do differently next time?",
                context_token="__STEP1_CONTEXT_TOKEN__")},
            "provider_replies": [model_answer_reply(evidence_ids[:1])],
        },
    ])
    run_case("followup_context_mismatch_400", [
        {
            "request": {"path": "/api/interview/model-answer",
                        "json": base_model},
            "provider_replies": [model_answer_reply(evidence_ids[:2])],
        },
        {
            "request": {"path": "/api/interview/model-answer", "json": dict(
                base_model,
                follow_up="What would you do differently next time?",
                context_token="__STEP1_CONTEXT_TOKEN__",
                opportunity_context="a different role context")},
            "provider_replies": [],
        },
    ])

    # Correction C10: the provider-construction paths the original oracle
    # did not cover end to end — public best_practice and compare
    # follow-ups, and authenticated variants where authorization/context
    # construction changes the provider request. Recorded post-rejection
    # from the same untouched legacy checkpoint via a detached provenance
    # worktree; the pre-existing 32 fixtures re-record byte-identically in
    # the same run, which is the provenance proof.
    c10_provenance = (
        "Recorded post-rejection (correction C10) from legacy checkpoint "
        "73c4e63d via a detached provenance worktree; the original 32 "
        "fixtures re-recorded byte-identically in the same run."
    )
    run_case("followup_best_practice_success", [
        {
            "request": {"path": "/api/interview/model-answer", "json": dict(
                base_model, mode="best_practice")},
            "provider_replies": [model_answer_reply([], cite=False)],
        },
        {
            "request": {"path": "/api/interview/model-answer", "json": dict(
                base_model, mode="best_practice",
                follow_up="How would you adapt this for a startup?",
                context_token="__STEP1_CONTEXT_TOKEN__")},
            "provider_replies": [model_answer_reply([], cite=False)],
        },
    ], provenance=c10_provenance)
    run_case("followup_compare_success", [
        {
            "request": {"path": "/api/interview/model-answer", "json": dict(
                base_model, mode="compare",
                opportunity_context=opportunity)},
            "provider_replies": [
                model_answer_reply(evidence_ids[:2]),
                model_answer_reply([], cite=False),
            ],
        },
        {
            "request": {"path": "/api/interview/model-answer", "json": dict(
                base_model, mode="compare", opportunity_context=opportunity,
                follow_up="What metrics would you track afterwards?",
                context_token="__STEP1_CONTEXT_TOKEN__")},
            "provider_replies": [
                model_answer_reply(evidence_ids[:1]),
                model_answer_reply([], cite=False),
            ],
        },
    ], provenance=c10_provenance)

    auth_identity = {
        "display_name": "Casey Rivera",
        "user_key": "synthetic-user-key-0001",
    }
    owner_auth = {"owner": True, "identity": auth_identity}
    member_auth = {"owner": False, "identity": auth_identity}
    auth_review = {
        key: value for key, value in base_review.items()
        if key != "profile_slug"
    }
    run_case("auth_owner_review_success", [{
        "request": {"path": "/api/interview/review", "json": auth_review},
        "provider_replies": [review_reply(evidence_ids, suggestions=1)],
    }], auth=owner_auth, provenance=c10_provenance)
    run_case("auth_member_review_success_empty_evidence", [{
        "request": {"path": "/api/interview/review", "json": auth_review},
        "provider_replies": [review_reply([], suggestions=0)],
    }], auth=member_auth, provenance=c10_provenance)
    run_case("auth_review_marker_gate_400", [{
        "request": {"path": "/api/interview/review", "json": dict(
            auth_review, attempt=2,
            answer=answer + " [Describe the specific outcome you achieved.]")},
        "provider_replies": [],
    }], auth=owner_auth, provenance=c10_provenance)
    auth_model = {
        key: value for key, value in base_model.items()
        if key != "profile_slug"
    }
    run_case("auth_member_grounded_insufficient", [{
        "request": {"path": "/api/interview/model-answer", "json": auth_model},
        "provider_replies": [model_answer_reply([], status="insufficient")],
    }], auth=member_auth, provenance=c10_provenance)
    run_case("auth_followup_refused_400", [{
        "request": {"path": "/api/interview/model-answer", "json": dict(
            auth_model, follow_up="And what happened next?")},
        "provider_replies": [],
    }], auth=owner_auth, provenance=c10_provenance)
    auth_nudge = {
        key: value for key, value in base_nudge.items()
        if key != "profile_slug"
    }
    run_case("auth_nudge_success", [{
        "request": {"path": "/api/interview/nudge", "json": auth_nudge},
        "provider_replies": [nudge_reply(2)],
    }], auth=member_auth, provenance=c10_provenance)

    print("fixture recording complete")


if __name__ == "__main__":
    main()
