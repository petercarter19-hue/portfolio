"""Build the deterministic, wholly synthetic Search 3F fixture manifest."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

from run_public_search_dark_proof import (
    canonical_digest,
    schema_body,
    validate_fixture_manifest,
    validate_index_schema,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "docs"
    / "initiatives"
    / "PS-SEARCH-DARK-PROOF-001"
    / "fixtures"
    / "public-content-proof-manifest.json"
)
SCHEMA_OUTPUT = (
    ROOT
    / "docs"
    / "initiatives"
    / "PS-SEARCH-DARK-PROOF-001"
    / "schema"
    / "public-content-index-v3.json"
)

MEMBERS = {
    "pk_synth_001": ("alder-quist", "Alder Quist"),
    "pk_synth_002": ("mira-ostrand", "Mira Ostrand"),
    "pk_synth_003": ("ben-okafor", "Ben Okafor"),
}

SPECS = [
    ("pk_synth_001", "profile", "Alder Quist", "Platform engineer focused on data reliability.", None, ["aq"], "platform reliability engineer synthetic"),
    ("pk_synth_001", "experience", "Grid Migration Lead", "Led a two-year electrical grid data migration.", "2021-2023", ["grid-move"], "migration lead grid synthetic"),
    ("pk_synth_001", "impact", "Cut batch failures 80 percent", "Rebuilt the retry pipeline for nightly loads.", "2022", [], "batch failure reduction synthetic"),
    ("pk_synth_001", "skill", "Kubernetes Operations", "Cluster operations at production scale.", None, ["k8s", "kube"], "kubernetes containers orchestration synthetic"),
    ("pk_synth_001", "credential", "CKA Certification", "Certified Kubernetes Administrator.", "2023", ["cka"], "certification kubernetes synthetic"),
    ("pk_synth_001", "story_chapter", "The Night the Grid Went Quiet", "A story chapter about an outage postmortem.", None, [], "outage postmortem story synthetic"),
    ("pk_synth_002", "profile", "Mira Ostrand", "Clinical data analyst turned product lead.", None, [], "clinical analyst product synthetic"),
    ("pk_synth_002", "experience", "Trial Data Steward", "Ran integrity checks for a multi-site trial.", "2019-2022", ["steward"], "trial data steward synthetic"),
    ("pk_synth_002", "impact", "Zero audit findings three years running", "Standardized the site data intake checklist.", "2020-2022", [], "audit findings zero synthetic"),
    ("pk_synth_002", "skill", "Statistical Review", "Applied statistics for trial datasets.", None, ["stats"], "statistics review synthetic"),
    ("pk_synth_002", "credential", "SAS Advanced", "SAS advanced programmer credential.", "2018", [], "sas credential synthetic"),
    ("pk_synth_002", "story_chapter", "Counting What Counts", "A chapter on honest measurement.", None, [], "measurement story synthetic"),
    ("pk_synth_003", "profile", "Ben Okafor", "Field service manager moving into operations.", None, [], "field service operations synthetic"),
    ("pk_synth_003", "experience", "Regional Service Manager", "Managed a nine-team field region.", "2020-2024", [], "regional manager field synthetic"),
    ("pk_synth_003", "impact", "Halved mean time to repair", "Introduced a triage playbook for dispatch.", "2023", ["mttr"], "repair time halved synthetic"),
    ("pk_synth_003", "skill", "Dispatch Triage", "Prioritization under load.", None, [], "dispatch triage synthetic"),
    ("pk_synth_003", "credential", "Six Sigma Green Belt", "Process improvement credential.", "2021", ["ssgb"], "six sigma credential synthetic"),
    ("pk_synth_003", "story_chapter", "Nine Teams, One Radio", "A chapter about coordination.", None, [], "coordination story synthetic"),
    ("pk_synth_001", "skill", "Terraform Modules", "Infrastructure as code module design.", None, ["tf"], "terraform infrastructure synthetic"),
    ("pk_synth_002", "skill", "Data Contracts", "Schema contracts between producing teams.", None, [], "data contracts synthetic"),
]


def build() -> dict:
    documents = []
    for number, (owner, result_type, title, summary, period, aliases, extra) in enumerate(SPECS, 1):
        slug, display_name = MEMBERS[owner]
        projection_key = f"proj_{slug}_{result_type}_{number:03d}"
        identity = f"{projection_key}\x1f{owner}\x1frev1"
        document = {
            "document_id": "d1_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
            "profile_key": owner,
            "profile_slug": slug,
            "member_display_name": display_name,
            "audience": "public",
            "publication_revision_key": f"rev_{slug}_001",
            "projection_version_key": "v1",
            "projection_key": projection_key,
            "result_type": result_type,
            "destination": f"{result_type}:{slug}:{number:03d}",
            "title": title,
            "summary": summary,
            "search_text": unicodedata.normalize("NFC", f"{title} {summary} {extra}"),
            "aliases": aliases,
            "period_label": period,
            "locale": "en",
            "title_sort": unicodedata.normalize("NFC", title).casefold(),
            "schema_version": "1",
            "indexed_at": "2026-08-16T19:00:00Z",
            "withdrawn": False,
        }
        document["projection_digest"] = canonical_digest(document)
        documents.append(document)
    content_root = hashlib.sha256(
        "".join(sorted(item["projection_digest"] for item in documents)).encode("utf-8")
    ).hexdigest()
    manifest = {
        "manifest": "PS-SEARCH-DARK-PROOF-001 fixtures - SYNTHETIC, DARK PROOF ONLY",
        "canonicalization": "cv1: SHA-256 over NFC UTF-8 compact JSON, sorted keys, sorted aliases, absent optionals omitted",
        "member_count": len(MEMBERS),
        "document_count": len(documents),
        "content_digest_root": content_root,
        "slot_owners": {item["projection_key"]: item["profile_key"] for item in documents},
        "documents": documents,
    }
    validate_fixture_manifest(manifest)
    return manifest


def main() -> int:
    manifest = build()
    schema = schema_body()
    validate_index_schema(schema)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    SCHEMA_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_OUTPUT.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"manifest: {manifest['document_count']} documents, "
        f"{manifest['member_count']} synthetic members, "
        f"root {manifest['content_digest_root']}"
    )
    print(f"schema: 20 fields at {SCHEMA_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
