"""Produce a secret-safe usage summary for explicitly selected Codex sessions.

The helper reads only structured ``token_usage_record`` and ``turn_context``
records from the supplied JSONL files.  It never emits transcript content,
local paths, raw parser errors, response identifiers, prices, or cost claims.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SESSION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
SAFE_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
SAFE_EFFORT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
METRICS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)
OPTIONAL_METRICS = {"cache_write_input_tokens", "reasoning_output_tokens"}
MetricValues = dict[str, int | None]


class UsageSummaryError(Exception):
    """A closed, content-free failure suitable for user-facing output."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SessionSelection:
    session_id: str
    path: Path | None
    selection_error: str | None = None


def _safe_label(value: Any, pattern: re.Pattern[str]) -> str:
    return value if isinstance(value, str) and pattern.fullmatch(value) else "unavailable"


def _timestamp(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.timestamp()


def _metric_dict(value: Any) -> MetricValues:
    if not isinstance(value, dict):
        raise UsageSummaryError("invalid_usage_record")
    result: MetricValues = {}
    for name in METRICS:
        if name in OPTIONAL_METRICS and name not in value:
            result[name] = None
            continue
        item = value.get(name)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise UsageSummaryError("invalid_usage_record")
        result[name] = item
    input_tokens = result["input_tokens"]
    cached_input_tokens = result["cached_input_tokens"]
    output_tokens = result["output_tokens"]
    cache_write_input_tokens = result["cache_write_input_tokens"]
    reasoning_output_tokens = result["reasoning_output_tokens"]
    assert isinstance(input_tokens, int)
    assert isinstance(cached_input_tokens, int)
    assert isinstance(output_tokens, int)
    if cached_input_tokens > input_tokens:
        raise UsageSummaryError("invalid_usage_record")
    if (
        cache_write_input_tokens is not None
        and cache_write_input_tokens > input_tokens
    ):
        raise UsageSummaryError("invalid_usage_record")
    if (
        reasoning_output_tokens is not None
        and reasoning_output_tokens > output_tokens
    ):
        raise UsageSummaryError("invalid_usage_record")
    total = value.get("total_tokens")
    if total is not None and (
        isinstance(total, bool)
        or not isinstance(total, int)
        or total != input_tokens + output_tokens
    ):
        raise UsageSummaryError("invalid_usage_record")
    return result


def _add_metrics(target: MetricValues, values: MetricValues) -> None:
    for name in METRICS:
        current = target[name]
        incoming = values[name]
        target[name] = (
            current + incoming
            if isinstance(current, int) and isinstance(incoming, int)
            else None
        )


def _cumulative_decreased(current: MetricValues, previous: MetricValues) -> bool:
    return any(
        isinstance(current[name], int)
        and isinstance(previous[name], int)
        and current[name] < previous[name]
        for name in METRICS
    )


def _metric_delta(current: MetricValues, previous: MetricValues) -> MetricValues:
    return {
        name: (
            current[name] - previous[name]
            if isinstance(current[name], int) and isinstance(previous[name], int)
            else None
        )
        for name in METRICS
    }


def _public_metrics(values: MetricValues) -> dict[str, int | str]:
    input_tokens = values["input_tokens"]
    cached_input_tokens = values["cached_input_tokens"]
    output_tokens = values["output_tokens"]
    assert isinstance(input_tokens, int)
    assert isinstance(cached_input_tokens, int)
    assert isinstance(output_tokens, int)
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "cache_write_input_tokens_included_in_input": (
            values["cache_write_input_tokens"]
            if values["cache_write_input_tokens"] is not None
            else "unavailable"
        ),
        "fresh_input_tokens": input_tokens - cached_input_tokens,
        "output_tokens": output_tokens,
        "reasoning_output_tokens_included_in_output": (
            values["reasoning_output_tokens"]
            if values["reasoning_output_tokens"] is not None
            else "unavailable"
        ),
        "total_tokens": input_tokens + output_tokens,
    }


