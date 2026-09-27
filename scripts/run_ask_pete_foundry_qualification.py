"""Finite, explicitly authorized LOCAL /api/chat qualification with real Foundry.

No production request, configuration, model deployment or baseline call. Without
--execute this validates the frozen packet and makes no credential/network call.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SUBSCRIPTION = "bd0ecf48-6940-4fd3-9687-3eaf72469d67"
ENDPOINT = "https://peerslate-foundry.openai.azure.com"


def azure(*arguments):
    executable = "az.cmd" if os.name == "nt" else "az"
    result = subprocess.run([executable, *arguments, "--subscription", SUBSCRIPTION, "-o", "json"],
                            capture_output=True, text=True, timeout=45, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--owner-authorization-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.manifest_sha256:
        raise ValueError("frozen manifest digest differs")
    manifest = json.loads(raw)
    if set(manifest) != {"candidate_sha", "owner_authorization_ref", "endpoint", "deployment",
                         "model_version", "reasoning_effort", "max_provider_calls", "hard_cap_micro_usd",
                         "maximum_seconds", "minimum_start_interval_seconds", "cases"}:
        raise ValueError("unknown qualification manifest")
    if manifest["owner_authorization_ref"] != args.owner_authorization_ref or not args.owner_authorization_ref.strip():
        raise ValueError("exact owner operation reference is required")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != manifest["candidate_sha"] or subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise ValueError("qualification requires the exact clean frozen candidate")
    if (manifest["endpoint"] != ENDPOINT or manifest["deployment"] != "gpt-6-luna"
        or manifest["model_version"] != "2026-09-22" or manifest["reasoning_effort"] != "low"):
        raise ValueError("qualified deployment tuple differs")
    cases = manifest["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 6:
        raise ValueError("at most six questions are admitted")
    if (type(manifest["max_provider_calls"]) is not int or manifest["max_provider_calls"] != 2 * len(cases)
        or type(manifest["hard_cap_micro_usd"]) is not int or not 0 < manifest["hard_cap_micro_usd"] <= 2_000_000
        or type(manifest["maximum_seconds"]) is not int or not 0 < manifest["maximum_seconds"] <= 600
        or type(manifest["minimum_start_interval_seconds"]) is not int
        or not 65 <= manifest["minimum_start_interval_seconds"] <= 90):
        raise ValueError("qualification ceilings differ")
    ids = set()
    for case in cases:
        if (not isinstance(case, dict) or set(case) != {"id", "message", "action", "expected_states"}
            or not isinstance(case["id"], str) or case["id"] in ids
            or not isinstance(case["message"], str) or not 1 <= len(case["message"]) <= 1000
            or case["action"] not in (None, "recruiter_brief", "evidence_finder", "interview_preparation")
            or not isinstance(case["expected_states"], list) or not case["expected_states"]
            or not set(case["expected_states"]) <= {"supported", "partially_supported", "not_established", "ambiguous", "refused"}):
            raise ValueError("invalid frozen question")
        ids.add(case["id"])
    destination = args.output.resolve()
    if destination.is_relative_to(ROOT.resolve()) or destination.exists():
        raise ValueError("use a new evidence directory outside the checkout")
    from services.ai_foundation.azure_foundry import LunaPriceSchedule, SpendLedger
    from services.ask_pete.foundry_provider import FoundryGroundedProvider, MAX_INPUT_TOKENS, MAX_ANSWER_TOKENS, MAX_SUPPORT_TOKENS
    reserve = sum(LunaPriceSchedule().estimate_micro_usd(input_tokens=MAX_INPUT_TOKENS, output_tokens=n)
                  for n in (MAX_ANSWER_TOKENS, MAX_SUPPORT_TOKENS)) * len(cases)
    if reserve > manifest["hard_cap_micro_usd"]:
        raise ValueError("budget cannot reserve every permitted call")
    if not args.execute:
        print(json.dumps({"ready": True, "executed": False, "questions": len(cases), "maximum_reservation_micro_usd": reserve}))
        return
    deployment = azure("cognitiveservices", "account", "deployment", "show", "--resource-group", "peerslate",
                       "--name", "peerslate-foundry", "--deployment-name", "gpt-6-luna")
    properties = deployment["properties"]
    if (properties["model"]["version"] != manifest["model_version"]
        or properties["model"]["name"] != "gpt-6-luna"
        or properties["versionUpgradeOption"] != "NoAutoUpgrade"
        or properties["provisioningState"] != "Succeeded"):
        raise ValueError("current Azure deployment is not the frozen model version")
    # Token exists only in this process, never in the evidence or stdout.
    token = azure("account", "get-access-token", "--resource", "https://cognitiveservices.azure.com/")["accessToken"]
    os.environ.setdefault("ANTHROPIC_API_KEY", "unused-local-qualification-placeholder")
    import app as app_module
    from services.ask_pete import runtime
    app_module.app.config.update(TESTING=True, PEERSLATE_ASK_PETE_FOUNDRY_ENABLED=True,
                                 PEERSLATE_ASK_PETE_FOUNDRY_ENDPOINT=ENDPOINT)
    app_module.limiter.enabled = False
    ledger = SpendLedger(hard_cap_micro_usd=manifest["hard_cap_micro_usd"], max_calls=manifest["max_provider_calls"])
    destination.mkdir(parents=True)
    (destination / "manifest.json").write_bytes(raw)
    (destination / "deployment.json").write_text(json.dumps(deployment, indent=2), encoding="utf-8")
    records, started, prior = [], time.monotonic(), None
    def provider(**kwargs):
        return FoundryGroundedProvider(**kwargs, spend_ledger=ledger)
    with patch.object(runtime, "_foundry_token", return_value=token), \
         patch("services.ask_pete.foundry_provider.FoundryGroundedProvider", side_effect=provider):
        for case in cases:
            if prior is not None:
                time.sleep(max(0, manifest["minimum_start_interval_seconds"] - (time.monotonic() - prior)))
            if time.monotonic() - started + 20 > manifest["maximum_seconds"]:
                break
            events = []
            prior = time.monotonic()
            with patch.object(app_module, "_record_ask_pete_execution", side_effect=events.append):
                response = app_module.app.test_client().post("/api/chat", json={"message": case["message"], "action": case["action"]},
                    headers={"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"})
            row = {"case_id": case["id"], "http_status": response.status_code,
                   "elapsed_seconds": time.monotonic() - prior, "answer": response.get_json(),
                   "events": events, "ledger": ledger.snapshot()}
            row["state_expected"] = row["answer"].get("state") in case["expected_states"]
            records.append(row)
            (destination / f"{len(records):02d}.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
            print(json.dumps({"case_id": case["id"], "state": row["answer"].get("state"), "seconds": row["elapsed_seconds"]}), flush=True)
            if not row["state_expected"] or row["ledger"]["reserved_micro_usd"] or row["answer"].get("state") == "unavailable":
                break  # No retries or further work while an abandoned call may remain.
    summary = {"questions_completed": len(records), "questions_planned": len(cases), "ledger": ledger.snapshot(),
               "duration_seconds": time.monotonic() - started, "semantic_review": "pending",
               "production_changed": False, "all_states_expected": len(records) == len(cases) and all(r["state_expected"] for r in records)}
    (destination / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
