"""Propose least-privilege publication SQL grants. Production apply is refused.

This is not schema application and not a production permission change.
"""

from __future__ import annotations

import argparse
import json
import sys


PROOF_ID = "ps-mvp1-ef-sql-proof-20260916-01"
PROPOSED_PROCEDURES = (
    "usp_CommitEntryPolicyCommandForOwner",
    "usp_GetEntryPolicyEntryForOwner",
    "usp_CommitResumePublicationCommandForOwner",
    "usp_GetResumePublicationForOwner",
    "usp_GetResumePublicationReceiptForOwner",
    "usp_GetPublicResumePublicationBySlug",
    "usp_GetResumePublicationMediaAuthorization",
    "usp_ListResumePublicationPolicyForOwner",
    "usp_ListEntryPolicyEntriesForOwner",
    "usp_GetResumeCatalogAsset",
    "usp_CommitResumeCatalogCommandForOwner",
)
DENIED_INTERNAL = (
    "usp_ResumePublicationApplyCanonicalInternal",
    "usp_ResumePublicationRefreshProjectionInternal",
    "usp_ResumePublicationEncodeSourceInternal",
    "usp_ResumePublicationLockOwnerInternal",
    "usp_ResumePublicationBuildManifestsInternal",
    "usp_ResumePublicationGuardLegacyMutator",
    "usp_ResumePublicationApplyAfterPolicyInternal",
    "usp_ResumeCatalogApplyInternal",
)


def plan() -> dict:
    return {
        "mode": "plan",
        "proof_id": PROOF_ID,
        "status": "proposal_not_applied",
        "target": "disposable proof databases only",
        "grant_execute": list(PROPOSED_PROCEDURES),
        "deny_execute": list(DENIED_INTERNAL),
        "deny_table_dml": [
            "resume_sharing_state",
            "resume_publication_revisions",
            "resume_publication_evidence",
            "resume_publication_receipts",
            "resume_publication_outbox",
            "resume_catalog_assets",
        ],
        "production_apply": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "reason": "Production or disposable permission apply is withheld until a new exact reviewed authorization.",
                }
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(plan(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
