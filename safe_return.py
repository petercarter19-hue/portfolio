"""Single source of truth for post-authentication return destinations.

Every surface that sends a signed-out member through sign-in builds its return
target here, and :mod:`auth_routes` validates the arriving value here.  One
parser, one allowlist, one place to register a protected destination.

PS-SIGNIN-MEMBER-ARRIVAL-001.  Before this module there were four separate
implementations: ``auth_routes`` held the only allowlist, while
``workshop_routes``, ``opportunity_slate_v2_routes`` and ``community_routes``
each built return targets their own way — two of them carrying docstrings
claiming they mirrored a sibling "exactly" when they did not.  The producers
were permissive and the single consumer was strict, so a namespace that was
never added to the consumer's allowlist was accepted by its own room, silently
rejected on arrival, and the member was dropped on ``/app`` with no
explanation.  Opportunity Slate shipped in exactly that state and was proven
live on 2026-08-16.

Sharing this module is what stops the mismatch recurring: a destination that is
not registered here fails a test rather than a member's journey.

The validator is deliberately fail-safe.  Anything it cannot positively
recognise resolves to the caller's default (``/app`` unless stated), never to
the candidate.  Rejection is silent by design at this layer; telling the member
their destination was dropped is the caller's job, not the parser's.
"""

from collections import namedtuple
from urllib.parse import urlsplit

from flask import current_app


DEFAULT_RETURN_PATH = "/app"

# A return target is a URL a member typed, followed, or was redirected from.
# Anything longer than this is not a real destination.
MAX_RETURN_PATH_LENGTH = 2048


#: ``prefix`` is the protected namespace.  ``flag`` is the configuration key
#: that must be true for the namespace to be reachable, or ``None`` when the
#: namespace is unconditional.  A flag-gated destination is only a valid
#: return target while its flag is on, so a member is never returned to a
#: route that would answer 404.
ProtectedDestination = namedtuple("ProtectedDestination", ("prefix", "flag"))


PROTECTED_DESTINATIONS = (
    # The private owner workspace and everything beneath it.
    ProtectedDestination("/app", None),
    # PS-COMMUNITY-AUTH-WALL-001: Community lives behind sign-in.
    ProtectedDestination("/the-slate", None),
    # PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001: unconditional, so a
    # return_to=/interview-studio round trip is correct even while the page
    # is still public.
    ProtectedDestination("/interview-studio", None),
    # PS-SIGNIN-MEMBER-ARRIVAL-001: the signed-in-only Opportunity Slate room
    # gates every one of its endpoints on sign-in and builds this exact return
    # target.  Flag-gated because the legacy public room registers at the same
    # path when the flag is off, and a stale return target must not land a
    # member on a 404.
    ProtectedDestination(
        "/opportunity-slate", "PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED"
    ),
)


def _destination_available(destination):
    """Whether this destination is reachable in the current configuration.

    Outside an application context there is no configuration to consult, so a
    flag-gated destination is treated as unavailable — the fail-safe answer.
    """
    if destination.flag is None:
        return True
    try:
        return current_app.config.get(destination.flag, False) is True
    except RuntimeError:
        return False


def available_prefixes():
    """The protected prefixes a member may currently be returned to."""
    return tuple(
        destination.prefix
        for destination in PROTECTED_DESTINATIONS
        if _destination_available(destination)
    )


def safe_return_path(candidate, default=DEFAULT_RETURN_PATH):
    """Return ``candidate`` when it is a safe same-origin destination.

    Every guard below is load-bearing and each rejects to ``default`` rather
    than raising, because a hostile or malformed return target is an ordinary
    thing to receive on a public endpoint, not an error.
    """
    if not candidate or not isinstance(candidate, str):
        return default
    if len(candidate) > MAX_RETURN_PATH_LENGTH:
        return default
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return default
    parsed = urlsplit(candidate)
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or not candidate.startswith("/")
    ):
        return default
    if candidate.startswith("//") or "\\" in candidate:
        return default
    if "//" in candidate:
        return default
    # PS-SIGNIN-MEMBER-ARRIVAL-001.  urlsplit does not remove RFC 3986 dot
    # segments, so without this a candidate such as "/app/../.auth/logout"
    # satisfies every check above — it starts with an allowlisted prefix and
    # carries no scheme, host, fragment, backslash or "//" — and then resolves
    # in the browser to exactly the provider path the exclusions below exist to
    # keep out.  Rejecting the segment outright is simpler than resolving it,
    # and no legitimate destination contains one.
    if any(segment == ".." for segment in parsed.path.split("/")):
        return default
    if parsed.path == "/auth" or parsed.path.startswith("/auth/"):
        return default
    if parsed.path == "/.auth" or parsed.path.startswith("/.auth/"):
        return default
    if not any(
        parsed.path == prefix or parsed.path.startswith(prefix + "/")
        for prefix in available_prefixes()
    ):
        return default
    return candidate