def summarize_session(selection: SessionSelection) -> dict[str, Any]:
    """Summarize one exact session without exposing untrusted record content."""

    empty = {name: 0 for name in METRICS}
    result: dict[str, Any] = {
        "session_id": selection.session_id,
        "status": "unavailable",
        "reason": selection.selection_error or "token_usage_record_absent",
        "elapsed_seconds_observed": None,
    }
    if not SESSION_ID_RE.fullmatch(selection.session_id):
        result["reason"] = "invalid_session_id"
        return result
    if selection.selection_error is not None or selection.path is None:
        return result

    turn_models: dict[str, tuple[str, str]] = {}
    unique_records: dict[str, tuple[MetricValues, str, str]] = {}
    session_meta_ids: set[str] = set()
    root_session_ids: set[str] = set()
    duplicates = 0
    resets = 0
    model_changes = 0
    prior_cumulative: MetricValues | None = None
    prior_model: str | None = None
    current_model = ("unavailable", "unavailable")
    fallback_samples: list[tuple[MetricValues, str, str]] = []
    fallback_error: str | None = None
    first_timestamp: float | None = None
    last_timestamp: float | None = None
    service_tiers: set[str] = set()
    speeds: set[str] = set()

    try:
        with selection.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, UnicodeError):
                    raise UsageSummaryError("invalid_jsonl")
                if not isinstance(record, dict):
                    raise UsageSummaryError("invalid_jsonl")
                observed_timestamp = _timestamp(record.get("timestamp"))
                if observed_timestamp is not None:
                    first_timestamp = (
                        observed_timestamp
                        if first_timestamp is None
                        else min(first_timestamp, observed_timestamp)
                    )
                    last_timestamp = (
                        observed_timestamp
                        if last_timestamp is None
                        else max(last_timestamp, observed_timestamp)
                    )
                record_type = record.get("type")
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue

                if record_type == "session_meta":
                    meta_id = payload.get("id")
                    if isinstance(meta_id, str):
                        session_meta_ids.add(meta_id)
                    continue

                if record_type == "turn_context":
                    turn_id = payload.get("turn_id")
                    if isinstance(turn_id, str):
                        turn_models[turn_id] = (
                            _safe_label(payload.get("model"), SAFE_MODEL_RE),
                            _safe_label(payload.get("effort"), SAFE_EFFORT_RE),
                        )
                        current_model = turn_models[turn_id]
                    service_tier = _safe_label(payload.get("service_tier"), SAFE_EFFORT_RE)
                    speed = _safe_label(payload.get("speed"), SAFE_EFFORT_RE)
                    if service_tier != "unavailable":
                        service_tiers.add(service_tier)
                    if speed != "unavailable":
                        speeds.add(speed)
                    continue

                # event_msg/token_count mirrors the same accounting and is
                # retained only as a legacy fallback. It is never added to the
                # canonical token_usage_record stream.
                if record_type == "event_msg" and payload.get("type") == "token_count":
                    try:
                        info = payload.get("info")
                        if not isinstance(info, dict):
                            raise UsageSummaryError("invalid_cumulative_usage_record")
                        cumulative = _metric_dict(info.get("total_token_usage"))
                        fallback_samples.append(
                            (cumulative, current_model[0], current_model[1])
                        )
                    except UsageSummaryError as error:
                        fallback_error = error.code
                    continue
                if record_type != "token_usage_record":
                    continue

                thread_identity = payload.get("thread_id", payload.get("session_id"))
                if thread_identity != selection.session_id:
                    raise UsageSummaryError("session_id_mismatch")
                root_session_id = payload.get("session_id")
                if not isinstance(root_session_id, str) or not SESSION_ID_RE.fullmatch(
                    root_session_id
                ):
                    raise UsageSummaryError("invalid_root_session_id")
                root_session_ids.add(root_session_id)
                response_id = payload.get("response_id")
                turn_id = payload.get("turn_id")
                if not isinstance(response_id, str) or not response_id:
                    raise UsageSummaryError("missing_response_identity")
                values = _metric_dict(payload.get("usage"))
                model, effort = turn_models.get(turn_id, ("unavailable", "unavailable"))
                existing = unique_records.get(response_id)
                candidate = (values, model, effort)
                if existing is not None:
                    if existing[0] != values:
                        raise UsageSummaryError("conflicting_duplicate_record")
                    duplicates += 1
                    continue

                cumulative_value = payload.get("thread_token_usage")
                if isinstance(cumulative_value, dict):
                    cumulative = _metric_dict(cumulative_value)
                    if prior_cumulative is not None and _cumulative_decreased(
                        cumulative, prior_cumulative
                    ):
                        resets += 1
                    prior_cumulative = cumulative

                if prior_model is not None and model != prior_model:
                    model_changes += 1
                prior_model = model
                unique_records[response_id] = candidate
    except FileNotFoundError:
        result["reason"] = "session_file_missing"
        return result
    except OSError:
        result["reason"] = "session_file_unreadable"
        return result
    except UnicodeError:
        result["reason"] = "invalid_jsonl"
        return result
    except UsageSummaryError as error:
        result["reason"] = error.code
        return result

    if not session_meta_ids:
        result["reason"] = "session_meta_missing"
        return result
    if session_meta_ids != {selection.session_id}:
        result["reason"] = "session_meta_mismatch"
        return result
    if len(root_session_ids) > 1:
        result["reason"] = "root_session_id_mismatch"
        return result
    if not unique_records:
        if fallback_error is not None:
            result["reason"] = fallback_error
            return result
        if not fallback_samples:
            return result

        totals = dict(empty)
        by_model: dict[tuple[str, str], MetricValues] = {}
        prior: MetricValues | None = None
        sample_count = 0
        prior_model = None
        for cumulative, model, effort in fallback_samples:
            if prior is not None and cumulative == prior:
                duplicates += 1
                continue
            if prior is None or _cumulative_decreased(cumulative, prior):
                if prior is not None:
                    resets += 1
                delta = dict(cumulative)
            else:
                delta = _metric_delta(cumulative, prior)
            if prior_model is not None and model != prior_model:
                model_changes += 1
            prior_model = model
            prior = cumulative
            sample_count += 1
            _add_metrics(totals, delta)
            bucket = by_model.setdefault((model, effort), dict(empty))
            _add_metrics(bucket, delta)
        fallback_result = {
            "session_id": selection.session_id,
            "status": "available",
            "source": "event_msg.token_count.cumulative_fallback",
            "usage_records_counted": sample_count,
            "duplicate_records_ignored": duplicates,
            "cumulative_resets_observed": resets,
            "model_changes_observed": model_changes,
            "usage": _public_metrics(totals),
            "models": [
                {
                    "model": model,
                    "effort": effort,
                    "usage": _public_metrics(values),
                }
                for (model, effort), values in sorted(by_model.items())
            ],
            "coverage": (
                "Legacy cumulative fallback; each unique cumulative snapshot is "
                "counted once and decreases begin a new cumulative segment."
            ),
            "elapsed_seconds_observed": round(last_timestamp - first_timestamp, 3)
            if first_timestamp is not None and last_timestamp is not None
            else None,
            "known_waiting_seconds": {
                "status": "unavailable",
                "reason": "not_in_structured_usage_records",
            },
            "service_tiers_observed": sorted(service_tiers)
            if service_tiers
            else "unavailable",
            "speeds_observed": sorted(speeds) if speeds else "unavailable",
        }
        return fallback_result

    totals = dict(empty)
    by_model: dict[tuple[str, str], MetricValues] = {}
    for values, model, effort in unique_records.values():
        _add_metrics(totals, values)
        bucket = by_model.setdefault((model, effort), dict(empty))
        _add_metrics(bucket, values)

    canonical_result = {
        "session_id": selection.session_id,
        "status": "available",
        "source": "token_usage_record",
        "usage_records_counted": len(unique_records),
        "duplicate_records_ignored": duplicates,
        "cumulative_resets_observed": resets,
        "model_changes_observed": model_changes,
        "usage": _public_metrics(totals),
        "models": [
            {
                "model": model,
                "effort": effort,
                "usage": _public_metrics(values),
            }
            for (model, effort), values in sorted(by_model.items())
        ],
        "elapsed_seconds_observed": round(last_timestamp - first_timestamp, 3)
        if first_timestamp is not None and last_timestamp is not None
        else None,
        "known_waiting_seconds": {
            "status": "unavailable",
            "reason": "not_in_structured_usage_records",
        },
        "service_tiers_observed": sorted(service_tiers)
        if service_tiers
        else "unavailable",
        "speeds_observed": sorted(speeds) if speeds else "unavailable",
    }
    if root_session_ids:
        canonical_result["root_session_id"] = next(iter(root_session_ids))
    return canonical_result


