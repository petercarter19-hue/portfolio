"""Verify the minimum public PeerSlate deployment boundary.

The script uses only the Python standard library so Azure can run it after
deployment without installing another operational dependency. It checks
process liveness and a small set of public routes. It never signs in, follows a
private redirect, submits data, or reads member content.
"""

from __future__ import annotations

import argparse
import http.client
import json
import socket
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    from scripts.release_identity import release_id_for_build
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from release_identity import release_id_for_build


MAX_RESPONSE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class SmokeCheck:
    path: str
    expected_status: int = 200
    expected_content_type: str | None = None
    required_texts: tuple[str, ...] = ()
    required_json: dict[str, str] | None = None
    required_headers: Mapping[str, str] = field(default_factory=dict)
    expected_xml_root: str | None = None
    # A route that may legitimately be gated behind sign-in declares the exact
    # redirect it is allowed to answer with instead. Only that precise
    # destination passes: any other 3xx, a 404, a 500, or a transport failure
    # is still a failed deployment. Without this, enabling a route's sign-in
    # wall silently turns every subsequent deployment red for every lane.
    allowed_signed_out_redirect: str | None = None


@dataclass(frozen=True)
class HttpResult:
    status: int
    content_type: str
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


def build_checks(
    release_id: str,
    *,
    base_url: str = 'https://peerslate.com',
) -> tuple[SmokeCheck, ...]:
    normalized_base = base_url.rstrip('/')
    checks = (
        SmokeCheck(
            '/healthz',
            expected_content_type='application/json',
            required_json={
                'service': 'peerslate',
                'status': 'ok',
                'release': release_id,
            },
            required_headers={
                'cache-control': 'no-store',
                'x-content-type-options': 'nosniff',
            },
        ),
        SmokeCheck(
            '/',
            expected_content_type='text/html',
            required_texts=(
                '<title>PeerSlate — Your Work. Your Story. Your Future.</title>',
                'home-v3-page',
            ),
        ),
        SmokeCheck(
            # Public while the authenticated transition is off; once
            # PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED is enabled the same
            # route answers signed-out visitors with the sign-in redirect that
            # carries the exact return destination. Both are healthy; anything
            # else is a failed deployment.
            '/interview-studio',
            expected_content_type='text/html',
            required_texts=(
                '<title>Interview Studio | PeerSlate</title>',
                'data-interview-studio',
            ),
            allowed_signed_out_redirect='/auth/sign-in?return_to=/interview-studio',
        ),
        SmokeCheck(
            '/robots.txt',
            expected_content_type='text/plain',
            required_texts=(f'Sitemap: {normalized_base}/sitemap.xml',),
        ),
        SmokeCheck(
            '/sitemap.xml',
            expected_content_type='application/xml',
            expected_xml_root='urlset',
        ),
    )
    return checks


DEFAULT_CHECKS = build_checks('unversioned')


class SmokeFailure(RuntimeError):
    """Raised when a deployment does not meet the public smoke contract."""


