"""Authorized read models for the real Community public pilot."""

from __future__ import annotations

from datetime import datetime, timezone

from services.community_contracts import (
    CONTRIBUTION_PAGE_SIZE,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    CommunityNotFoundError,
    CommunityUnavailableError,
    CommunityValidationError,
    opaque_key,
    safe_search_query,
)
from services.community_cursor import (
    decode_contribution_token,
    decode_shelf_token,
    decode_window_token,
    new_window_token,
    next_contribution_token,
    next_shelf_token,
    next_window_token,
)
from services.database_service import DatabaseServiceError, database_service


def _author(row):
    return {
        "display_name": row.get("author_name") or "PeerSlate member",
        "avatar_url": row.get("author_avatar_url"),
    }


def _utc_json(value):
    """Emit SQL datetime2 values as explicit UTC rather than browser-local time."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    else:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _conversation_label(value, maximum=72):
    """Derive a stable, plain-text label without creating a second title field."""
    cleaned = " ".join(str(value or "").split())
    if not cleaned:
        return "Community conversation"
    if len(cleaned) <= maximum:
        return cleaned
    return cleaned[: maximum - 1].rstrip() + "…"


def _attachment(row):
    key = str(row["media_key"])
    return {
        "key": key,
        "display_name": row.get("display_name") or "Attachment",
        "content_type": row.get("content_type"),
        "byte_length": int(row.get("byte_length") or 0),
        "width": int(row["pixel_width"]) if row.get("pixel_width") else None,
        "height": int(row["pixel_height"]) if row.get("pixel_height") else None,
        "preview_url": (
            f"/api/v1/community/attachments/{key}/preview"
            if str(row.get("content_type") or "").startswith("image/")
            else None
        ),
        "download_url": f"/api/v1/community/attachments/{key}/download",
    }


def _group_attachments(rows, target_field):
    grouped = {}
    for row in rows or []:
        target = row.get(target_field)
        if target:
            grouped.setdefault(str(target), []).append(_attachment(row))
    return grouped


def _post(row, attachments=None):
    key = str(row["post_key"])
    post = {
        "key": key,
        "author": _author(row),
        "body": row.get("body") or "",
        "conversation_label": _conversation_label(row.get("body")),
        "intent": row.get("intent") or "post",
        "response_posture": row.get("response_posture") or "open_feedback",
        "audience": "Public",
        "published_at_utc": _utc_json(row.get("published_at_utc")),
        "edited_at_utc": _utc_json(row.get("edited_at_utc")),
        "revision": int(row.get("revision_number") or 1),
        "contribution_count": int(row.get("contribution_count") or 0),
        "attachments": list((attachments or {}).get(key, [])),
        "permalink": f"/the-slate/posts/{key}",
    }
    post["viewer"] = {
        "saved": bool(row.get("viewer_saved")),
        "response": row.get("viewer_response_intention"),
    }
    return post


def _contribution(row, attachments=None):
    key = str(row["contribution_key"])
    parent = row.get("parent_contribution_key")
    projection_state = row.get("projection_state") or "active"
    active = projection_state == "active"
    return {
        "key": key,
        "post_key": str(row["post_key"]),
        "parent_key": str(parent) if parent else None,
        "kind": row.get("contribution_kind") if active else None,
        "author": _author(row) if active else {
            "display_name": None,
            "avatar_url": None,
        },
        "body": (row.get("body") or "") if active else "",
        "created_at_utc": _utc_json(row.get("created_at_utc")),
        "edited_at_utc": _utc_json(row.get("edited_at_utc")),
        "revision": int(row.get("revision_number") or 1),
        "depth": min(8, int(row.get("depth") or 0)),
        "attachments": list((attachments or {}).get(key, [])),
        "state": projection_state,
        "viewer_saved": bool(row.get("viewer_saved")),
        "child_reply_count": int(row.get("child_reply_count") or 0),
    }


class CommunityFeedService:
    def __init__(self, database=None):
        self.database = database or database_service

    def feed_page(
        self, token=None, *, page_size=PAGE_SIZE_DEFAULT, viewer_user_key=None
    ):
        try:
            size = max(1, min(int(page_size), PAGE_SIZE_MAX))
        except (TypeError, ValueError) as error:
            raise CommunityValidationError("The page size is invalid.") from error
        if token:
            window = decode_window_token(token)
        else:
            token = new_window_token()
            window = decode_window_token(token)
        size = min(size, window["remaining"])
        if size == 0:
            return {"items": [], "next_cursor": None, "caught_up": True}
        try:
            result_sets = self.database.execute_procedure(
                "usp_ListPublicCommunityFeed",
                [
                    ("@AsOfUtc", window["as_of"]),
                    ("@AfterPublishedAtUtc", window["after_time"]),
                    ("@AfterPostKey", window["after_key"]),
                    ("@PageLimit", size),
                    ("@ViewerUserKey", viewer_user_key),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Feed unavailable.") from error
        posts = result_sets[0] if result_sets else []
        media = result_sets[1] if len(result_sets) > 1 else []
        preview_rows = result_sets[2] if len(result_sets) > 2 else []
        preview_media = result_sets[3] if len(result_sets) > 3 else []
        shelf_boundaries = result_sets[4] if len(result_sets) > 4 else []
        feed_boundaries = result_sets[5] if len(result_sets) > 5 else []
        attachments = _group_attachments(media, "post_key")
        preview_attachments = _group_attachments(
            preview_media, "contribution_key"
        )
        previews = {}
        for row in preview_rows:
            previews.setdefault(str(row["post_key"]), []).append(
                _contribution(row, preview_attachments)
            )
        shelf_boundary_by_post = {
            str(row["post_key"]): row
            for row in shelf_boundaries
            if row.get("post_key")
        }
        items = []
        for row in posts:
            post = _post(row, attachments)
            post["preview_contributions"] = previews.get(post["key"], [])
            shelf_boundary = shelf_boundary_by_post.get(post["key"], {})
            post["next_shelf_cursor"] = None
            if (
                bool(shelf_boundary.get("has_more"))
                and shelf_boundary.get("boundary_created_at_utc")
                and shelf_boundary.get("boundary_contribution_key")
            ):
                shelf_window = decode_shelf_token(
                    None, post["key"], as_of=window["as_of"]
                )
                post["next_shelf_cursor"] = next_shelf_token(
                    shelf_window,
                    {
                        "created_at_utc": shelf_boundary[
                            "boundary_created_at_utc"
                        ],
                        "contribution_key": shelf_boundary[
                            "boundary_contribution_key"
                        ],
                    },
                )
            items.append(post)
        next_cursor = None
        feed_boundary = feed_boundaries[0] if feed_boundaries else {}
        selected_candidate_count = int(
            feed_boundary.get("selected_candidate_count") or 0
        )
        if (
            bool(feed_boundary.get("has_more"))
            and selected_candidate_count > 0
            and feed_boundary.get("boundary_published_at_utc")
            and feed_boundary.get("boundary_post_key")
        ):
            next_cursor = next_window_token(
                window,
                {
                    "published_at_utc": feed_boundary[
                        "boundary_published_at_utc"
                    ],
                    "post_key": feed_boundary["boundary_post_key"],
                },
                selected_candidate_count,
            )
        return {
            "items": items,
            "next_cursor": next_cursor,
            "caught_up": next_cursor is None,
            "window_limit": window["remaining"],
        }

    def post_detail(
        self,
        post_key,
        viewer_user_key=None,
        contribution_cursor=None,
    ):
        post_key = opaque_key(post_key, field="post key")
        window = decode_contribution_token(contribution_cursor, post_key)
        size = CONTRIBUTION_PAGE_SIZE
        try:
            result_sets = self.database.execute_procedure(
                "usp_GetPublicCommunityPost",
                [
                    ("@PostKey", post_key),
                    ("@ViewerUserKey", viewer_user_key),
                    ("@AsOfUtc", window["as_of"]),
                    ("@BeforeCreatedAtUtc", window["before_time"]),
                    ("@BeforeContributionKey", window["before_key"]),
                    ("@PageSize", size),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Conversation unavailable.") from error
        rows = result_sets[0] if result_sets else []
        if not rows:
            raise CommunityNotFoundError("Post not found.")
        contribution_rows = result_sets[1] if len(result_sets) > 1 else []
        post_media = result_sets[2] if len(result_sets) > 2 else []
        contribution_media = result_sets[3] if len(result_sets) > 3 else []
        viewer_rows = result_sets[4] if len(result_sets) > 4 else []
        boundary_rows = result_sets[5] if len(result_sets) > 5 else []
        detail = _post(rows[0], _group_attachments(post_media, "post_key"))
        selected_rows = contribution_rows
        selected_keys = {str(row["contribution_key"]) for row in selected_rows}
        contribution_media = [
            row
            for row in contribution_media
            if str(row.get("contribution_key")) in selected_keys
        ]
        detail["contributions"] = list(reversed([
            _contribution(
                row, _group_attachments(contribution_media, "contribution_key")
            )
            for row in selected_rows
        ]))
        detail["next_contribution_cursor"] = (
            next_contribution_token(
                window,
                {
                    "created_at_utc": boundary_rows[0][
                        "boundary_created_at_utc"
                    ],
                    "contribution_key": boundary_rows[0][
                        "boundary_contribution_key"
                    ],
                },
            )
            if boundary_rows
            and bool(boundary_rows[0].get("has_more"))
            and boundary_rows[0].get("boundary_created_at_utc")
            and boundary_rows[0].get("boundary_contribution_key")
            else None
        )
        viewer = viewer_rows[0] if viewer_rows else {}
        detail["viewer"] = {
            "saved": bool(viewer.get("saved")),
            "response": viewer.get("response_intention"),
        }
        return detail

    def shelf_page(self, post_key, token=None, viewer_user_key=None):
        post_key = opaque_key(post_key, field="post key")
        window = decode_shelf_token(token, post_key)
        try:
            result_sets = self.database.execute_procedure(
                "usp_ListPublicCommunityShelf",
                [
                    ("@PostKey", post_key),
                    ("@AsOfUtc", window["as_of"]),
                    ("@BeforeCreatedAtUtc", window["before_time"]),
                    ("@BeforeContributionKey", window["before_key"]),
                    ("@PageSize", CONTRIBUTION_PAGE_SIZE),
                    ("@ViewerUserKey", viewer_user_key),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Replies & updates unavailable.") from error
        eligibility = result_sets[0] if result_sets else []
        if not eligibility:
            raise CommunityNotFoundError("Post not found.")
        rows = result_sets[1] if len(result_sets) > 1 else []
        media = result_sets[2] if len(result_sets) > 2 else []
        boundary_rows = result_sets[3] if len(result_sets) > 3 else []
        attachments = _group_attachments(media, "contribution_key")
        items = [_contribution(row, attachments) for row in rows]
        next_cursor = None
        if (
            boundary_rows
            and bool(boundary_rows[0].get("has_more"))
            and boundary_rows[0].get("boundary_created_at_utc")
            and boundary_rows[0].get("boundary_contribution_key")
        ):
            next_cursor = next_shelf_token(
                window,
                {
                    "created_at_utc": boundary_rows[0][
                        "boundary_created_at_utc"
                    ],
                    "contribution_key": boundary_rows[0][
                        "boundary_contribution_key"
                    ],
                },
            )
        return {
            "items": items,
            "next_cursor": next_cursor,
            "caught_up": next_cursor is None,
        }

    def selected_contribution(
        self, post_key, contribution_key, viewer_user_key=None
    ):
        post_key = opaque_key(post_key, field="post key")
        contribution_key = opaque_key(
            contribution_key, field="contribution key"
        )
        try:
            result_sets = self.database.execute_procedure(
                "usp_GetPublicCommunityContribution",
                [
                    ("@PostKey", post_key),
                    ("@ContributionKey", contribution_key),
                    ("@ViewerUserKey", viewer_user_key),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Contribution unavailable.") from error
        selected_rows = result_sets[0] if result_sets else []
        if not selected_rows:
            raise CommunityNotFoundError("Contribution not found.")
        selected_media = result_sets[1] if len(result_sets) > 1 else []
        ancestor_rows = result_sets[2] if len(result_sets) > 2 else []
        ancestor_media = result_sets[3] if len(result_sets) > 3 else []
        selected = _contribution(
            selected_rows[0],
            _group_attachments(selected_media, "contribution_key"),
        )
        ancestor_attachments = _group_attachments(
            ancestor_media, "contribution_key"
        )
        ancestors = [
            _contribution(row, ancestor_attachments) for row in ancestor_rows
        ]
        return {"contribution": selected, "ancestors": ancestors}

    def search(self, query, viewer_user_key=None):
        query = safe_search_query(query)
        try:
            result_sets = self.database.execute_procedure(
                "usp_SearchPublicCommunity",
                [
                    ("@Query", query),
                    ("@ResultLimit", 20),
                    ("@ViewerUserKey", viewer_user_key),
                ],
            )
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Search unavailable.") from error
        posts = result_sets[0] if result_sets else []
        media = result_sets[1] if len(result_sets) > 1 else []
        attachments = _group_attachments(media, "post_key")
        return [_post(row, attachments) for row in posts]


community_feed_service = CommunityFeedService()
