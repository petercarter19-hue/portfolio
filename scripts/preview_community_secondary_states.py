"""Serve a fixture-only Community conversation tranche for local visual review.

This is intentionally separate from the approved primary Feed harness. It
renders the real Community template, CSS, and JavaScript with in-memory,
Pete-only conversation data. It never reads or writes Community persistence,
does not upload a file, and rejects public-post creation explicitly.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ANTHROPIC_API_KEY", "local-preview-placeholder")
os.environ["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = "true"
os.environ["PEERSLATE_COMMUNITY_SIGNING_KEY"] = "local-preview-signing-key"

from flask import Response, jsonify, render_template, request

from app import app


POST_KEY = "55555555-5555-4555-8555-555555555555"
FOCUSED_CONTRIBUTION_KEY = "66666666-6666-4666-8666-000000000003"
RESPONSE_INTENTIONS = {"celebrate", "support", "i_relate", "ask", "offer_help"}
fixture_response = None
fixture_contributions: list[dict] = []


def timestamp(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")


def author() -> dict:
    return {
        "display_name": "Pete Carter",
        "avatar_url": "/static/images/story/pete-headshot-m.jpg",
    }


def initial_contributions() -> list[dict]:
    return [
        {
            "key": "66666666-6666-4666-8666-000000000001",
            "author": author(),
            "body": "I framed it around the owners and evidence that would change the decision.",
            "kind": "author_update",
            "parent_key": None,
            "depth": 0,
            "revision": 1,
            "created_at_utc": timestamp(92),
            "edited_at_utc": None,
            "attachments": [],
            "viewer_saved": False,
        },
        {
            "key": "66666666-6666-4666-8666-000000000002",
            "author": author(),
            "body": "The decision owner and the risk owner need to be visible at the same time.",
            "kind": "reply",
            "parent_key": "66666666-6666-4666-8666-000000000001",
            "depth": 1,
            "revision": 1,
            "created_at_utc": timestamp(68),
            "edited_at_utc": None,
            "attachments": [],
            "viewer_saved": False,
        },
        {
            "key": FOCUSED_CONTRIBUTION_KEY,
            "author": author(),
            "body": "That made the handoff clearer: people could see the next irreversible decision without reading every source note.",
            "kind": "reply",
            "parent_key": "66666666-6666-4666-8666-000000000002",
            "depth": 2,
            "revision": 1,
            "created_at_utc": timestamp(44),
            "edited_at_utc": None,
            "attachments": [],
            "viewer_saved": False,
        },
        {
            "key": "66666666-6666-4666-8666-000000000004",
            "author": author(),
            "body": "I added a small working sheet so the next review has the same source order.",
            "kind": "author_update",
            "parent_key": None,
            "depth": 0,
            "revision": 1,
            "created_at_utc": timestamp(31),
            "edited_at_utc": None,
            "attachments": [
                {
                    "key": "77777777-7777-4777-8777-000000000001",
                    "display_name": "vendor-handoff-working-sheet.xlsx",
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "byte_length": 84_210,
                    "preview_url": None,
                    "download_url": "/the-slate/local-secondary-preview-file",
                }
            ],
            "viewer_saved": False,
        },
    ]


def fixture_post() -> dict:
    return {
        "key": POST_KEY,
        "author": author(),
        "body": (
            "I turned a loose vendor handoff into a one-page decision guide today.\n\n"
            "The useful part was not the template—it was making ownership, evidence, "
            "and the next decision visible in one place."
        ),
        "conversation_label": "A one-page vendor handoff decision guide",
        "intent": "small_win",
        "response_posture": "questions_welcome",
        "audience": "Public",
        "published_at_utc": timestamp(120),
        "edited_at_utc": None,
        "revision": 1,
        "contribution_count": len(fixture_contributions),
        "attachments": [
            {
                "key": "77777777-7777-4777-8777-000000000002",
                "display_name": "An illustrative team reviewing a corkboard workflow",
                "content_type": "image/png",
                "byte_length": 2_320_474,
                "width": 1672,
                "height": 941,
                "preview_url": "/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
                "download_url": "/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
            }
        ],
        "permalink": f"/the-slate/posts/{POST_KEY}",
        "viewer": {"saved": False, "response": fixture_response},
        "preview_contributions": fixture_contributions[:4],
        "contributions": fixture_contributions,
        "next_shelf_cursor": None,
        "next_contribution_cursor": None,
    }


def rendered_preview(post_key: str | None = None, contribution_key: str | None = None) -> Response:
    html = render_template(
        "community_feed.html",
        community_owner=True,
        community_signed_in=True,
        community_display_name="Pete Carter",
        community_draft_namespace="local-secondary-conversation-preview",
        community_post_key=post_key,
        community_contribution_key=contribution_key,
        community_preview=True,
    )
    return Response(html, mimetype="text/html")


def selected_payload(contribution_key: str):
    by_key = {item["key"]: item for item in fixture_contributions}
    contribution = by_key.get(contribution_key)
    if not contribution:
        return None
    ancestors = []
    parent_key = contribution.get("parent_key")
    while parent_key and parent_key in by_key:
        parent = by_key[parent_key]
        ancestors.insert(0, parent)
        parent_key = parent.get("parent_key")
    return {"success": True, "post": fixture_post(), "contribution": contribution, "ancestors": ancestors}


app.config.update(TESTING=True)


@app.before_request
def local_secondary_state_preview():
    global fixture_response

    if request.path.startswith("/static/"):
        return None
    if request.path == "/the-slate" and request.method == "GET":
        return rendered_preview()
    if request.path == f"/the-slate/posts/{POST_KEY}" and request.method == "GET":
        return rendered_preview(POST_KEY)
    if request.path.startswith(f"/the-slate/posts/{POST_KEY}/contributions/") and request.method == "GET":
        contribution_key = request.path.rsplit("/", 1)[-1]
        if selected_payload(contribution_key):
            return rendered_preview(POST_KEY, contribution_key)
        return Response("This local fixture does not include that reply.", status=404, mimetype="text/plain")
    if request.path == "/api/v1/community/feed" and request.method == "GET":
        return jsonify(success=True, items=[fixture_post()], next_cursor=None, caught_up=True, window_limit=1)
    if request.path == f"/api/v1/community/posts/{POST_KEY}" and request.method == "GET":
        return jsonify(success=True, post=fixture_post())
    if request.path.startswith(f"/api/v1/community/posts/{POST_KEY}/contributions/") and request.method == "GET":
        contribution_key = request.path.rsplit("/", 1)[-1]
        payload = selected_payload(contribution_key)
        if payload:
            return jsonify(payload)
        return jsonify(success=False, message="That local fixture reply is unavailable.", retryable=False), 404

    response_path = f"/api/v1/community/posts/{POST_KEY}/response"
    if request.path == response_path and request.method == "PUT":
        intention = (request.get_json(silent=True) or {}).get("intention")
        if intention not in RESPONSE_INTENTIONS:
            return jsonify(success=False, message="Choose an available response.", retryable=False), 400
        fixture_response = intention
        return jsonify(success=True, intention=fixture_response)
    if request.path == response_path and request.method == "DELETE":
        fixture_response = None
        return jsonify(success=True, intention=None)

    contribution_path = f"/api/v1/community/posts/{POST_KEY}/contributions"
    if request.path == contribution_path and request.method == "POST":
        payload = request.get_json(silent=True) or {}
        body = payload.get("body")
        if not isinstance(body, str) or not body.strip() or len(body) > 2_000:
            return jsonify(success=False, message="Write a reply before sending.", retryable=False), 400
        parent_key = payload.get("parent_key")
        by_key = {item["key"]: item for item in fixture_contributions}
        if parent_key is not None and parent_key not in by_key:
            return jsonify(success=False, message="That reply target is unavailable.", retryable=False), 422
        if parent_key is not None and int(by_key[parent_key]["depth"]) >= 8:
            return jsonify(success=False, message="Maximum reply depth reached.", retryable=False), 422
        if payload.get("attachment_keys") not in ([], None):
            return jsonify(success=False, message="File uploads are intentionally not represented in this local fixture.", retryable=False), 409
        fixture_contributions.append(
            {
                "key": f"88888888-8888-4888-8888-{len(fixture_contributions) + 1:012d}",
                "author": author(),
                "body": body.strip(),
                "kind": "reply" if parent_key else "author_update",
                "parent_key": parent_key,
                "depth": int(by_key[parent_key]["depth"]) + 1 if parent_key else 0,
                "revision": 1,
                "created_at_utc": timestamp(0),
                "edited_at_utc": None,
                "attachments": [],
                "viewer_saved": False,
            }
        )
        return jsonify(success=True, result={"outcome": "local_fixture_only"}), 201

    if request.path == "/api/v1/community/posts" and request.method == "POST":
        return jsonify(success=False, message="Public publishing is intentionally disabled in this local secondary-state fixture.", retryable=False), 409
    if request.path == "/api/v1/community/attachments" and request.method == "POST":
        return jsonify(success=False, message="File upload is intentionally not represented in this local secondary-state fixture.", retryable=False), 409
    if request.path.startswith("/api/v1/community/"):
        return jsonify(success=False, message="Only local conversation, response, and typed-reply states are available in this secondary fixture.", retryable=False), 409
    return Response("This local review serves only the Community secondary conversation states.", status=404, mimetype="text/plain")


fixture_contributions = initial_contributions()


if __name__ == "__main__":
    port = int(os.environ.get("PEERSLATE_SECONDARY_STATE_PREVIEW_PORT", "5056"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