def summarize(selections: Iterable[SessionSelection]) -> dict[str, Any]:
    selections = list(selections)
    ids = [item.session_id for item in selections]
    resolved_paths = [
        str(item.path.resolve()) for item in selections if item.path is not None
    ]
    if len(ids) != len(set(ids)) or len(resolved_paths) != len(set(resolved_paths)):
        raise UsageSummaryError("duplicate_session_selection")
    if not selections:
        raise UsageSummaryError("no_sessions_selected")

    sessions = [summarize_session(item) for item in selections]
    totals = {name: 0 for name in METRICS}
    available = 0
    for session in sessions:
        if session["status"] != "available":
            continue
        available += 1
        public = session["usage"]
        _add_metrics(
            totals,
            {
                "input_tokens": public["input_tokens"],
                "cached_input_tokens": public["cached_input_tokens"],
                "cache_write_input_tokens": public[
                    "cache_write_input_tokens_included_in_input"
                ],
                "output_tokens": public["output_tokens"],
                "reasoning_output_tokens": public[
                    "reasoning_output_tokens_included_in_output"
                ],
            },
        )
    status = "available" if available == len(sessions) else "partial"
    if available == 0:
        status = "unavailable"
    return {
        "schema_version": 1,
        "status": status,
        "sessions_selected": len(sessions),
        "sessions_available": available,
        "usage": _public_metrics(totals) if available else None,
        "sessions": sessions,
        "interpretation": (
            "Observed local token counters only; cached input and any exposed cache-write "
            "input are included in input, and any exposed reasoning output is included in "
            "output. This is not a billing, "
            "invoice, price, quota, or live-usage claim. Elapsed time is the observed "
            "log timestamp span and does not subtract or infer waiting."
        ),
        "bounded_evidence": {
            "accepted_outcome": {
                "status": "unavailable",
                "reason": "requires_completion_evidence_source",
            },
            "rework": {
                "status": "unavailable",
                "reason": "requires_completion_evidence_source",
            },
            "interventions": {
                "status": "unavailable",
                "reason": "requires_completion_evidence_source",
            },
            "known_waiting": {
                "status": "unavailable",
                "reason": "requires_completion_evidence_source",
            },
        },
    }


