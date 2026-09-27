"""Declared, route-aware destinations for navigation and sign-in returns.

The declaration below is the server-side source of truth. A return target is
accepted only when Flask currently registers the declared endpoint, the
destination's feature is available, and any query value is explicitly listed.
Unknown and action URLs fail closed to a validated parent destination.
"""

from dataclasses import dataclass, field
import os
import re
from types import MappingProxyType
from urllib.parse import parse_qsl, urlencode, unquote, urlsplit

from flask import current_app
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect


DEFAULT_RETURN_PATH = "/app"
MAX_RETURN_PATH_LENGTH = 2048
_BAD_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


@dataclass(frozen=True)
class ProtectedDestination:
    """A browser-private namespace retained independently of visible nav."""

    prefix: str
    flag: str | None = None


PROTECTED_DESTINATIONS = (
    ProtectedDestination("/app"),
    ProtectedDestination("/the-slate"),
    ProtectedDestination("/interview-studio"),
    ProtectedDestination("/opportunity-slate"),
)


@dataclass(frozen=True)
class Destination:
    """One exact safe landing route and its current availability contract."""

    key: str
    path: str
    endpoints: tuple[str, ...]
    label: str = ""
    sub: str = ""
    icon: str = ""
    keys: str = ""
    surfaces: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    href_suffix: str = ""
    return_allowed: bool = False
    return_endpoints: tuple[str, ...] = ()
    return_flag: str | None = None
    availability: str | None = None
    endpoint_flags: MappingProxyType = field(
        default_factory=lambda: MappingProxyType({})
    )
    query_values: MappingProxyType = field(
        default_factory=lambda: MappingProxyType({})
    )


def _query_values(**values):
    return MappingProxyType(
        {name: frozenset(allowed) for name, allowed in values.items()}
    )


