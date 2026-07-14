"""People & Interests living-board feed — fixture-backed service (PS-FEAT-002).

This module is the ONE seam between the feed UI/API and its storage. Today it
serves approved fixture posts from static/data/people_interests_feed.json plus
an in-process overlay for posts, comments, reactions, and saves created during
this server's lifetime. When the PS-PLAT-008 migration is approved and applied,
each public function here swaps to its stored procedure without the API or the
page changing shape.

Fixture convention: PeerSlate is pre-launch, so every non-Pete author is a
representative sample member (same convention as The Slate hub). Fixture posts
carry age offsets instead of absolute timestamps so the demo board always
reads fresh; the offsets are resolved to real datetimes ONCE at load so cursor
pagination stays stable for the life of the process.

Known limitation (documented in PS-FEAT-002): the in-process overlay is
per-worker and resets on restart. It exists to demonstrate the full loop
honestly, not to imply durable multi-user storage.
"""

import base64
import binascii
import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "data", "people_interests_feed.json",
)

# One shared reaction vocabulary — positive only, defined exactly once.
# The template embeds this for the browser; the API validates against it.
REACTION_TYPES = (
    {"key": "applaud", "label": "Applaud", "emoji": "\U0001F44F"},
    {"key": "celebrate", "label": "Celebrate", "emoji": "\U0001F389"},
    {"key": "inspired", "label": "Inspired", "emoji": "\U0001F4A1"},
    {"key": "rooting", "label": "Rooting for you", "emoji": "❤️"},
)
# Context-specific reaction: goal posts can also collect "I'm in".
GOAL_REACTION = {"key": "im_in", "label": "I'm in", "emoji": "✋"}

REACTION_KEYS = frozenset(
    [reaction["key"] for reaction in REACTION_TYPES] + [GOAL_REACTION["key"]]
)

CONTENT_TYPES = frozenset(
    {"note", "win", "question", "goal", "project", "idea", "photo", "quote", "moment"}
)

POST_BODY_MAX = 200
COMMENT_BODY_MAX = 300
PAGE_LIMIT_DEFAULT = 16
PAGE_LIMIT_MAX = 32

# Layout variants a browser may request for its own new posts. Sizes are
# assigned deterministically server-side from content; this set only bounds
# the vocabulary so nothing unexpected reaches the CSS.
LAYOUT_VARIANTS = frozenset(
    {"small", "standard", "tall", "wide", "photo", "featured"}
)

_CURSOR_PATTERN = re.compile(r"^[0-9T:.\-]+\|[A-Za-z0-9\-_]+$")


class FeedValidationError(ValueError):
    """Raised when browser-provided feed input is invalid."""


class FeedNotFoundError(LookupError):
    """Raised when a post id does not exist in the feed."""


