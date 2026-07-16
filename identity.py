"""Tenant-safe request identity for PeerSlate APIs."""

import base64
import json
from dataclasses import dataclass

from flask import current_app, g, request

from services.database_service import database_service


OBJECT_ID_CLAIMS = {
    "oid",
    "sub",
    "http://schemas.microsoft.com/identity/claims/objectidentifier",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
}
EMAIL_CLAIMS = {
    "email",
    "emails",
    "preferred_username",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
}
NAME_CLAIMS = {
    "name",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
}


class AuthenticationRequired(RuntimeError):
    """Raised when a request has no trusted member identity."""


@dataclass(frozen=True)
class PeerSlateIdentity:
    user_key: str
    auth_provider: str
    auth_subject: str
    email: str | None = None
    display_name: str | None = None


def _decode_easy_auth_principal(encoded_principal):
    try:
        padding = "=" * (-len(encoded_principal) % 4)
        decoded = base64.b64decode(encoded_principal + padding)
        principal = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthenticationRequired("The authentication identity is invalid.") from error

    claims = principal.get("claims")
    if not isinstance(claims, list):
        raise AuthenticationRequired("The authentication identity has no claims.")

    return principal, claims


def _first_claim(claims, accepted_types):
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if claim.get("typ") in accepted_types and claim.get("val"):
            return str(claim["val"])
    return None


def _easy_auth_identity(encoded_principal):
    principal, claims = _decode_easy_auth_principal(encoded_principal)
    provider = (
        principal.get("auth_typ")
        or request.headers.get("X-MS-CLIENT-PRINCIPAL-IDP")
        or "appservice"
    )
    subject = _first_claim(claims, OBJECT_ID_CLAIMS)
    if not subject:
        raise AuthenticationRequired("The authentication identity has no stable subject.")

    email = _first_claim(claims, EMAIL_CLAIMS)
    display_name = _first_claim(claims, NAME_CLAIMS) or email
    user = database_service.first_row(
        "usp_UpsertAppUserFromAuth",
        [
            ("@AuthProvider", provider),
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
        auth_subject=subject,
        email=user.get("email"),
        display_name=user.get("display_name"),
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
            auth_subject=development_user_key,
            display_name="Local PeerSlate Test User",
        )

    g.peerslate_identity = identity
    return identity