# Exact landing routes only. Dynamic object keys and write actions are handled
# by _COLLAPSE_ENDPOINTS below and never reflected to the browser.
DESTINATIONS = (
    Destination(
        "workspace", "/app", ("auth.owner_workspace",),
        label="My PeerSlate", sub="Your private starting point",
        keys="my peerslate start workspace home",
        surfaces=("account", "member_search"), return_allowed=True,
    ),
    Destination(
        "settings", "/app/settings", ("owner.settings",),
        label="Settings", sub="Account controls",
        keys="settings account my data export",
        surfaces=("account", "launchpad", "member_search"), return_allowed=True,
    ),
    Destination(
        "member_profile", "/app/profile", ("mvp1_profile.owner_profile",),
        label="My Profile", sub="Your introduction and public identity", icon="slate",
        keys="my profile introduction identity", surfaces=("account", "member_search"),
        flags=("PEERSLATE_MVP1_PROFILE_ENABLED",), return_allowed=True,
    ),
    Destination(
        "member_resume", "/app/resume", ("resume_draft.get_resume_editor_page",),
        label="My Resume", sub="Build and review your Resume", icon="slate",
        keys="my resume edit experience skills", surfaces=("account", "member_search"),
        flags=("PEERSLATE_RESUME_EDITOR_ENABLED",), return_allowed=True,
    ),
    Destination(
        "capture", "/app/capture", ("owner.capture",), return_allowed=True,
    ),
    Destination(
        "studio",
        "/app/studio/build-your-future",
        ("auth.studio_build_your_future",),
        flags=("PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED",), return_allowed=True,
    ),
    Destination(
        "workshop",
        "/app/workshop",
        ("workshop.my_information",),
        flags=("PEERSLATE_WORKSHOP_ENABLED",), return_allowed=True,
    ),
    Destination(
        "workshop_add",
        "/app/workshop/add",
        ("workshop.add_information",),
        flags=("PEERSLATE_WORKSHOP_ENABLED",), return_allowed=True,
    ),
    Destination(
        "workshop_work",
        "/app/workshop/work",
        ("workshop.work_opening",),
        flags=(
            "PEERSLATE_WORKSHOP_ENABLED",
            "PEERSLATE_WORKSHOP_SESSION_ENABLED",
        ),
        return_allowed=True,
        availability="workshop_session",
    ),
    Destination(
        "workshop_work_session",
        "/app/workshop/work/session",
        ("workshop.work_session_screen",),
        flags=(
            "PEERSLATE_WORKSHOP_ENABLED",
            "PEERSLATE_WORKSHOP_SESSION_ENABLED",
        ),
        return_allowed=True,
        availability="workshop_session",
    ),
    Destination(
        "community",
        "/the-slate",
        ("the_slate",),
        label="Community", sub="Visible to signed-in PeerSlate members",
        icon="community",
        keys="the slate hub feed people community goals progress proof connect",
        surfaces=("shell", "phone", "launchpad", "public_search", "member_search", "home_card"),
        flags=("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",), return_allowed=True,
    ),
    Destination(
        "community_deleted",
        "/the-slate/recently-deleted",
        ("community_routes.community_recently_deleted",),
        flags=("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",), return_allowed=True,
    ),
    Destination(
        "community_policy",
        "/the-slate/policy",
        ("community_routes.community_policy",),
        flags=("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",), return_allowed=True,
    ),
    Destination(
        "interview",
        "/interview-studio",
        ("interview_studio",),
        label="Interview Studio", sub="Practice, coaching, video, and growth",
        icon="interview",
        keys="interview me interview ai video practice questions star behavioral coach mock answer",
        surfaces=("shell", "phone", "launchpad", "public_search", "member_search", "home_card"),
        return_allowed=True,
        query_values=_query_values(mode=("me", "ai", "video")),
    ),
    Destination(
        "interview_history",
        "/interview-studio/history",
        ("interview_studio_history",),
        return_allowed=True, availability="interview_history",
    ),
    Destination(
        "opportunity",
        "/opportunity-slate",
        ("opportunity_slate.room", "opportunity_slate_v2.room"),
        label="Opportunity Slate",
        sub="See how your evidence lines up with a role", icon="opportunity",
        keys="opportunity slate role job posting alignment requirements evidence match analysis",
        surfaces=("shell", "launchpad", "public_search", "member_search"),
        flags=("PEERSLATE_OPPORTUNITY_SLATE_ENABLED", "PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"),
        endpoint_flags=MappingProxyType({
            "opportunity_slate.room": "PEERSLATE_OPPORTUNITY_SLATE_ENABLED",
            "opportunity_slate_v2.room": "PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED",
        }),
        return_allowed=True,
        return_endpoints=("opportunity_slate_v2.room",),
        return_flag="PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED",
        query_values=_query_values(step=("replace",)),
    ),
    Destination(
        "slate", "/app", ("auth.owner_workspace",),
        label="My PeerSlate", sub="Your private starting point", icon="slate",
        keys="my peerslate resume profile start",
        surfaces=("shell", "phone", "public_search", "member_search"),
        return_allowed=True,
    ),
    Destination(
        "story", "/petec/my-story", ("my_story",),
        label="My Story", sub="The person behind the work",
        keys="story about journey bio my story personal life",
        surfaces=("profile", "public_search", "home_card"),
    ),
    Destination(
        "skills", "/petec/skills", ("skills",),
        label="Skills in practice", sub="Sources behind the skills",
        keys="skills sources mbse sysml cameo doors expertise supporting work",
        surfaces=("public_search", "home_card"),
    ),
    Destination(
        "resume", "/petec/resume", ("profile_resume",),
        label="Résumé", sub="Detailed career record",
        keys="resume résumé career experience education certifications pmp jobs roles clearance",
        href_suffix="#resume-start", surfaces=("profile", "public_search"),
    ),
    Destination(
        "contact", "/petec/contact", ("contact",),
        label="Contact", sub="Email and LinkedIn",
        keys="contact email message linkedin reach hire connect",
        surfaces=("public_search",),
    ),
    Destination(
        "resume_download", "/static/files/pete-carter-resume.pdf", ("static",),
        label="Example résumé PDF", sub="Pete Carter's example PDF",
        keys="download resume résumé pdf file print ats",
        surfaces=(),
    ),
    Destination(
        "why", "/peerslate", ("peerslate_home",),
        label="Why PeerSlate", sub="Why the platform exists",
        keys="why peerslate about mission private first how it works",
        surfaces=("public_search", "member_search"),
    ),
)

_DESTINATION_BY_PATH = {destination.path: destination for destination in DESTINATIONS}
_DESTINATION_BY_KEY = {destination.key: destination for destination in DESTINATIONS}

