"""Serve the production public-demo fallback over an empty fake real Feed.

The harness exercises the registered Community routes and the real API fallback
without reading or writing Community persistence. It binds to localhost only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ANTHROPIC_API_KEY", "local-preview-placeholder")
os.environ["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = "true"
os.environ["PEERSLATE_COMMUNITY_SIGNING_KEY"] = "local-preview-signing-key"

from app import app
import community_api
from services.community_contracts import CommunityNotFoundError


class EmptyPublicFeed:
    def feed_page(self, *_args, **_kwargs):
        return {"items": [], "next_cursor": None, "caught_up": True, "window_limit": 120}

    def post_detail(self, *_args, **_kwargs):
        raise CommunityNotFoundError("Post not found.")

    def shelf_page(self, *_args, **_kwargs):
        raise CommunityNotFoundError("Post not found.")

    def selected_contribution(self, *_args, **_kwargs):
        raise CommunityNotFoundError("Contribution not found.")

    def search(self, *_args, **_kwargs):
        return []


community_api.community_feed_service = EmptyPublicFeed()
owner_preview = os.environ.get("PEERSLATE_PUBLIC_DEMO_PREVIEW_OWNER", "false").lower() == "true"
owner_preview_key = "community-public-demo-preview-owner"
app.config.update(
    TESTING=True,
    PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
    PEERSLATE_DEV_USER_KEY=owner_preview_key if owner_preview else None,
    PEERSLATE_OWNER_USER_KEYS=owner_preview_key if owner_preview else "",
)


if __name__ == "__main__":
    port = int(os.environ.get("PEERSLATE_PUBLIC_DEMO_PREVIEW_PORT", "5077"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
