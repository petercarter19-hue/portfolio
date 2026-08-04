"""Serve one truthful, fixture-only Community primary Feed for visual review.

This harness never reads or writes Community persistence. It exists only to
render the approved primary-page checkpoint against the real Flask template,
CSS, JavaScript, and static assets.
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


POST_KEY = "11111111-1111-4111-8111-111111111111"
ATTACHMENT_KEY = "22222222-2222-4222-8222-222222222222"
RESPONSE_INTENTIONS = {"celebrate", "support", "i_relate", "ask", "offer_help"}
fixture_response = None
fixture_comment_count = 12


def fixture_contributions(published_at):
    updates = [
        ("I pulled the owners and evidence into one scan-friendly first page.", []),
        (
            "Here is the working decision guide for anyone who wants the structure.",
            [
                {
                    "key": "44444444-4444-4444-8444-000000000001",
                    "display_name": "vendor-handoff-decision-guide.xlsx",
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "byte_length": 84_210,
                    "preview_url": None,
                    "download_url": "/the-slate/local-preview-file",
                }
            ],
        ),
        ("The next-decision column was the piece people used most in the review.", []),
        ("I shortened the evidence notes so the guide works during a live handoff.", []),
        ("One open question: should the risk owner sit beside the decision owner?", []),
        (
            "This is the board state that helped me see the missing handoff step.",
            [
                {
                    "key": "44444444-4444-4444-8444-000000000002",
                    "display_name": "workshop-board.png",
                    "content_type": "image/png",
                    "byte_length": 2_320_474,
                    "preview_url": "/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
                    "download_url": "/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
                }
            ],
        ),
        ("I added a final check for who can make the next irreversible decision.", []),
        ("The guide now separates source evidence from the recommendation.", []),
        (
            "I bundled the worksheet and a short read-me after the second pass.",
            [
                {
                    "key": "44444444-4444-4444-8444-000000000003",
                    "display_name": "handoff-working-sheet.xlsx",
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "byte_length": 93_811,
                    "preview_url": None,
                    "download_url": "/the-slate/local-preview-file",
                },
                {
                    "key": "44444444-4444-4444-8444-000000000004",
                    "display_name": "handoff-read-me.pdf",
                    "content_type": "application/pdf",
                    "byte_length": 118_402,
                    "preview_url": None,
                    "download_url": "/the-slate/local-preview-file",
                },
            ],
        ),
        ("The last review removed two fields that were not helping anyone decide.", []),
        ("I kept the original evidence links intact so the summary is auditable.", []),
        ("The one-page version is ready for the next real vendor handoff.", []),
    ]
    contributions = []
    for index, (body, attachments) in enumerate(updates, start=1):
        created_at = published_at + timedelta(minutes=5 + index * 8)
        contributions.append(
            {
                "key": f"33333333-3333-4333-8333-{index:012d}",
                "author": {
                    "display_name": "Pete Carter",
                    "avatar_url": "/static/images/story/pete-headshot-m.jpg",
                },
                "body": body,
                "kind": "author_update",
                "created_at_utc": created_at.isoformat().replace("+00:00", "Z"),
                "edited_at_utc": None,
                "child_reply_count": 0,
                "attachments": attachments,
            }
        )
    return contributions


def fixture_post():
    published_at = datetime.now(timezone.utc) - timedelta(hours=2)
    return {
        "key": POST_KEY,
        "author": {
            "display_name": "Pete Carter",
            "avatar_url": "/static/images/story/pete-headshot-m.jpg",
        },
        "body": (
            "I turned a loose vendor handoff into a one-page decision guide today.\n\n"
            "The useful part was not the template—it was making ownership, "
            "evidence, and the next decision visible in one place."
        ),
        "conversation_label": "A one-page vendor handoff decision guide",
        "intent": "small_win",
        "response_posture": "questions_welcome",
        "audience": "Public",
        "published_at_utc": published_at.isoformat().replace("+00:00", "Z"),
        "edited_at_utc": None,
        "revision": 1,
        "contribution_count": fixture_comment_count,
        "attachments": [
            {
                "key": ATTACHMENT_KEY,
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
        "preview_contributions": fixture_contributions(published_at),
        "next_shelf_cursor": None,
    }


def rendered_preview():
    html = render_template(
        "community_feed.html",
        community_owner=True,
        community_signed_in=True,
        community_display_name="Pete Carter",
        community_draft_namespace="local-primary-feed-preview",
        community_post_key=None,
        community_contribution_key=None,
        community_preview=True,
    )
    return Response(html, mimetype="text/html")


# TESTING prevents the application's earlier Community-maintenance hook from
# reaching media dependencies. The request allowlist below is the primary
# isolation boundary: it serves only this page, its Feed fixture, and static
# assets, and denies every other application route before its view can run.
app.config.update(TESTING=True)


@app.before_request
def local_primary_feed_preview():
    global fixture_comment_count, fixture_response

    if request.path.startswith("/static/"):
        return None

    if request.path == "/the-slate" and request.method == "GET":
        return rendered_preview()

    if request.path == "/api/v1/community/feed" and request.method == "GET":
        return jsonify(
            success=True,
            items=[fixture_post()],
            next_cursor=None,
            caught_up=True,
            window_limit=1,
        )

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
            return jsonify(success=False, message="Write a comment before publishing.", retryable=False), 400
        if payload.get("parent_key") is not None or payload.get("attachment_keys") != []:
            return jsonify(success=False, message="This preview accepts a text-only top-level comment.", retryable=False), 400
        fixture_comment_count += 1
        return jsonify(success=True, result={"outcome": "created"}), 201

    if request.path.startswith("/api/v1/community/"):
        return (
            jsonify(
                success=False,
                message="Only the primary Feed and its in-memory response/comment actions are available in this local review fixture.",
                retryable=False,
            ),
            409,
        )

    return Response(
        "This local review serves only the closed primary Community Feed.",
        status=404,
        mimetype="text/plain",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PEERSLATE_PRIMARY_FEED_PREVIEW_PORT", "5055"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