# These are real routes whose URL exposes an opaque key or names an action.
# Return members to the declared parent without consulting object storage.
_COLLAPSE_ENDPOINTS = {
    "owner.account_export": "settings",
    "owner.account_export_status": "settings",
    "owner.account_export_download": "settings",
    "owner.upload_voice_capture": "capture",
    "owner.retry_voice_capture": "capture",
    "owner.confirm_voice_capture": "capture",
    "owner.delete_voice_draft": "capture",
    "owner.voice_capture_audio": "capture",
    "owner.upload_photo_capture": "capture",
    "owner.photo_capture_status": "capture",
    "owner.reconcile_photo_capture": "capture",
    "owner.confirm_photo_capture": "capture",
    "owner.delete_photo_draft": "capture",
    "owner.photo_capture_preview": "capture",
    "owner.photo_capture_original": "capture",
    "owner.create_moment_proposal": "capture",
    "owner.review_moment": "capture",
    "owner.save_moment_proposal": "capture",
    "owner.confirm_moment": "capture",
    "owner.discard_moment_proposal": "capture",
    "owner.correct_capture": "capture",
    "owner.archive_capture": "capture",
    "owner.restore_capture": "capture",
    "owner.delete_capture": "capture",
    "owner.export_capture": "capture",
    "workshop.keep_working_add": "workshop",
    "workshop.review_add": "workshop",
    "workshop.save_item": "workshop",
    "workshop.edit_information": "workshop",
    "workshop.keep_working_edit": "workshop",
    "workshop.review_edit": "workshop",
    "workshop.update_item": "workshop",
    "workshop.saved_item": "workshop",
    "workshop.archive_item": "workshop",
    "workshop.restore_item": "workshop",
    "workshop.delete_confirm": "workshop",
    "workshop.delete_item": "workshop",
    "workshop.work_session_review_redirect": "workshop_work_session",
    "workshop.reset_preview_confirm": "workshop",
    "community_routes.community_post_page": "community",
    "community_routes.community_contribution_page": "community",
    "community_routes.community_restore": "community",
    "opportunity_slate_v2.set_source": "opportunity",
    "opportunity_slate_v2.upload_source": "opportunity",
    "opportunity_slate_v2.import_source": "opportunity",
    "opportunity_slate_v2.save_identity": "opportunity",
    "opportunity_slate_v2.correct_source": "opportunity",
    "opportunity_slate_v2.confirm_source": "opportunity",
    "opportunity_slate_v2.delete_source": "opportunity",
}


def _destination_available(destination, *, endpoint=None, for_return=False):
    try:
        if for_return and destination.return_flag:
            if current_app.config.get(destination.return_flag, False) is not True:
                return False
        elif endpoint in destination.endpoint_flags:
            if current_app.config.get(
                destination.endpoint_flags[endpoint], False
            ) is not True:
                return False
        elif destination.flags and not any(
            current_app.config.get(flag, False) is True for flag in destination.flags
        ):
            return False
    except RuntimeError:
        return not destination.flags and not destination.return_flag
    if destination.availability == "interview_history":
        return os.environ.get(
            "INTERVIEW_PROGRESS_HISTORY", "preview"
        ).strip().lower() in {"preview", "enabled", "browser"}
    if destination.availability == "workshop_session":
        try:
            return all(
                current_app.config.get(flag, False) is True
                for flag in destination.flags
            )
        except RuntimeError:
            return False
    return True


def available_prefixes():
    """Compatibility view of currently available protected root routes."""
    available = []
    for protected in PROTECTED_DESTINATIONS:
        declared = _DESTINATION_BY_PATH.get(protected.prefix)
        if declared is not None and _destination_available(declared, for_return=True):
            available.append(protected.prefix)
    return tuple(available)


def _is_current_destination(destination, current_path):
    if destination.key == "community":
        return current_path == "/the-slate" or current_path.startswith("/the-slate/")
    if destination.key == "interview":
        return current_path == "/interview-studio" or current_path.startswith(
            "/interview-studio/"
        )
    if destination.key == "opportunity":
        return current_path == "/opportunity-slate" or current_path.startswith(
            "/opportunity-slate/"
        )
    return current_path == destination.path


def navigation_destinations(surface, current_path=""):
    """Return available, registered destination records for one UI surface."""
    records = []
    for destination in DESTINATIONS:
        if surface not in destination.surfaces:
            continue
        endpoint = _registered_endpoint(destination.path, "GET")
        if endpoint not in destination.endpoints or not _destination_available(
            destination, endpoint=endpoint
        ):
            continue
        records.append(
            {
                "key": destination.key,
                "label": destination.label,
                "sub": destination.sub,
                "icon": destination.icon,
                "keys": destination.keys,
                "href": destination.path + destination.href_suffix,
                "current": _is_current_destination(destination, current_path),
            }
        )
    return records


