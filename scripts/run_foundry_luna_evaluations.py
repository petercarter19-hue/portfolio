#!/usr/bin/env python3
"""Run public/synthetic Luna evaluations behind explicit spend authorization.

Dry-run is the default.  Successful runs print only structural pass/fail and
usage aggregates; prompts, sources, model output, bearer tokens, and endpoint
identifiers are never written to the report.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.ai_foundation import (
    AIFoundationGateway,
    AIRequest,
    AnswerExpectation,
    AnswerState,
    Audience,
    Purpose,
    SourceVersion,
    evaluate_answer,
)

# Imported explicitly rather than from the package root: this adapter can spend
# money, and the shared package is loaded by the running website.
from services.ai_foundation.azure_foundry import (
    FOUNDRY_TOKEN_SCOPE,
    AzureFoundryResponsesProvider,
    FoundryUsage,
    SpendLedger,
    usd_to_micro_usd,
)
from services.ai_foundation.errors import AIFoundationError, ExecutionLimitError

ACTIVATED_ENV = "PEERSLATE_AZURE_QUALIFICATION_ACTIVATED"
CREDIT_ENV = "PEERSLATE_AZURE_CREDIT_CONFIRMED"
AUTHORIZATION_ENV = "PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF"
DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "azure_startup_qualification"
    / "luna_eval_cases.json"
)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    request: AIRequest
    sources: tuple[SourceVersion, ...]
    expectation: AnswerExpectation


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded Microsoft Foundry Luna evaluator"
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--endpoint")
    parser.add_argument("--deployment", default="gpt-5.6-luna")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--hard-cap-usd", default="1.25")
    parser.add_argument("--maximum-input-tokens", type=int, default=1500)
    parser.add_argument("--maximum-output-tokens", type=int, default=700)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def _entra_token() -> str:
    completed = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--scope",
            FOUNDRY_TOKEN_SCOPE,
            "--query",
            "accessToken",
            "--output",
            "tsv",
            "--only-show-errors",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError("Microsoft Entra token is unavailable")
    return completed.stdout.strip()


def _load_cases(path: Path) -> tuple[EvaluationCase, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"cases"}:
        raise ValueError("evaluation fixture must contain only cases")
    items = payload["cases"]
    if not isinstance(items, list) or not items or len(items) > 20:
        raise ValueError("evaluation fixture needs 1-20 cases")
    cases: list[EvaluationCase] = []
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("evaluation case must be an object")
        case_id = item["case_id"]
        subject_key = f"synthetic:{case_id}"
        purpose = Purpose(item["purpose"])
        audience = Audience(item["audience"])
        sources = tuple(
            SourceVersion.approved(
                source_version_key=source["source_version_key"],
                source_key=source["source_key"],
                version=source["version"],
                subject_key=subject_key,
                title=source["title"],
                content=source["content"],
                allowed_audiences=frozenset({audience}),
                allowed_purposes=frozenset({purpose}),
            )
            for source in item["sources"]
        )
        expected = item["expectation"]
        cases.append(
            EvaluationCase(
                case_id=case_id,
                request=AIRequest(
                    request_id=f"eval:{case_id}",
                    product="azure_startup_qualification_evaluation",
                    purpose=purpose,
                    audience=audience,
                    subject_key=subject_key,
                    question=item["question"],
                ),
                sources=sources,
                expectation=AnswerExpectation(
                    allowed_states=frozenset(
                        AnswerState(value) for value in expected["allowed_states"]
                    ),
                    minimum_claims=expected.get("minimum_claims", 0),
                    minimum_citations=expected.get("minimum_citations", 0),
                    minimum_follow_ups=expected.get("minimum_follow_ups", 0),
                    minimum_summary_words=expected.get("minimum_summary_words"),
                    maximum_summary_words=expected.get("maximum_summary_words"),
                    requires_boundary=expected.get("requires_boundary", False),
                    requires_handoff=expected.get("requires_handoff", False),
                ),
            )
        )
    return tuple(cases)


def _execution_authorized(args: argparse.Namespace) -> bool:
    return (
        args.execute
        and os.environ.get(ACTIVATED_ENV) == "true"
        and os.environ.get(CREDIT_ENV) == "true"
        and bool(os.environ.get(AUTHORIZATION_ENV, "").strip())
    )


def _plan(args: argparse.Namespace, case_count: int) -> dict[str, Any]:
    return {
        "mode": "execute" if _execution_authorized(args) else "dry_run",
        "provider": "Microsoft Foundry",
        "deployment": args.deployment,
        "case_count": case_count,
        "repeat": args.repeat,
        "maximum_calls": case_count * args.repeat,
        "hard_cap_usd": str(Decimal(args.hard_cap_usd)),
        "credit_confirmed": os.environ.get(CREDIT_ENV) == "true",
        "activation_enabled": os.environ.get(ACTIVATED_ENV) == "true",
        "spend_authorization_present": bool(
            os.environ.get(AUTHORIZATION_ENV, "").strip()
        ),
        "prompts_or_outputs_retained": False,
    }


def _spend_fields(ledger: SpendLedger, usages: list[FoundryUsage]) -> dict[str, Any]:
    """Cost evidence for any report, including a run that stopped early.

    A stop is exactly when this matters most: calls before the stop were
    already billed, so a report without these fields would hide real spend.

    ``calls_billed`` comes from the ledger, not from the usage sink, so the
    call count and the dollar figure always describe the same set of calls.  A
    call that failed after its reservation is charged in full and never reaches
    the usage sink, so counting the sink would report fewer calls than the
    money accounts for.  ``calls_with_usage`` is reported alongside it: the two
    differ by exactly the number of charged calls that returned no usable usage
    record, which is worth seeing when reconciling against the Azure bill.
    """
    snapshot = ledger.snapshot()
    return {
        "calls_billed": snapshot["calls"],
        "calls_with_usage": len(usages),
        "input_tokens": sum(item.input_tokens for item in usages),
        "output_tokens": sum(item.output_tokens for item in usages),
        "estimated_cost_usd": snapshot["spent_micro_usd"] / 1_000_000,
        "price_schedule_ref": usages[0].price_schedule_ref if usages else None,
    }


def main() -> int:
    args = _arguments()
    if args.repeat < 1 or args.repeat > 300:
        raise SystemExit("--repeat must be between 1 and 300")
    try:
        cases = _load_cases(args.fixture)
        hard_cap = usd_to_micro_usd(args.hard_cap_usd)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"evaluation plan unavailable: {error}", file=sys.stderr)
        return 2
    plan = _plan(args, len(cases))
    if not _execution_authorized(args):
        print(json.dumps(plan, sort_keys=True))
        return 0
    if args.fixture.resolve() != DEFAULT_FIXTURE.resolve():
        print(
            "authorized execution requires the fixed reviewed synthetic fixture",
            file=sys.stderr,
        )
        return 2
    if not args.endpoint:
        print("--endpoint is required for an authorized execution", file=sys.stderr)
        return 2

    usages: list[FoundryUsage] = []
    ledger = SpendLedger(
        hard_cap_micro_usd=hard_cap,
        max_calls=len(cases) * args.repeat,
    )
    provider = AzureFoundryResponsesProvider(
        endpoint=args.endpoint,
        deployment=args.deployment,
        token_provider=_entra_token,
        spend_ledger=ledger,
        usage_sink=usages.append,
        maximum_input_tokens=args.maximum_input_tokens,
        maximum_output_tokens=args.maximum_output_tokens,
    )
    gateway = AIFoundationGateway(provider)
    passed = 0
    failures: dict[str, int] = {}
    for _ in range(args.repeat):
        for case in cases:
            try:
                result = gateway.answer(case.request, case.sources)
            except ExecutionLimitError as error:
                # A bound was reached.  Stop, but report what was already
                # billed and say which bound fired: the dollar ceiling, the
                # call ceiling, and the pre-call input bound are all
                # ExecutionLimitError, and the last of them spends nothing.
                print(
                    json.dumps(
                        {
                            **plan,
                            **_spend_fields(ledger, usages),
                            "mode": "stopped",
                            "stop_category": "execution_limit",
                            "stop_reason": str(error),
                            "prompts_or_outputs_retained": False,
                        },
                        sort_keys=True,
                    )
                )
                return 2
            except AIFoundationError as error:
                # A single non-conforming answer is an evaluation failure, not
                # a reason to abandon the run.  Aborting here would also stop
                # the workload accruing the daily spend the plan depends on.
                failure = f"answer_rejected:{type(error).__name__}"
                failures[failure] = failures.get(failure, 0) + 1
                continue
            if result.trace.outcome != "completed":
                print(
                    json.dumps(
                        {
                            **plan,
                            **_spend_fields(ledger, usages),
                            "mode": "stopped",
                            "stop_category": "provider_unavailable",
                            "prompts_or_outputs_retained": False,
                        },
                        sort_keys=True,
                    )
                )
                return 2
            evaluation = evaluate_answer(
                case_id=case.case_id,
                answer=result.answer,
                expectation=case.expectation,
            )
            if evaluation.passed:
                passed += 1
            for failure in evaluation.failures:
                failures[failure] = failures.get(failure, 0) + 1

    print(
        json.dumps(
            {
                **plan,
                **_spend_fields(ledger, usages),
                "mode": "completed",
                "passed": passed,
                "failed": len(cases) * args.repeat - passed,
                "failure_categories": failures,
            },
            sort_keys=True,
        )
    )
    return 0 if passed == len(cases) * args.repeat else 1


if __name__ == "__main__":
    raise SystemExit(main())
