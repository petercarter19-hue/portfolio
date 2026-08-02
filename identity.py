"""Tenant-safe request identity for PeerSlate APIs."""

import base64
import binascii
import json
import re
from dataclasses import dataclass

from flask import current_app, g, request

from services.database_service import database_service


OBJECT_ID_CLAIMS = (
    "oid",
    "http://schemas.microsoft.com/identity/claims/objectidentifier",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
    "sub",
)
ISSUER_CLAIMS = (
    "iss",
    "http://schemas.microsoft.com/identity/claims/issuer",
)
EMAIL_CLAIMS = (
    "email",
    "emails",
    "preferred_username",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
)
NAME_CLAIMS = (
    "name",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
)
GIVEN_NAME_CLAIMS = (
    "given_name",
    "givenname",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
)

# Entra emits these literal placeholders as the `name` claim for local
# sign-ups that never collected a real name. Treat them as "no name at all".
_PLACEHOLDER_NAMES = frozenset({"unknown", "unknownuser", "unknown user"})
AUTH_PROVIDER = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")


class AuthenticationRequired(RuntimeError):
    """Raised when a request has no trusted member identity."""


class AuthenticationPrincipalInvalid(RuntimeError):
    """Raised when a presented trusted principal cannot be safely used."""


class IdentityMappingError(RuntimeError):
    """Raised when a valid principal cannot be mapped to a PeerSlate member."""


@dataclass(frozen=True)
class PeerSlatePrincipal:
    """Validated Easy Auth (or explicit development) principal, without SQL.

    This deliberately keeps provider claims separate from the database-backed
    PeerSlate identity.  Public chrome and the session probe can therefore
    answer whether an authenticated session is present without waking Azure
    SQL or creating/updating an application account.
    """

    auth_provider: str
    auth_issuer: str
    auth_subject: str
    email: str | None = None
    display_name: str | None = None
    is_development: bool = False


@dataclass(frozen=True)
class PeerSlateIdentity:
    user_key: str
    auth_provider: str
    auth_issuer: str
    auth_subject: str
    email: str | None = None
    display_name: str | None = None
    account_key: str | None = None


def _decode_easy_auth_principal(encoded_principal):
    max_header_length = current_app.config.get(
        "PEERSLATE_AUTH_HEADER_MAX_LENGTH", 65536
    )
    if not isinstance(encoded_principal, str) or len(encoded_principal) > max_header_length:
        raise AuthenticationPrincipalInvalid("The authentication principal is invalid.")

    try:
        padding = "=" * (-len(encoded_principal) % 4)
        decoded = base64.b64decode(encoded_principal + padding, validate=True)
        principal = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthenticationPrincipalInvalid("The authentication principal is invalid.") from error

    if not isinstance(principal, dict):
        raise AuthenticationPrincipalInvalid("The authentication principal is invalid.")
    claims = principal.get("claims")
    if not isinstance(claims, list) or len(claims) > 250:
        raise AuthenticationPrincipalInvalid("The authentication principal has no claims.")

    return principal, claims


def _first_claim(claims, accepted_types):
    for accepted_type in accepted_types:
        for claim in claims:
            if not isinstance(claim, dict) or claim.get("typ") != accepted_type:
                continue
            value = claim.get("val")
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value).strip()
    return None


