"""Default-off narrow Profile introduction and owner approval for MVP1."""

from dataclasses import asdict
from uuid import uuid4

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for
from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError
from services.profile_core_service import (
    ProfileConflictError, ProfileDraft, ProfileIdentityDraft, ProfileNotFound,
    ProfileUnavailableError, ProfileValidationError,
)

mvp1_profile = Blueprint("mvp1_profile", __name__)


@mvp1_profile.before_request
def gate():
    if current_app.config.get("PEERSLATE_MVP1_PROFILE_ENABLED") is not True:
        abort(404)
    if request.method == "POST":
        if (request.headers.get("X-PeerSlate-Request") != "same-origin"
                or request.headers.get("Sec-Fetch-Site") == "cross-site"
                or request.headers.get("Origin", request.host_url.rstrip("/")) != request.host_url.rstrip("/")):
            abort(403)


@mvp1_profile.after_request
def private_headers(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


def _binding():
    value = current_app.config.get("MVP1_PROFILE_BINDING")
    if value is None:
        raise ProfileUnavailableError("Profile is unavailable.")
    return value


def _owner():
    try:
        return get_current_identity().user_key
    except AuthenticationRequired:
        abort(404)
    except DatabaseServiceError:
        abort(503)


def _draft_and_context(binding, owner):
    draft = binding.store.draft_for_owner(owner)
    if draft is None:
        return None, None
    if type(draft) is not ProfileDraft or draft.owner_key != owner:
        raise ProfileUnavailableError("Profile is unavailable.")
    context = binding.core.owner_context(actor_key=owner, subject_owner_key=owner,
                                         slug=draft.slug, purpose="edit")
    draft = binding.core._owner_draft(context)
    if not binding.core._valid_draft_manifest(draft, require_current_sources=False):
        raise ProfileUnavailableError("Profile is unavailable.")
    return draft, context


def _state(binding, owner):
    draft, _ = _draft_and_context(binding, owner)
    reference = binding.select_for_owner(owner)
    current = binding.core._current_publication_for_owner(draft, fail_closed=True) if draft else None
    return {"draft_version": draft.version if draft else None,
            "profile_slug": draft.slug if draft else None,
            "identity": asdict(draft.identity) if draft and draft.identity else None,
            "public_revision": current.revision_key if current else None,
            "public_profile_url": url_for("mvp1_profile.public_profile", profile_slug=reference.profile_slug) if reference else None}


@mvp1_profile.get("/app/profile")
def owner_profile():
    try:
        owner = get_current_identity().user_key
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/profile"))
    except DatabaseServiceError:
        abort(503)
    try:
        state = _state(_binding(), owner)
    except ProfileUnavailableError:
        abort(503)
    return render_template("profile/profile_destination.html", mvp1=True, profile_owner=True,
                           profile_state=state, profile_destination="identity", page_title="Your Profile")


@mvp1_profile.get("/api/profile/me")
def owner_state():
    owner = _owner()
    try:
        return jsonify(success=True, **_state(_binding(), owner))
    except ProfileUnavailableError:
        return jsonify(success=False, message="Profile is unavailable. Your information is unchanged."), 503


@mvp1_profile.post("/api/profile/me/commands")
def owner_command():
    owner = _owner()
    body = request.get_json(silent=True)
    allowed = {"type", "slug", "identity", "expected_draft_version", "expected_public_revision",
               "candidate_digest", "request_id", "confirmed"}
    if type(body) is not dict or set(body) - allowed:
        return jsonify(success=False, message="Invalid Profile command."), 400
    try:
        binding = _binding()
        draft, context = _draft_and_context(binding, owner)
        action = body.get("type")
        if action == "save":
            identity = body.get("identity")
            if type(identity) is not dict or set(identity) != {"display_name", "headline", "location", "summary"}:
                raise ProfileValidationError("Complete your name, headline and introduction.")
            typed = ProfileIdentityDraft(**identity)
            if not binding.core._valid_native_manifest(typed, None, None, require_identity=True):
                raise ProfileValidationError("Check your name, headline, location and introduction.")
            if draft is None:
                if body.get("expected_draft_version") is not None:
                    raise ProfileConflictError("Profile changed. Reload before saving.")
                slug = body.get("slug")
                # Validate the explicit address and server-derived owner before any write.
                binding.core.owner_context(actor_key=owner, subject_owner_key=owner, slug=slug, purpose="edit")
                endpoint, _ = current_app.url_map.bind(request.host).match("/" + slug, method="GET")
                if (endpoint != "mvp1_profile.public_profile"
                        or slug in current_app.config.get("PEERSLATE_RESUME_FIXTURE_SLUGS", ())):
                    raise ProfileValidationError("Choose another Profile address.")
                existing_owner = binding.store.profile_for_slug(slug)
                if existing_owner is not None and existing_owner != owner:
                    raise ProfileConflictError("Choose another Profile address.")
                draft = ProfileDraft(uuid4().hex, owner, slug, "v1", typed)
                binding.store.put_draft(draft, expected_version=None)
            else:
                if body.get("slug", draft.slug) != draft.slug:
                    raise ProfileValidationError("Changing a Profile address is unavailable here.")
                binding.core.update_native_draft(context, expected_version=body.get("expected_draft_version"), identity=identity)
            return jsonify(success=True, outcome="saved_private", **_state(binding, owner))
        if draft is None:
            raise ProfileValidationError("Save your introduction before reviewing it.")
        if action in {"review", "publish"}:
            # This narrow UI cannot approve unshown full-Profile placements.
            if draft.placements or draft.about is not None or draft.current_chapter is not None:
                raise ProfileConflictError("This Profile has additional content requiring its full review.")
            args = {"expected_draft_version": body.get("expected_draft_version"),
                    "expected_public_revision": body.get("expected_public_revision")}
            if action == "review":
                return jsonify(success=True, review=binding.core.review_publication(context, **args),
                               identity=asdict(draft.identity))
            command = binding.core.publish_publication(context, **args,
                candidate_digest=body.get("candidate_digest"), idempotency_key=body.get("request_id"),
                confirmed=body.get("confirmed") is True)
        elif action == "withdraw":
            command = binding.core.withdraw_publication(context,
                expected_public_revision=body.get("expected_public_revision"),
                idempotency_key=body.get("request_id"), confirmed=body.get("confirmed") is True)
        else:
            raise ProfileValidationError("Unknown Profile command.")
        return jsonify(success=True, outcome=command.revision.action, **_state(binding, owner))
    except ProfileValidationError as error:
        return jsonify(success=False, message=str(error)), 400
    except ProfileConflictError as error:
        return jsonify(success=False, message=str(error)), 409
    except ProfileNotFound:
        abort(404)
    except (ProfileUnavailableError, DatabaseServiceError):
        return jsonify(success=False, message="Profile is unavailable. Keep your input and try again."), 503


@mvp1_profile.get("/<string:profile_slug>")
def public_profile(profile_slug):
    try:
        binding = _binding()
        owner = binding.store.profile_for_slug(profile_slug)
        if owner is None:
            abort(404)
        reference = binding.select_for_owner(owner)
        if reference is None or reference.profile_slug != profile_slug:
            abort(404)
        identity = binding.resolve(owner, reference)
        if identity is None:
            abort(404)
        from services.resume_publication_service import resume_publication_service
        publication = current_app.config.get("RESUME_PUBLICATION_SERVICE") or resume_publication_service
        resume_href = None
        if current_app.config.get("PEERSLATE_RESUME_PUBLICATION_ENABLED") is True:
            try:
                snapshot = publication.repository.load_owner(owner)
                if snapshot.get("sharing_enabled") is True and snapshot.get("current_revision") is not None and snapshot.get("slug"):
                    resume_href = url_for("profile_resume", profile_slug=snapshot["slug"])
            except Exception:
                pass
        response = render_template("profile/profile_destination.html", mvp1=True, profile_owner=False,
                                   profile_identity=identity, profile_destination="identity", page_title=identity.display_name,
                                   resume_href=resume_href)
        if binding.recheck(owner, reference).value != "current":
            abort(404)
        return response
    except ProfileUnavailableError:
        abort(503)
