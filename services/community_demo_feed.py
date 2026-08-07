"""Truthfully labelled, read-only projection of the approved Community demo.

This module owns presentation-only example content. It never reads or writes
Community persistence and is returned only after a successful empty real Feed
read. Canonical Community content remains solely in Azure SQL.
"""

from __future__ import annotations

from copy import deepcopy

from services.community_contracts import (
    CommunityNotFoundError,
    CommunityValidationError,
    opaque_key,
    safe_search_query,
)


DEMO_POST_KEY = "11111111-1111-4111-8111-111111111111"
DEMO_ATTACHMENT_KEY = "22222222-2222-4222-8222-222222222222"
DEMO_PUBLISHED_AT = "2026-08-01T15:00:00Z"
DEMO_AUTHOR = {
    "display_name": "Pete Carter",
    "avatar_url": "/static/images/story/pete-headshot-m.jpg",
}


_UPDATES = (
    ("I pulled the owners and evidence into one scan-friendly first page.", ()),
    (
        "Here is the working decision guide for anyone who wants the structure.",
        (("vendor-handoff-decision-guide.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 84_210, None),),
    ),
    ("The next-decision column was the piece people used most in the review.", ()),
    ("I shortened the evidence notes so the guide works during a live handoff.", ()),
    ("One open question: should the risk owner sit beside the decision owner?", ()),
    (
        "This is the board state that helped me see the missing handoff step.",
        (("workshop-board.png", "image/png", 2_320_474, "/static/images/feed/feed-workflow-corkboard-2026-07-21.png"),),
    ),
    ("I added a final check for who can make the next irreversible decision.", ()),
    ("The guide now separates source evidence from the recommendation.", ()),
    (
        "I bundled the worksheet and a short read-me after the second pass.",
        (
            ("handoff-working-sheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 93_811, None),
            ("handoff-read-me.pdf", "application/pdf", 118_402, None),
        ),
    ),
    ("The last review removed two fields that were not helping anyone decide.", ()),
    ("I kept the original evidence links intact so the summary is auditable.", ()),
    ("The one-page version is ready for the next real vendor handoff.", ()),
)


def _demo_attachment(index, file_index, value):
    name, content_type, byte_length, preview_url = value
    return {
        "key": f"44444444-4444-4444-8444-{index:06d}{file_index:06d}",
        "display_name": name,
        "content_type": content_type,
        "byte_length": byte_length,
        "width": 1672 if preview_url else None,
        "height": 941 if preview_url else None,
        "preview_url": preview_url,
        "download_url": preview_url,
        "demo": True,
    }


def demo_contributions():
    items = []
    for index, (body, attachments) in enumerate(_UPDATES, start=1):
        minute = 5 + index * 8
        items.append(
            {
                "key": f"33333333-3333-4333-8333-{index:012d}",
                "post_key": DEMO_POST_KEY,
                "parent_key": None,
                "kind": "author_update",
                "author": deepcopy(DEMO_AUTHOR),
                "body": body,
                "created_at_utc": f"2026-08-01T{15 + minute // 60:02d}:{minute % 60:02d}:00Z",
                "edited_at_utc": None,
                "revision": 1,
                "depth": 0,
                "attachments": [
                    _demo_attachment(index, file_index, value)
                    for file_index, value in enumerate(attachments, start=1)
                ],
                "state": "active",
                "viewer_saved": False,
                "child_reply_count": 0,
                "demo": True,
            }
        )
    return items


def demo_post(*, include_contributions=False):
    contributions = demo_contributions()
    post = {
        "key": DEMO_POST_KEY,
        "author": deepcopy(DEMO_AUTHOR),
        "body": (
            "I turned a loose vendor handoff into a one-page decision guide today.\n\n"
            "The useful part was not the template—it was making ownership, "
            "evidence, and the next decision visible in one place."
        ),
        "conversation_label": "A one-page vendor handoff decision guide",
        "intent": "small_win",
        "response_posture": "questions_welcome",
        "audience": "Public demo",
        "published_at_utc": DEMO_PUBLISHED_AT,
        "edited_at_utc": None,
        "revision": 1,
        "contribution_count": len(contributions),
        "attachments": [
            {
                "key": DEMO_ATTACHMENT_KEY,
                "display_name": "An illustrative team reviewing a corkboard workflow",
                "content_type": "image/png",
                "byte_length": 2_320_474,
                "width": 1672,
                "height": 941,
                "preview_url": "/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
                "download_url": "/static/images/feed/feed-workflow-corkboard-2026-07-21.png",
                "demo": True,
            }
        ],
        "permalink": f"/the-slate/posts/{DEMO_POST_KEY}",
        "viewer": {"saved": False, "response": None},
        "preview_contributions": contributions,
        "next_shelf_cursor": None,
        "demo": True,
        "demo_label": "Illustrative demo",
    }
    if include_contributions:
        post["contributions"] = contributions
        post["next_contribution_cursor"] = None
    return post


def demo_feed_page():
    return {
        "items": [demo_post()],
        "next_cursor": None,
        "caught_up": True,
        "window_limit": 1,
        "demo_mode": True,
    }


def demo_post_detail(post_key):
    if opaque_key(post_key, field="post key") != DEMO_POST_KEY:
        raise CommunityNotFoundError("Post not found.")
    return demo_post(include_contributions=True)


def demo_shelf_page(post_key, token=None):
    if token:
        raise CommunityValidationError("The demo has no additional Replies & updates page.")
    post = demo_post_detail(post_key)
    return {
        "items": post["preview_contributions"],
        "next_cursor": None,
        "caught_up": True,
        "demo_mode": True,
    }


def demo_selected_contribution(post_key, contribution_key):
    post = demo_post_detail(post_key)
    key = opaque_key(contribution_key, field="contribution key")
    selected = next((item for item in post["contributions"] if item["key"] == key), None)
    if not selected:
        raise CommunityNotFoundError("Contribution not found.")
    return {"contribution": selected, "ancestors": [], "demo_mode": True}


def demo_search(query):
    clean = safe_search_query(query).casefold()
    post = demo_post()
    searchable = " ".join(
        [post["body"], post["conversation_label"]]
        + [item["body"] for item in post["preview_contributions"]]
    ).casefold()
    return [post] if clean in searchable else []