def _meaningful_name(value):
    """Return a stripped display name, or None when it is blank or a known
    Entra placeholder ("unknown" / "unknownuser"). Comparison is
    case-insensitive so "Unknown", "UNKNOWN", etc. are all rejected.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.casefold() in _PLACEHOLDER_NAMES:
        return None
    return cleaned


def _resolve_display_name(claims, email):
    """Pick the best human-readable display name, or None so the UI default
    ("PeerSlate member") renders.

    Order of preference:
      1. A real `name` claim (not blank, not an Entra placeholder).
      2. A real given-name claim.
      3. The local-part of the email (before the '@').
      4. None.
    """
    real_name = _meaningful_name(_first_claim(claims, NAME_CLAIMS))
    if real_name:
        return real_name

    given_name = _meaningful_name(_first_claim(claims, GIVEN_NAME_CLAIMS))
    if given_name:
        return given_name

    if email and "@" in email:
        local_part = email.split("@", 1)[0].strip()
        if local_part:
            return local_part

    return None


def _bounded_identity_value(value, label, max_length, *, required=True):
    if value is None or not str(value).strip():
        if required:
            raise AuthenticationPrincipalInvalid(
                f"The authentication principal has no stable {label}."
            )
        return None

    clean_value = str(value).strip()
    if len(clean_value) > max_length or any(ord(char) < 32 for char in clean_value):
        if required:
            raise AuthenticationPrincipalInvalid("The authentication principal is invalid.")
        return None
    return clean_value


def _easy_auth_principal(encoded_principal):
    principal, claims = _decode_easy_auth_principal(encoded_principal)
    provider = _bounded_identity_value(
        principal.get("auth_typ")
        or request.headers.get("X-MS-CLIENT-PRINCIPAL-IDP")
        or "appservice",
        "provider",
        100,
    )
    provider = provider.lower()
    if not AUTH_PROVIDER.fullmatch(provider):
        raise AuthenticationPrincipalInvalid("The authentication principal is invalid.")

    configured_issuer = current_app.config.get("PEERSLATE_AUTH_ISSUER")
    issuer = _bounded_identity_value(
        _first_claim(claims, ISSUER_CLAIMS),
        "issuer",
        500,
    ).rstrip("/")
    # The issuer arrives inside the principal the platform presents, and it is
    # part of the identity key. Treating it as advisory is safe only while
    # Azure overwrites the header at the edge; if the app ever became
    # reachable without that boundary, any issuer could be asserted. When the
    # expected issuer is configured, require it. Leaving it unset preserves
    # today's behaviour exactly.
    if configured_issuer:
        expected_issuer = str(configured_issuer).strip().rstrip("/")
        if issuer.casefold() != expected_issuer.casefold():
            raise AuthenticationPrincipalInvalid("The authentication principal is invalid.")
    subject = _bounded_identity_value(
        _first_claim(claims, OBJECT_ID_CLAIMS), "subject", 500
    )

    email = _bounded_identity_value(
        _first_claim(claims, EMAIL_CLAIMS), "email", 254, required=False
    )
    display_name = _bounded_identity_value(
        _resolve_display_name(claims, email),
        "display name",
        150,
        required=False,
    )
    return PeerSlatePrincipal(
        auth_provider=provider,
        auth_issuer=issuer,
        auth_subject=subject,
        email=email,
        display_name=display_name,
    )


def _map_principal_to_identity(principal):
    """Resolve one previously validated principal to the existing account row."""
    user = database_service.first_row(
        "usp_UpsertAppUserFromAuth",
        [
            ("@AuthProvider", principal.auth_provider),
            ("@AuthIssuer", principal.auth_issuer),
            ("@AuthSubject", principal.auth_subject),
            ("@Email", principal.email),
            ("@DisplayName", principal.display_name),
            ("@ProfileImageUrl", None),
            ("@TimezoneName", None),
        ],
    )
    if not user or not user.get("user_key"):
        raise IdentityMappingError("The authenticated member could not be mapped.")

    return PeerSlateIdentity(
        user_key=user["user_key"],
        auth_provider=principal.auth_provider,
        auth_issuer=principal.auth_issuer,
        auth_subject=principal.auth_subject,
        email=user.get("email"),
        display_name=user.get("display_name"),
        account_key=(str(user["account_key"]) if user.get("account_key") else None),
    )


def get_current_principal():
    """Return a cached validated principal without touching identity storage."""
    cached_principal = getattr(g, "peerslate_principal", None)
    if cached_principal:
        return cached_principal

    encoded_principal = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    # App Service hosting and Flask test mode do not prove that a request
    # passed through a trusted authentication boundary. Accept Easy Auth
    # headers only after that boundary has been configured and the explicit
    # application flag has been enabled.
    trust_easy_auth = (
        current_app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS", False) is True
    )

    if encoded_principal and trust_easy_auth:
        principal = _easy_auth_principal(encoded_principal)
    else:
        development_user_key = current_app.config.get("PEERSLATE_DEV_USER_KEY")
        allow_development_identity = (
            current_app.testing
            or current_app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY", False)
        )
        if not allow_development_identity or not development_user_key:
            raise AuthenticationRequired("Sign in is required.")

        principal = PeerSlatePrincipal(
            auth_provider="development",
            auth_issuer="urn:peerslate:development",
            auth_subject=development_user_key,
            display_name="Local PeerSlate Test User",
            is_development=True,
        )

    g.peerslate_principal = principal
    return principal


def get_optional_principal():
    """Return no principal only for a genuinely absent trusted principal."""
    try:
        return get_current_principal()
    except AuthenticationRequired:
        return None


def get_current_identity():
    cached_identity = getattr(g, "peerslate_identity", None)
    if cached_identity:
        return cached_identity

    principal = get_current_principal()
    if principal.is_development:
        identity = PeerSlateIdentity(
            user_key=principal.auth_subject,
            auth_provider=principal.auth_provider,
            auth_issuer=principal.auth_issuer,
            auth_subject=principal.auth_subject,
            display_name=principal.display_name,
        )
    else:
        identity = _map_principal_to_identity(principal)

    g.peerslate_identity = identity
    return identity


def get_optional_identity():
    try:
        return get_current_identity()
    except AuthenticationRequired:
        return None
