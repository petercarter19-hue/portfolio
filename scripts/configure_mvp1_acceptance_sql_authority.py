"""Read-only G privilege plan. Never connects, grants or executes SQL."""
import json


def plan():
    return {'status': 'proposal_not_applied', 'production_authority': False,
            'target': 'invocation-owned isolated proof databases only',
            'direct_table_grants': [],
            'grant_execute': ['usp_GetResumeDraftForOwner', 'usp_CommitResumeDraftCommandForOwner',
                'usp_GetResumeMediaDraftForOwner', 'usp_CommitResumeMediaCommandForOwner', 'usp_GetResumeCatalogAsset',
                'usp_GetResumePublicationForOwner', 'usp_GetPublicResumePublicationBySlug',
                'usp_CommitResumePublicationCommandForOwner', 'usp_GetMemberVisitorAiBySlug',
                'usp_GetMemberVisitorAiPreviewForOwner'],
            'deny_execute': ['usp_MemberVisitorAiSnapshotInternal',
                'usp_ResumePublicationBuildManifestsInternal', 'usp_ResumePublicationApplyCanonicalInternal',
                'usp_ResumePublicationRefreshProjectionInternal'],
            'owner_authorization': 'server-derived owner; grants alone do not authorize a subject'}


if __name__ == '__main__':
    print(json.dumps(plan(), indent=2))
