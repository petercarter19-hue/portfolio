"""Signed, content-free finite Feed cursors for public Community reads."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

from services.community_contracts import (
    FEED_WINDOW_MAX,
    CommunityValidationError,
    opaque_key,
)


CURSOR_MAX_AGE_SECONDS = 30 * 60


def _utc_now():
    """Return the full-precision UTC watermark used by new read windows."""
    return datetime.now(timezone.utc)


def _serializer():
    key = current_app.config.get("PEERSLATE_COMMUNITY_SIGNING_KEY")
    if not key:
        raise RuntimeError("Community cursor signing is unavailable.")
    return URLSafeTimedSerializer(key, salt="peerslate-community-feed-v1")


def _conversation_serializer():
    key = current_app.config.get("PEERSLATE_COMMUNITY_SIGNING_KEY")
    if not key:
        raise RuntimeError("Community cursor signing is unavailable.")
    return URLSafeTimedSerializer(key, salt="peerslate-community-conversation-v1")


def _shelf_serializer():
    key = current_app.config.get("PEERSLATE_COMMUNITY_SIGNING_KEY")
    if not key:
        raise RuntimeError("Community cursor signing is unavailable.")
    return URLSafeTimedSerializer(key, salt="peerslate-community-shelf-v1")


def _utc_datetime(value, *, optional=False):
    if value in (None, "") and optional:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise CommunityValidationError(
                "The Feed window is invalid or expired."
            ) from error
    else:
        raise CommunityValidationError("The Feed window is invalid or expired.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_token_value(value):
    parsed = _utc_datetime(value)
    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def new_window_token():
    now = _utc_now()
    return _serializer().dumps(
        {
            "v": 1,
            "as_of": _utc_token_value(now),
            "after_time": None,
            "after_key": None,
            "remaining": FEED_WINDOW_MAX,
        }
    )


def decode_window_token(token):
    if not token or not isinstance(token, str) or len(token) > 2048:
        raise CommunityValidationError("The Feed window is invalid or expired.")
    try:
        payload = _serializer().loads(token, max_age=CURSOR_MAX_AGE_SECONDS)
    except BadData as error:
        raise CommunityValidationError(
            "The Feed window is invalid or expired."
        ) from error
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise CommunityValidationError("The Feed window is invalid or expired.")
    try:
        remaining = int(payload.get("remaining"))
    except (TypeError, ValueError) as error:
        raise CommunityValidationError(
            "The Feed window is invalid or expired."
        ) from error
    if not 0 <= remaining <= FEED_WINDOW_MAX:
        raise CommunityValidationError("The Feed window is invalid or expired.")
    after_key = payload.get("after_key")
    try:
        after_key = str(UUID(str(after_key))) if after_key else None
    except (TypeError, ValueError, AttributeError) as error:
        raise CommunityValidationError(
            "The Feed window is invalid or expired."
        ) from error
    after_time = _utc_datetime(payload.get("after_time"), optional=True)
    if (after_time is None) != (after_key is None):
        raise CommunityValidationError("The Feed window is invalid or expired.")
    return {
        "as_of": _utc_datetime(payload.get("as_of")),
        "after_time": after_time,
        "after_key": after_key,
        "remaining": remaining,
    }


def next_window_token(window, last_item, returned_count):
    remaining = max(0, int(window["remaining"]) - int(returned_count))
    if remaining == 0 or not last_item:
        return None
    return _serializer().dumps(
        {
            "v": 1,
            "as_of": _utc_token_value(window["as_of"]),
            "after_time": _utc_token_value(last_item["published_at_utc"]),
            "after_key": last_item.get("post_key") or last_item.get("key"),
            "remaining": remaining,
        }
    )


def decode_contribution_token(token, post_key):
    """Decode a conversation cursor cryptographically bound to one post.

    Conversation pages are bounded per request, not by an arbitrary total-row
    ceiling. The cursor therefore carries only the last selected keyset
    boundary; it cannot be replayed against another post or projection scope.
    """
    post_key = opaque_key(post_key, field="post key")
    if token in (None, ""):
        return {
            "post_key": post_key,
            "as_of": _utc_datetime(_utc_now()),
            "before_time": None,
            "before_key": None,
        }
    if not isinstance(token, str) or len(token) > 2048:
        raise CommunityValidationError(
            "The conversation window is invalid or expired."
        )
    try:
        payload = _conversation_serializer().loads(
            token, max_age=CURSOR_MAX_AGE_SECONDS
        )
    except BadData as error:
        raise CommunityValidationError(
            "The conversation window is invalid or expired."
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("v") != 2
        or payload.get("scope") != "conversation"
    ):
        raise CommunityValidationError(
            "The conversation window is invalid or expired."
        )
    try:
        token_post_key = opaque_key(payload.get("post_key"), field="post key")
        before_key = (
            opaque_key(payload.get("before_key"), field="contribution key")
            if payload.get("before_key")
            else None
        )
        before_time = _utc_datetime(payload.get("before_time"), optional=True)
        token_as_of = _utc_datetime(payload.get("as_of"))
    except (TypeError, ValueError, CommunityValidationError) as error:
        raise CommunityValidationError(
            "The conversation window is invalid or expired."
        ) from error
    if token_post_key != post_key:
        raise CommunityValidationError(
            "The conversation window is invalid or expired."
        )
    if (before_time is None) != (before_key is None):
        raise CommunityValidationError(
            "The conversation window is invalid or expired."
        )
    return {
        "post_key": post_key,
        "as_of": token_as_of,
        "before_time": before_time,
        "before_key": before_key,
    }


def next_contribution_token(window, last_item):
    if not last_item:
        return None
    return _conversation_serializer().dumps(
        {
            "v": 2,
            "scope": "conversation",
            "post_key": window["post_key"],
            "as_of": _utc_token_value(window["as_of"]),
            "before_time": _utc_token_value(last_item["created_at_utc"]),
            "before_key": last_item.get("contribution_key") or last_item.get("key"),
        }
    )


def decode_shelf_token(token, post_key, *, as_of=None):
    """Decode one stable, post-bound Replies & updates shelf window."""
    post_key = opaque_key(post_key, field="post key")
    if token in (None, ""):
        return {
            "post_key": post_key,
            "as_of": _utc_datetime(as_of or _utc_now()),
            "before_time": None,
            "before_key": None,
        }
    if not isinstance(token, str) or len(token) > 2048:
        raise CommunityValidationError("The Replies & updates window is invalid or expired.")
    try:
        payload = _shelf_serializer().loads(token, max_age=CURSOR_MAX_AGE_SECONDS)
    except BadData as error:
        raise CommunityValidationError(
            "The Replies & updates window is invalid or expired."
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("v") != 1
        or payload.get("scope") != "shelf"
    ):
        raise CommunityValidationError(
            "The Replies & updates window is invalid or expired."
        )
    try:
        token_post_key = opaque_key(payload.get("post_key"), field="post key")
        before_key = (
            opaque_key(payload.get("before_key"), field="contribution key")
            if payload.get("before_key")
            else None
        )
        before_time = _utc_datetime(payload.get("before_time"), optional=True)
        token_as_of = _utc_datetime(payload.get("as_of"))
    except (TypeError, ValueError, CommunityValidationError) as error:
        raise CommunityValidationError(
            "The Replies & updates window is invalid or expired."
        ) from error
    if token_post_key != post_key or (before_time is None) != (before_key is None):
        raise CommunityValidationError(
            "The Replies & updates window is invalid or expired."
        )
    return {
        "post_key": post_key,
        "as_of": token_as_of,
        "before_time": before_time,
        "before_key": before_key,
    }


def next_shelf_token(window, last_item):
    if not last_item:
        return None
    return _shelf_serializer().dumps(
        {
            "v": 1,
            "scope": "shelf",
            "post_key": window["post_key"],
            "as_of": _utc_token_value(window["as_of"]),
            "before_time": _utc_token_value(last_item["created_at_utc"]),
            "before_key": last_item.get("contribution_key") or last_item.get("key"),
        }
    )