def _load_fixture():
    with open(_DATA_PATH, "r", encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def _resolve_created_at(post, loaded_at):
    minutes = post.get("age_minutes")
    if minutes is None:
        minutes = 60
    return loaded_at - timedelta(minutes=int(minutes))


class PeopleInterestsFeed:
    """Fixture feed + in-process overlay, guarded for concurrent requests."""

    def __init__(self):
        self._lock = threading.RLock()
        self._loaded_at = datetime.now()
        fixture = _load_fixture()
        self.authors = fixture["authors"]
        self.left_rail = fixture.get("left_rail", {})
        self.right_rail = fixture.get("right_rail", {})
        self._posts = {}
        self._order = []  # post ids, newest first
        for raw in fixture["posts"]:
            post = dict(raw)
            post["created_at"] = _resolve_created_at(post, self._loaded_at)
            post["comments"] = [dict(c) for c in post.get("comments", [])]
            for comment in post["comments"]:
                comment["created_at"] = _resolve_created_at(comment, self._loaded_at)
            post["reactions"] = dict(post.get("reactions", {}))
            post["is_fixture"] = True
            self._posts[post["id"]] = post
        self._order = sorted(
            self._posts,
            key=lambda pid: (self._posts[pid]["created_at"], pid),
            reverse=True,
        )
        # user_key -> {post_id -> set(reaction keys)} / set(saved post ids)
        self._user_reactions = {}
        self._user_saves = {}

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def _relative_label(self, moment, now):
        seconds = max(0, (now - moment).total_seconds())
        minutes = int(seconds // 60)
        if minutes < 60:
            return f"{max(1, minutes)}m"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h"
        days = hours // 24
        if days < 7:
            return f"{days}d"
        weeks = days // 7
        if weeks < 5:
            return f"{weeks}w"
        return f"{moment.strftime('%b')} {moment.day}"

    def _author_payload(self, author_key):
        author = self.authors.get(author_key, {})
        return {
            "key": author_key,
            "name": author.get("name", "PeerSlate member"),
            "initials": author.get("initials", ""),
            "tint": author.get("tint", "blue"),
            "avatar": author.get("avatar"),
            "title": author.get("title", ""),
            "is_sample": author.get("is_sample", True),
        }

    def _post_summary(self, post, now, user_key=None):
        body = post.get("body") or ""
        summary = {
            "id": post["id"],
            "author": self._author_payload(post["author"]),
            "content_type": post["content_type"],
            "time_label": self._relative_label(post["created_at"], now),
            "created_at": post["created_at"].isoformat(),
            "body": body,
            "title": post.get("title"),
            "list_items": post.get("list_items"),
            "quote_attribution": post.get("quote_attribution"),
            "photo": post.get("photo"),
            "paper": post.get("paper", "sticky"),
            "paper_color": post.get("paper_color", "yellow"),
            "layout": post.get("layout", "standard"),
            "rotation": post.get("rotation", 0),
            "offset_x": post.get("offset_x", 0),
            "offset_y": post.get("offset_y", 0),
            "flourish": post.get("flourish"),
            "attachment": post.get("attachment", "pin"),
            "pin_color": post.get("pin_color", "indigo"),
            "handwriting": post.get("handwriting", "cursive"),
            "reactions": dict(post.get("reactions", {})),
            "comment_count": len(post.get("comments", [])),
            "joining_count": post.get("joining_count", 0),
            "is_fixture": post.get("is_fixture", False),
        }
        if user_key:
            summary["viewer_reactions"] = sorted(
                self._user_reactions.get(user_key, {}).get(post["id"], set())
            )
            summary["viewer_saved"] = post["id"] in self._user_saves.get(user_key, set())
        return summary

    def get_page(self, cursor=None, limit=PAGE_LIMIT_DEFAULT, user_key=None):
        """Keyset-paginated slice of the board, newest first."""
        limit = max(1, min(int(limit), PAGE_LIMIT_MAX))
        with self._lock:
            order = self._order
            start = 0
            if cursor:
                if not _CURSOR_PATTERN.match(cursor):
                    raise FeedValidationError("cursor has an unsupported value.")
                cursor_time, cursor_id = cursor.split("|", 1)
                for index, post_id in enumerate(order):
                    post = self._posts[post_id]
                    if (
                        post["created_at"].isoformat() == cursor_time
                        and post_id == cursor_id
                    ):
                        start = index + 1
                        break
                else:
                    # Cursor no longer present (e.g. process restart):
                    # start from the top rather than erroring the scroll.
                    start = 0
            now = datetime.now()
            page_ids = order[start:start + limit]
            items = [
                self._post_summary(self._posts[pid], now, user_key)
                for pid in page_ids
            ]
            next_cursor = None
            if start + limit < len(order) and page_ids:
                last = self._posts[page_ids[-1]]
                next_cursor = f"{last['created_at'].isoformat()}|{last['id']}"
            return {"items": items, "next_cursor": next_cursor}

    def get_post_detail(self, post_id, user_key=None):
        with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                raise FeedNotFoundError("Post not found.")
            now = datetime.now()
            detail = self._post_summary(post, now, user_key)
            detail["comments"] = [
                {
                    "id": comment["id"],
                    "author": self._author_payload(comment["author"]),
                    "body": comment["body"],
                    "time_label": self._relative_label(comment["created_at"], now),
                    "supports": comment.get("supports", 0),
                }
                for comment in sorted(
                    post["comments"], key=lambda c: c["created_at"]
                )
            ]
            return detail

    # ------------------------------------------------------------------
    # Writes (in-process overlay; stored-procedure seam for PS-PLAT-008)
    # ------------------------------------------------------------------

    def _assign_layout(self, content_type, body):
        """Deterministic size from content — never random at render time."""
        if content_type == "photo":
            return "photo"
        if content_type in {"goal", "project"}:
            return "tall" if len(body) > 90 else "standard"
        if len(body) <= 60:
            return "small"
        if len(body) > 140:
            return "tall"
        return "standard"

    def _stable_style(self, seed_text, content_type):
        """Deterministic paper/rotation from the post id so the same item
        never jumps to a new angle on a refresh."""
        seed = sum(seed_text.encode("utf-8"))
        colors = ("yellow", "green", "blue", "pink", "cream", "peach", "aqua")
        rotations = (-3.2, -2.1, -1.2, 0, 1.4, 2.3, 3.1)
        attachments = ("pin", "tape", "pin", "clip", "pin", "tape")
        pins = ("indigo", "red", "teal", "amber", "violet")
        offsets_x = (-6, 4, 0, 6, -4, 5)
        offsets_y = (6, -8, 10, -5, 8, -6)
        papers_by_type = {
            "note": "sticky", "win": "sticky", "goal": "sticky",
            "idea": "torn", "question": "torn", "moment": "torn",
            "project": "lined", "quote": "quote", "photo": "polaroid",
        }
        return {
            "paper": papers_by_type.get(content_type, "sticky"),
            "paper_color": colors[seed % len(colors)],
            "rotation": rotations[seed % len(rotations)],
            "attachment": attachments[seed % len(attachments)],
            "pin_color": pins[seed % len(pins)],
            "offset_x": offsets_x[seed % len(offsets_x)],
            "offset_y": offsets_y[seed % len(offsets_y)],
        }

    def create_post(self, user_key, author_payload, body, content_type):
        body = (body or "").strip()
        if not body:
            raise FeedValidationError("Write something before posting.")
        if len(body) > POST_BODY_MAX:
            raise FeedValidationError(
                f"Posts are limited to {POST_BODY_MAX} characters."
            )
        if content_type not in CONTENT_TYPES:
            raise FeedValidationError("content_type has an unsupported value.")
        if content_type == "photo":
            raise FeedValidationError(
                "Photo uploads arrive with PeerSlate accounts."
            )
        with self._lock:
            post_id = f"pi-{uuid.uuid4().hex[:12]}"
            author_key = f"member-{user_key}"
            if author_key not in self.authors:
                self.authors[author_key] = {
                    "name": author_payload.get("display_name") or "You",
                    "initials": "You",
                    "tint": "you",
                    "is_sample": False,
                }
            style = self._stable_style(post_id, content_type)
            post = {
                "id": post_id,
                "author": author_key,
                "created_at": datetime.now(),
                "content_type": content_type,
                "body": body,
                "layout": self._assign_layout(content_type, body),
                "handwriting": "cursive" if len(body) <= 120 else "print",
                "comments": [],
                "reactions": {},
                "is_fixture": False,
                "owner_user_key": user_key,
                "visibility": "private",  # new board drafts default private
            }
            post.update(style)
            self._posts[post_id] = post
            self._order.insert(0, post_id)
            return self._post_summary(post, datetime.now(), user_key)

    def add_comment(self, user_key, author_payload, post_id, body):
        body = (body or "").strip()
        if not body:
            raise FeedValidationError("Write a comment before sending.")
        if len(body) > COMMENT_BODY_MAX:
            raise FeedValidationError(
                f"Comments are limited to {COMMENT_BODY_MAX} characters."
            )
        with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                raise FeedNotFoundError("Post not found.")
            author_key = f"member-{user_key}"
            if author_key not in self.authors:
                self.authors[author_key] = {
                    "name": author_payload.get("display_name") or "You",
                    "initials": "You",
                    "tint": "you",
                    "is_sample": False,
                }
            comment = {
                "id": f"c-{uuid.uuid4().hex[:10]}",
                "author": author_key,
                "body": body,
                "created_at": datetime.now(),
                "supports": 0,
            }
            post["comments"].append(comment)
            now = datetime.now()
            return {
                "id": comment["id"],
                "author": self._author_payload(author_key),
                "body": body,
                "time_label": self._relative_label(comment["created_at"], now),
                "supports": 0,
                "comment_count": len(post["comments"]),
            }

    def add_reaction(self, user_key, post_id, reaction_type):
        if reaction_type not in REACTION_KEYS:
            raise FeedValidationError("reaction_type has an unsupported value.")
        with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                raise FeedNotFoundError("Post not found.")
            mine = self._user_reactions.setdefault(user_key, {}).setdefault(
                post_id, set()
            )
            # Idempotent: reacting twice never double-counts.
            if reaction_type not in mine:
                mine.add(reaction_type)
                post["reactions"][reaction_type] = (
                    post["reactions"].get(reaction_type, 0) + 1
                )
            return {
                "reactions": dict(post["reactions"]),
                "viewer_reactions": sorted(mine),
            }

    def remove_reaction(self, user_key, post_id, reaction_type):
        if reaction_type not in REACTION_KEYS:
            raise FeedValidationError("reaction_type has an unsupported value.")
        with self._lock:
            post = self._posts.get(post_id)
            if post is None:
                raise FeedNotFoundError("Post not found.")
            mine = self._user_reactions.setdefault(user_key, {}).setdefault(
                post_id, set()
            )
            if reaction_type in mine:
                mine.discard(reaction_type)
                current = post["reactions"].get(reaction_type, 0)
                if current <= 1:
                    post["reactions"].pop(reaction_type, None)
                else:
                    post["reactions"][reaction_type] = current - 1
            return {
                "reactions": dict(post["reactions"]),
                "viewer_reactions": sorted(mine),
            }

    def toggle_save(self, user_key, post_id):
        with self._lock:
            if post_id not in self._posts:
                raise FeedNotFoundError("Post not found.")
            saved = self._user_saves.setdefault(user_key, set())
            if post_id in saved:
                saved.discard(post_id)
                return {"saved": False}
            saved.add(post_id)
            return {"saved": True}


people_interests_feed = PeopleInterestsFeed()
