"""Read-only F disposable privilege plan. No apply mode or production connection."""
import json


def plan():
    return {'status':'proposal_not_applied','target':'invocation-owned isolated proof databases only',
            'grant_execute':['usp_GetMemberVisitorAiBySlug','usp_GetMemberVisitorAiPreviewForOwner'],
            'deny_execute':['usp_MemberVisitorAiSnapshotInternal'],
            'production_authority':False,'direct_table_grants':[]}


if __name__=='__main__': print(json.dumps(plan(),indent=2))
