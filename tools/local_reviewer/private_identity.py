"""One private local profile behind the owner's verified Tailscale identity."""
from __future__ import annotations

from dataclasses import dataclass
import hmac
import re
from urllib.parse import urlsplit
from uuid import UUID


class PrivateAccessDenied(ValueError):
    pass


@dataclass(frozen=True)
class PrivateIdentity:
    origin: str
    login: str
    owner: str
    display_name: str

    @classmethod
    def from_config(cls, config):
        if not isinstance(config, dict) or set(config) != {"origin", "login", "owner", "display_name"}:
            raise ValueError("Complete private profile configuration required")
        origin, login, owner, display = (config[k] for k in ("origin", "login", "owner", "display_name"))
        if not isinstance(origin, str) or not re.fullmatch(
            r"https://[a-z0-9-]+\.[a-z0-9-]+\.ts\.net(?::[0-9]{1,5})?", origin
        ):
            raise ValueError("Exact private Tailscale HTTPS origin required")
        parsed = urlsplit(origin)
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Invalid HTTPS port")
        if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9_.+@-]{1,200}", login):
            raise ValueError("Exact Tailscale login required")
        if not isinstance(owner, str) or str(UUID(owner)) != owner:
            raise ValueError("Persistent private owner UUID required")
        if not isinstance(display, str) or not 1 <= len(display) <= 80 or any(ord(c) < 32 for c in display):
            raise ValueError("Private profile display name required")
        return cls(origin, login, owner, display)

    def authorize(self, environ):
        """Only the local Serve proxy supplies the authenticated edge identity.

        Other processes on this Windows account remain trusted administrators
        of this installation. Browser selector cookies never select its owner.
        """
        host = urlsplit(self.origin).netloc
        if (environ.get("REMOTE_ADDR") != "127.0.0.1"
                or environ.get("HTTP_HOST") != host
                or environ.get("HTTP_X_FORWARDED_HOST") != host
                or environ.get("HTTP_X_FORWARDED_PROTO") != "https"
                or not hmac.compare_digest(
                    environ.get("HTTP_TAILSCALE_USER_LOGIN", "").encode("utf-8"),
                    self.login.encode("utf-8"))):
            raise PrivateAccessDenied("Open the private address with your Tailscale account")
        origin = environ.get("HTTP_ORIGIN")
        if ((origin is not None and origin != self.origin)
                or environ.get("HTTP_SEC_FETCH_SITE") == "cross-site"
                or (environ.get("REQUEST_METHOD") not in {"GET", "HEAD", "OPTIONS"}
                    and origin != self.origin)):
            raise PrivateAccessDenied("Same-origin private request required")
        return self.owner

    def bind_principal(self, stack):
        """Compose the local member key after edge authentication, without SQL."""
        from flask import request
        from identity import AuthenticationRequired, PeerSlatePrincipal
        from unittest.mock import patch

        def principal():
            if request.environ.get("local_reviewer.private_owner") != self.owner:
                raise AuthenticationRequired()
            # This remains a local development profile, authenticated by the
            # outer Tailscale boundary. No production account is impersonated.
            return PeerSlatePrincipal("development", "private-local-tailscale", self.owner,
                                      display_name=self.display_name, is_development=True)

        stack.enter_context(patch("identity.get_current_principal", side_effect=principal))
        stack.enter_context(patch("auth_routes.get_current_principal", side_effect=principal))
