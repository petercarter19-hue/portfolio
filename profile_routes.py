"""Unregistered Profile D0 HTML blueprint.

This module intentionally exports a blueprint but never imports ``app`` or
registers itself.  The later production-capable integration package owns
registration, feature configuration, trusted Easy Auth resolution, and every
live route cutover.  D0 routes exist only as isolated contract surfaces.
"""

from __future__ import annotations

from typing import Callable

from flask import Blueprint, Response, abort, current_app, render_template

from services.profile_core_service import (
    ProfileAuthorizationError,
    ProfileCoreService,
    ProfileNotFound,
    ProfileUnavailableError,
)


profile_routes = Blueprint("profile_routes", __name__)


def _service() -> ProfileCoreService:
    provider: Callable[[], ProfileCoreService] | None = current_app.config.get(
        "PEERSLATE_PROFILE_CORE_SERVICE_PROVIDER"
    )
    if provider is None:
        raise ProfileUnavailableError("Profile foundation dependency unavailable.")
    service = provider()
    if not isinstance(service, ProfileCoreService):
        raise ProfileUnavailableError("Profile foundation dependency unavailable.")
    return service


def _profile_response(slug: str, destination: str) -> Response:
    try:
        model = _service().public_read(slug=slug, destination=destination)
    except (ProfileNotFound, ProfileAuthorizationError):
        abort(404)
    except ProfileUnavailableError:
        abort(503)
    response = Response(
        render_template(
            "profile/profile_destination.html",
            profile=model,
            profile_destination=destination,
            profile_owner=False,
            profile_preview=False,
        )
    )
    _private_safe_headers(response)
    return response


@profile_routes.get("/<string:profile_slug>/profile-home")
def profile_home_contract(profile_slug: str):
    """D0-only noncanonical contract route; integration replaces its path."""

    return _profile_response(profile_slug, "home")


@profile_routes.get("/<string:profile_slug>/profile-posts")
def profile_posts_contract(profile_slug: str):
    """D0-only noncanonical contract route; integration replaces its path."""

    return _profile_response(profile_slug, "posts")


@profile_routes.get("/<string:profile_slug>/profile-about")
def profile_about_contract(profile_slug: str):
    """D0-only noncanonical contract route; integration replaces its path."""

    return _profile_response(profile_slug, "about")


@profile_routes.get("/<string:profile_slug>/profile-projects")
def profile_projects_contract(profile_slug: str):
    return _profile_response(profile_slug, "projects")


@profile_routes.get("/<string:profile_slug>/profile-media")
def profile_media_contract(profile_slug: str):
    return _profile_response(profile_slug, "media")


@profile_routes.get("/<string:profile_slug>/profile-voice")
def profile_voice_contract(profile_slug: str):
    return _profile_response(profile_slug, "voice")


def _private_safe_headers(response: Response) -> None:
    # D0 responses are intentionally no-store: later public caching must prove
    # safe revision invalidation and signed-in block handling first.
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Content-Type-Options"] = "nosniff"


@profile_routes.after_request
def profile_headers(response: Response) -> Response:
    _private_safe_headers(response)
    return response