def _decoded_path_is_safe(path):
    """Reject separator/dot/control tricks through two decoding layers."""
    if _BAD_ESCAPE.search(path):
        return False
    previous = path
    for _ in range(2):
        decoded = unquote(previous, errors="strict")
        if any(ord(character) < 32 or ord(character) == 127 for character in decoded):
            return False
        if "\\" in decoded or decoded.count("/") != previous.count("/"):
            return False
        if any(segment in (".", "..") for segment in decoded.split("/")):
            return False
        previous = decoded
    return True


def _parse_candidate(candidate):
    if not candidate or not isinstance(candidate, str):
        return None
    if len(candidate) > MAX_RETURN_PATH_LENGTH:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return None
    try:
        parsed = urlsplit(candidate)
    except (TypeError, ValueError, UnicodeError):
        return None
    if parsed.scheme or parsed.netloc or parsed.fragment or not candidate.startswith("/"):
        return None
    if candidate.startswith("//") or "\\" in candidate or "//" in parsed.path:
        return None
    try:
        if not _decoded_path_is_safe(parsed.path):
            return None
        decoded_path = unquote(unquote(parsed.path, errors="strict"), errors="strict")
    except (UnicodeError, ValueError):
        return None
    if decoded_path == "/auth" or decoded_path.startswith("/auth/"):
        return None
    if decoded_path == "/.auth" or decoded_path.startswith("/.auth/"):
        return None
    try:
        pairs = (
            parse_qsl(
                parsed.query,
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=4,
            )
            if parsed.query
            else []
        )
    except (TypeError, ValueError, UnicodeError):
        return None
    if len({name for name, _ in pairs}) != len(pairs):
        return None
    return decoded_path, pairs


def _registered_endpoint(path, method):
    try:
        adapter = current_app.url_map.bind("localhost")
        endpoint, _ = adapter.match(path, method=method)
        return endpoint
    except (RuntimeError, NotFound, MethodNotAllowed, RequestRedirect, ValueError):
        return None


def _declared_result(destination, pairs):
    endpoint = _registered_endpoint(destination.path, "GET")
    if not destination.return_allowed or not _destination_available(
        destination, endpoint=endpoint, for_return=True
    ):
        return None
    allowed_endpoints = destination.return_endpoints or destination.endpoints
    if endpoint not in allowed_endpoints:
        return None
    if _registered_endpoint(destination.path, "HEAD") != endpoint:
        return None
    if any(
        name not in destination.query_values
        or value not in destination.query_values[name]
        for name, value in pairs
    ):
        return None
    if destination.key == "interview" and any(
        name == "mode"
        and value == "video"
        and os.environ.get(
            "INTERVIEW_VIDEO_STUDIO", "preview"
        ).strip().lower() not in {"preview", "enabled"}
        for name, value in pairs
    ):
        return None
    if not pairs:
        return destination.path
    return f"{destination.path}?{urlencode(pairs)}"


def _resolve(candidate, *, allow_collapse=True):
    parsed = _parse_candidate(candidate)
    if parsed is None:
        return None
    path, pairs = parsed
    destination = _DESTINATION_BY_PATH.get(path)
    if destination is not None:
        return _declared_result(destination, pairs)
    if pairs or not allow_collapse:
        return None
    for method in ("GET", "POST"):
        endpoint = _registered_endpoint(path, method)
        parent_key = _COLLAPSE_ENDPOINTS.get(endpoint)
        if parent_key is not None:
            return _declared_result(_DESTINATION_BY_KEY[parent_key], [])
    return None


def safe_return_path(candidate, default=DEFAULT_RETURN_PATH):
    """Return a declared, currently registered landing route or a safe default."""
    resolved = _resolve(candidate)
    if resolved is not None:
        return resolved
    resolved_default = _resolve(default, allow_collapse=False)
    if resolved_default is not None:
        return resolved_default
    # /app is the neutral terminal fallback. If its declaration or route ever
    # disappears, retain the inert local path instead of reflecting the caller.
    return DEFAULT_RETURN_PATH