def render_text(summary: dict[str, Any]) -> str:
    lines = [
        "Agent usage summary (observed local counters; not billing)",
        (
            f"Sessions: {summary['sessions_available']}/{summary['sessions_selected']} "
            f"available ({summary['status']})"
        ),
    ]
    usage = summary.get("usage")
    if isinstance(usage, dict):
        lines.extend(
            [
                f"Input tokens: {usage['input_tokens']:,}",
                f"  Cached input subset: {usage['cached_input_tokens']:,}",
                (
                    "  Cache-write input subset: "
                    f"{_format_counter(usage['cache_write_input_tokens_included_in_input'])}"
                ),
                f"  Fresh input: {usage['fresh_input_tokens']:,}",
                f"Output tokens: {usage['output_tokens']:,}",
                (
                    "  Reasoning output subset (already included): "
                    f"{_format_counter(usage['reasoning_output_tokens_included_in_output'])}"
                ),
                f"Total tokens (input + output): {usage['total_tokens']:,}",
            ]
        )
    for session in summary["sessions"]:
        if session["status"] == "available":
            models = ", ".join(
                f"{item['model']}/{item['effort']}" for item in session["models"]
            )
            elapsed = session.get("elapsed_seconds_observed")
            elapsed_text = f"{elapsed:,.3f}s observed" if isinstance(elapsed, (int, float)) else "elapsed unavailable"
            lines.append(
                f"Session {session['session_id']}: available, "
                f"{session['usage_records_counted']} usage records; {models}; {elapsed_text}; "
                "known waiting unavailable"
            )
        else:
            lines.append(
                f"Session {session['session_id']}: unavailable ({session['reason']})"
            )
    lines.append(summary["interpretation"])
    return "\n".join(lines)