class NoRedirectHandler(HTTPRedirectHandler):
    """Return the original 3xx response instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None


SMOKE_OPENER = build_opener(NoRedirectHandler())


def _read_result(response, url: str) -> HttpResult:
    try:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    except (
        TimeoutError,
        socket.timeout,
        ConnectionError,
        http.client.HTTPException,
        OSError,
    ) as error:
        raise SmokeFailure(f'{url} response could not be read: {error}') from error
    if len(body) > MAX_RESPONSE_BYTES:
        raise SmokeFailure(
            f'{url} response exceeded {MAX_RESPONSE_BYTES} bytes'
        )
    return HttpResult(
        status=(
            getattr(response, 'status', None)
            or getattr(response, 'code')
        ),
        content_type=response.headers.get('Content-Type', ''),
        body=body,
        headers={key.lower(): value for key, value in response.headers.items()},
    )


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if not parsed.hostname:
        raise ValueError('base URL must include a hostname')
    if parsed.username or parsed.password:
        raise ValueError('base URL must not include credentials')
    if parsed.query or parsed.fragment:
        raise ValueError('base URL must not include a query or fragment')
    if parsed.path not in ('', '/'):
        raise ValueError('base URL must not include a path')
    is_local = parsed.hostname in {'localhost', '127.0.0.1'}
    if parsed.scheme != 'https' and not (is_local and parsed.scheme == 'http'):
        raise ValueError('base URL must use HTTPS except for localhost')
    return f'{parsed.scheme}://{parsed.netloc}'


def fetch_url(url: str, timeout_seconds: float) -> HttpResult:
    request = Request(
        url,
        headers={
            'Accept': '*/*',
            'User-Agent': 'PeerSlate-Deployment-Smoke/1.0',
        },
    )
    try:
        with SMOKE_OPENER.open(request, timeout=timeout_seconds) as response:
            return _read_result(response, url)
    except HTTPError as error:
        return _read_result(error, url)
    except SmokeFailure:
        raise
    except (
        URLError,
        TimeoutError,
        socket.timeout,
        ConnectionError,
        http.client.HTTPException,
        OSError,
    ) as error:
        reason = getattr(error, 'reason', error)
        raise SmokeFailure(f'{url} could not be reached: {reason}') from error


def verify_checks(
    base_url: str,
    checks: Iterable[SmokeCheck] = DEFAULT_CHECKS,
    *,
    timeout_seconds: float = 10.0,
    fetcher: Callable[[str, float], HttpResult] = fetch_url,
) -> list[str]:
    normalized = normalize_base_url(base_url)
    passed: list[str] = []

    for check in checks:
        target = urljoin(f'{normalized}/', check.path.lstrip('/'))
        try:
            result = fetcher(target, timeout_seconds)
        except SmokeFailure:
            raise
        except (
            TimeoutError,
            socket.timeout,
            ConnectionError,
            http.client.HTTPException,
            OSError,
        ) as error:
            raise SmokeFailure(
                f'{check.path} transport failed: {error}'
            ) from error
        if (
            check.allowed_signed_out_redirect is not None
            and result.status in (301, 302, 303, 307, 308)
        ):
            location = {
                key.lower(): value for key, value in result.headers.items()
            }.get('location')
            if location != check.allowed_signed_out_redirect:
                raise SmokeFailure(
                    f'{check.path} redirected to {location!r}; the only '
                    f'permitted signed-out destination is '
                    f'{check.allowed_signed_out_redirect!r}'
                )
            passed.append(f'{check.path} (gated: signed-out redirect verified)')
            continue

        if result.status != check.expected_status:
            raise SmokeFailure(
                f'{check.path} returned {result.status}; '
                f'expected {check.expected_status}'
            )

        if (
            check.expected_content_type
            and not result.content_type.lower().startswith(
                check.expected_content_type
            )
        ):
            raise SmokeFailure(
                f'{check.path} returned {result.content_type!r}; expected '
                f'{check.expected_content_type!r}'
            )

        normalized_headers = {
            key.lower(): value for key, value in result.headers.items()
        }
        for name, expected in check.required_headers.items():
            actual = normalized_headers.get(name.lower())
            if actual != expected:
                raise SmokeFailure(
                    f'{check.path} header {name!r} was {actual!r}; '
                    f'expected {expected!r}'
                )

        decoded = result.body.decode('utf-8', errors='replace')
        for required_text in check.required_texts:
            if required_text not in decoded:
                raise SmokeFailure(
                    f'{check.path} did not contain {required_text!r}'
                )

        if check.required_json is not None:
            try:
                payload = json.loads(decoded)
            except json.JSONDecodeError as error:
                raise SmokeFailure(f'{check.path} returned invalid JSON') from error
            if not isinstance(payload, dict):
                raise SmokeFailure(f'{check.path} JSON must be an object')
            if payload != check.required_json:
                raise SmokeFailure(
                    f'{check.path} JSON did not match the exact public contract'
                )

        if check.expected_xml_root is not None:
            try:
                root = ET.fromstring(decoded)
            except ET.ParseError as error:
                raise SmokeFailure(f'{check.path} returned invalid XML') from error
            local_name = root.tag.rsplit('}', 1)[-1]
            if local_name != check.expected_xml_root:
                raise SmokeFailure(
                    f'{check.path} XML root was {local_name!r}; expected '
                    f'{check.expected_xml_root!r}'
                )

        passed.append(check.path)

    return passed


def verify_with_retries(
    base_url: str,
    *,
    retry_delay_seconds: float,
    timeout_seconds: float,
    warmup_seconds: float,
    checks: Iterable[SmokeCheck] = DEFAULT_CHECKS,
    fetcher: Callable[[str, float], HttpResult] = fetch_url,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> list[str]:
    if retry_delay_seconds <= 0:
        raise ValueError('retry delay must be greater than zero')
    if timeout_seconds <= 0:
        raise ValueError('timeout must be greater than zero')
    if warmup_seconds < 0:
        raise ValueError('warm-up window must not be negative')

    deadline = monotonic() + warmup_seconds
    attempt = 0
    while True:
        attempt += 1
        try:
            return verify_checks(
                base_url,
                checks=checks,
                timeout_seconds=timeout_seconds,
                fetcher=fetcher,
            )
        except SmokeFailure as error:
            print(
                f'Smoke attempt {attempt} failed: {error}',
                file=sys.stderr,
            )
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise
            sleeper(min(retry_delay_seconds, remaining))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Verify the public PeerSlate deployment boundary.',
    )
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--expected-source-version', required=True)
    parser.add_argument('--expected-build-id', required=True)
    parser.add_argument('--warmup-seconds', type=float, default=180.0)
    parser.add_argument('--retry-delay', type=float, default=10.0)
    parser.add_argument('--timeout', type=float, default=15.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        expected_release_id = release_id_for_build(
            args.expected_source_version,
            args.expected_build_id,
        )
        normalized_base = normalize_base_url(args.base_url)
        passed = verify_with_retries(
            normalized_base,
            retry_delay_seconds=args.retry_delay,
            timeout_seconds=args.timeout,
            warmup_seconds=args.warmup_seconds,
            checks=build_checks(
                expected_release_id,
                base_url=normalized_base,
            ),
        )
    except (SmokeFailure, ValueError) as error:
        print(f'Deployment smoke failed: {error}', file=sys.stderr)
        return 1

    print(
        'Deployment smoke passed: '
        + ', '.join(passed)
        + f' at {normalized_base}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
