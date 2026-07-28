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
        raise AuthenticationRequired("The authentication identity is invalid.")

    try:
        padding = "=" * (-len(encoded_principal) % 4)
        decoded = base64.b64decode(encoded_principal + padding, validate=True)
        principal = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthenticationRequired("The authentication identity is invalid.") from error

    if not isinstance(principal, dict):
        raise AuthenticationRequired("The authentication identity is invalid.")
    claims = principal.get("claims")
    if not isinstance(claims, list) or len(claims) > 250:
        raise AuthenticationRequired("The authentication identity has no claims.")

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
            raise AuthenticationRequired(
                f"The authentication identity has no stable {label}."
            )
        return None

    clean_value = str(value).strip()
    if len(clean_value) > max_length or any(ord(char) < 32 for char in clean_value):
        if required:
            raise AuthenticationRequired("The authentication identity is invalid.")
        return None
    return clean_value


def _easy_auth_identity(encoded_principal):
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
        raise AuthenticationRequired("The authentication identity is invalid.")

    issuer = _bounded_identity_value(
        _first_claim(claims, ISSUER_CLAIMS)
        or current_app.config.get("PEERSLATE_AUTH_ISSUER"),
        "issuer",
        500,
    ).rstrip("/")
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
    user = database_service.first_row(
        "usp_UpsertAppUserFromAuth",
        [
            ("@AuthProvider", provider),
            ("@AuthIssuer", issuer),
            ("@AuthSubject", subject),
            ("@Email", email),
            ("@DisplayName", display_name),
            ("@ProfileImageUrl", None),
            ("@TimezoneName", None),
        ],
    )
    if not user or not user.get("user_key"):
        raise AuthenticationRequired("The authenticated member could not be loaded.")

    return PeerSlateIdentity(
        user_key=user["user_key"],
        auth_provider=provider,
        auth_issuer=issuer,
        auth_subject=subject,
        email=user.get("email"),
        display_name=user.get("display_name"),
        account_key=(str(user["account_key"]) if user.get("account_key") else None),
    )


def get_current_identity():
    cached_identity = getattr(g, "peerslate_identity", None)
    if cached_identity:
        return cached_identity

    encoded_principal = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    # App Service hosting and Flask test mode do not prove that a request
    # passed through a trusted authentication boundary. Accept Easy Auth
    # headers only after that boundary has been configured and the explicit
    # application flag has been enabled.
    trust_easy_auth = (
        current_app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS", False) is True
    )

    if encoded_principal and trust_easy_auth:
        identity = _easy_auth_identity(encoded_principal)
    else:
        development_user_key = current_app.config.get("PEERSLATE_DEV_USER_KEY")
        allow_development_identity = (
            current_app.testing
            or current_app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY", False)
        )
        if not allow_development_identity or not development_user_key:
            raise AuthenticationRequired("Sign in is required.")

        identity = PeerSlateIdentity(
            user_key=development_user_key,
            auth_provider="development",
            auth_issuer="urn:peerslate:development",
            auth_subject=development_user_key,
            display_name="Local PeerSlate Test User",
        )

    g.peerslate_identity = identity
    return identity


def get_optional_identity():
    try:
        return get_current_identity()
    except AuthenticationRequired:
        return None