def _format_counter(value: Any) -> str:
    return (
        f"{value:,}"
        if isinstance(value, int) and not isinstance(value, bool)
        else "unavailable"
    )


def _selection(value: str) -> SessionSelection:
    session_id, separator, raw_path = value.partition("=")
    if not separator or not raw_path or not SESSION_ID_RE.fullmatch(session_id):
        raise argparse.ArgumentTypeError("expected SESSION_ID=JSONL_PATH")
    return SessionSelection(session_id=session_id, path=Path(raw_path))


def _discover(session_id: str, roots: Iterable[Path]) -> SessionSelection:
    if not SESSION_ID_RE.fullmatch(session_id):
        return SessionSelection(session_id=session_id, path=None, selection_error="invalid_session_id")
    roots = list(roots)
    if not roots:
        return SessionSelection(
            session_id=session_id,
            path=None,
            selection_error="sessions_root_not_supplied",
        )
    suffix = f"-{session_id}.jsonl"
    matches: list[Path] = []
    for root in roots:
        try:
            matches.extend(
                path for path in root.rglob("*.jsonl") if path.name.endswith(suffix)
            )
        except OSError:
            continue
    unique = sorted({path.resolve() for path in matches}, key=str)
    if not unique:
        return SessionSelection(
            session_id=session_id,
            path=None,
            selection_error="session_file_missing",
        )
    if len(unique) != 1:
        return SessionSelection(
            session_id=session_id,
            path=None,
            selection_error="ambiguous_session_file",
        )
    return SessionSelection(session_id=session_id, path=unique[0])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session",
        action="append",
        default=[],
        type=_selection,
        metavar="SESSION_ID=JSONL_PATH",
        help="exact root or child session; repeat once per session",
    )
    parser.add_argument(
        "--session-id",
        action="append",
        default=[],
        metavar="SESSION_ID",
        help="discover one exact session under --sessions-root; repeat for children",
    )
    parser.add_argument(
        "--sessions-root",
        action="append",
        default=[],
        type=Path,
        metavar="DIRECTORY",
        help="root searched only for exact rollout filename suffixes",
    )
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        selections = list(args.session)
        selections.extend(_discover(item, args.sessions_root) for item in args.session_id)
        report = summarize(selections)
    except UsageSummaryError as error:
        report = {
            "schema_version": 1,
            "status": "unavailable",
            "reason": error.code,
            "sessions_selected": 0,
            "sessions_available": 0,
            "usage": None,
            "sessions": [],
            "interpretation": "Observed local counters unavailable; no billing claim.",
        }
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] in {"available", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
