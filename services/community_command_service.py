"""Owner-authorized commands for canonical Community conversation truth."""

from __future__ import annotations

from services.community_contracts import (
    CONTRIBUTION_BODY_MAX,
    POST_BODY_MAX,
    POST_INTENTS,
    RESPONSE_INTENTIONS,
    RESPONSE_POSTURES,
    CommunityConflictError,
    CommunityNotFoundError,
    CommunityUnavailableError,
    CommunityValidationError,
    attachment_keys,
    bounded_text,
    enum_value,
    idempotency_key,
    opaque_key,
    optional_opaque_key,
    revision_number,
)
from services.database_service import DatabaseServiceError, database_service


class CommunityCommandService:
    def __init__(self, database=None):
        self.database = database or database_service

    @staticmethod
    def _outcome(row, *, allowed):
        outcome = row.get("outcome") if row else None
        if outcome == "not_found":
            raise CommunityNotFoundError("Community content not found.")
        if outcome == "depth_limit":
            raise CommunityValidationError(
                "Maximum reply depth reached. Add a top-level update instead."
            )
        if outcome in {"stale", "idempotency_conflict"}:
            raise CommunityConflictError("Community content changed.")
        if outcome not in allowed:
            raise CommunityUnavailableError("Community update unavailable.")
        return dict(row)

    def _call(self, procedure, parameters, allowed):
        try:
            row = self.database.last_row(procedure, parameters)
        except DatabaseServiceError as error:
            raise CommunityUnavailableError("Community update unavailable.") from error
        return self._outcome(row, allowed=allowed)

    def publish_post(self, user_key, payload, command_key):
        if not isinstance(payload, dict):
            raise CommunityValidationError("The post is invalid.")
        allowed_fields = {
            "body", "intent", "response_posture", "audience", "attachment_keys"
        }
        if set(payload) - allowed_fields:
            raise CommunityValidationError("The post contains unsupported fields.")
        if payload.get("audience") != "public":
            raise CommunityValidationError("Choose Public before publishing.")
        body = bounded_text(
            payload.get("body"), field="Post", maximum=POST_BODY_MAX
        )
        intent = enum_value(
            payload.get("intent"), field="Post intent", allowed=POST_INTENTS
        )
        posture = enum_value(
            payload.get("response_posture"),
            field="Response posture",
            allowed=RESPONSE_POSTURES,
        )
        media = attachment_keys(payload.get("attachment_keys"))
        row = self._call(
            "usp_PublishPublicCommunityPost",
            [
                ("@UserKey", user_key),
                ("@IdempotencyKey", idempotency_key(command_key)),
                ("@Body", body),
                ("@Intent", intent),
                ("@ResponsePosture", posture),
                ("@Audience", "public"),
                ("@AttachmentKeysJson", __import__("json").dumps(media)),
            ],
            {"created", "existing"},
        )
        return row

    def edit_post(self, user_key, post_key, payload, expected_revision):
        if not isinstance(payload, dict) or set(payload) - {
            "body", "intent", "response_posture"
        }:
            raise CommunityValidationError("The post edit is invalid.")
        return self._call(
            "usp_EditPublicCommunityPost",
            [
                ("@UserKey", user_key),
                ("@PostKey", opaque_key(post_key, field="post key")),
                ("@ExpectedRevision", revision_number(expected_revision)),
                ("@Body", bounded_text(payload.get("body"), field="Post", maximum=POST_BODY_MAX)),
                ("@Intent", enum_value(payload.get("intent"), field="Post intent", allowed=POST_INTENTS)),
                ("@ResponsePosture", enum_value(payload.get("response_posture"), field="Response posture", allowed=RESPONSE_POSTURES)),
            ],
            {"updated"},
        )

    def delete_post(self, user_key, post_key, expected_revision):
        return self._call(
            "usp_DeletePublicCommunityPost",
            [
                ("@UserKey", user_key),
                ("@PostKey", opaque_key(post_key, field="post key")),
                ("@ExpectedRevision", revision_number(expected_revision)),
            ],
            {"deleted", "existing"},
        )

    def add_contribution(self, user_key, post_key, payload, command_key):
        if not isinstance(payload, dict):
            raise CommunityValidationError("The contribution is invalid.")
        if set(payload) - {"body", "parent_key", "attachment_keys"}:
            raise CommunityValidationError(
                "The contribution contains unsupported fields."
            )
        parent_key = optional_opaque_key(
            payload.get("parent_key"), field="parent contribution key"
        )
        media = attachment_keys(payload.get("attachment_keys"))
        return self._call(
            "usp_AddPublicCommunityContribution",
            [
                ("@UserKey", user_key),
                ("@PostKey", opaque_key(post_key, field="post key")),
                ("@ParentContributionKey", parent_key),
                ("@Body", bounded_text(payload.get("body"), field="Reply", maximum=CONTRIBUTION_BODY_MAX)),
                ("@IdempotencyKey", idempotency_key(command_key)),
                ("@AttachmentKeysJson", __import__("json").dumps(media)),
            ],
            {"created", "existing"},
        )

    def edit_contribution(self, user_key, contribution_key, body, expected_revision):
        return self._call(
            "usp_EditPublicCommunityContribution",
            [
                ("@UserKey", user_key),
                ("@ContributionKey", opaque_key(contribution_key, field="contribution key")),
                ("@ExpectedRevision", revision_number(expected_revision)),
                ("@Body", bounded_text(body, field="Reply", maximum=CONTRIBUTION_BODY_MAX)),
            ],
            {"updated"},
        )

    def delete_contribution(self, user_key, contribution_key, expected_revision):
        return self._call(
            "usp_DeletePublicCommunityContribution",
            [
                ("@UserKey", user_key),
                ("@ContributionKey", opaque_key(contribution_key, field="contribution key")),
                ("@ExpectedRevision", revision_number(expected_revision)),
            ],
            {"deleted", "existing"},
        )

    def set_response(self, user_key, post_key, intention):
        intention = enum_value(
            intention, field="Response", allowed=RESPONSE_INTENTIONS
        )
        return self._call(
            "usp_SetPublicCommunityResponse",
            [("@UserKey", user_key), ("@PostKey", opaque_key(post_key, field="post key")), ("@Intention", intention)],
            {"saved"},
        )

    def remove_response(self, user_key, post_key):
        return self._call(
            "usp_RemovePublicCommunityResponse",
            [("@UserKey", user_key), ("@PostKey", opaque_key(post_key, field="post key"))],
            {"removed", "existing"},
        )

    def set_save(self, user_key, post_key, saved):
        return self._call(
            "usp_SetPublicCommunitySave",
            [("@UserKey", user_key), ("@PostKey", opaque_key(post_key, field="post key")), ("@Saved", bool(saved))],
            {"saved", "removed", "existing"},
        )

    def set_contribution_save(self, user_key, contribution_key, saved):
        return self._call(
            "usp_SetPublicCommunityContributionSave",
            [
                ("@UserKey", user_key),
                (
                    "@ContributionKey",
                    opaque_key(contribution_key, field="contribution key"),
                ),
                ("@Saved", bool(saved)),
            ],
            {"saved", "removed", "existing"},
        )


community_command_service = CommunityCommandService()
