"""Interactive local review server for Opportunity Slate v2 R1.

Uses the same stateful stored-procedure contract fake as the browser gauntlet.
All data is process-local and disappears when the server stops.

Usage: serve_review_v2.py [port]
"""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ANTHROPIC_API_KEY", "placeholder-not-a-real-key")

import opportunity_slate_v2_routes as routes  # noqa: E402
from services.opportunity_slate_v2_service import OpportunitySlateV2Service  # noqa: E402
from tests.test_opportunity_slate_v2 import make_app  # noqa: E402

from functional_gauntlet_v2 import StatefulDatabase  # noqa: E402


port = int(sys.argv[1]) if len(sys.argv) > 1 else 5110
app, _unused_database, _patcher = make_app()
app.config["TESTING"] = False
app.add_url_rule(
    "/auth/session",
    endpoint="local_review_auth_session",
    view_func=lambda: {"authenticated": True},
)
routes.opportunity_slate_v2_service = OpportunitySlateV2Service(
    database=StatefulDatabase()
)

print(
    f"Local disposable review: http://127.0.0.1:{port}/opportunity-slate",
    flush=True,
)
app.run(host="127.0.0.1", port=port, use_reloader=False)
