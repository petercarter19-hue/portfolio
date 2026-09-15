"""Pure response-policy decisions for the public resume quiet preview.

The Flask integration deliberately stays outside this module.  Callers supply
the response MIME type and, for static requests, the containment-safe canonical
filename already resolved by the application.  Keeping that boundary explicit
prevents a raw URL spelling or file suffix from widening the two-file public
resume resource policy.
"""

from dataclasses import dataclass


QUIET_PREVIEW_X_ROBOTS_TAG = "noindex, nofollow, noarchive, noimageindex"

PUBLIC_STATIC_IMMUTABLE_CACHE_CONTROL = (
    "public, max-age=31536000, immutable"
)
PUBLIC_STATIC_FALLBACK_CACHE_CONTROL = (
    "public, max-age=3600, stale-while-revalidate=86400"
)

PUBLIC_RESUME_DATA_STATIC_FILENAME = "data/resume_data.json"
PUBLIC_RESUME_PDF_STATIC_FILENAME = "files/pete-carter-resume.pdf"
PUBLIC_RESUME_STATIC_FILENAMES = frozenset(
    {
        PUBLIC_RESUME_DATA_STATIC_FILENAME,
        PUBLIC_RESUME_PDF_STATIC_FILENAME,
    }
)

ROBOTS_TXT_BODY = "\n".join(
    (
        "User-agent: *",
        "Allow: /",
        "Disallow: /app",
        "Disallow: /api/",
        "Disallow: /owner",
        "Disallow: /the-slate",
        "Disallow: /interview-studio",
        "",
    )
)

EMPTY_SITEMAP_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
)

_PROTECTIVE_CACHE_DIRECTIVES = frozenset(
    {"private", "no-store", "no-transform"}
)
_REVALIDATION_CACHE_DIRECTIVES = frozenset({"no-cache", "must-revalidate"})
_BOUNDED_STATIC_MAX_AGE = 3600


@dataclass(frozen=True)
class ResponsePolicy:
    """Headers selected by :func:`resolve_response_policy`.

    ``None`` means the integration must leave that header untouched.
    """

    x_robots_tag: str | None = None
    cache_control: str | None = None


def is_quiet_preview_response(
    request_path: str,
    *,
    response_mimetype: str | None,
    canonical_static_filename: str | None = None,
) -> bool:
    """Return whether this response stays out of indexes during preview.

    ``canonical_static_filename`` is intentionally not normalized here.  It
    must be the containment-safe key produced by the application's existing
    static-file resolver; only the two exact public-resume files qualify.
    Every HTML response outside the private ``/app`` namespace qualifies,
    including errors and generic public member resumes.
    """

    normalized_mimetype = (
        (response_mimetype or "").partition(";")[0].strip().lower()
    )
    private_app_path = request_path == "/app" or request_path.startswith("/app/")
    return (
        (normalized_mimetype == "text/html" and not private_app_path)
        or canonical_static_filename in PUBLIC_RESUME_STATIC_FILENAMES
    )


def _cache_directives(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(
        directive.strip().lower()
        for directive in value.split(",")
        if directive.strip()
    )


def _has_protective_cache_directive(value: str | None) -> bool:
    names = {directive.split("=", 1)[0] for directive in _cache_directives(value)}
    return bool(names & _PROTECTIVE_CACHE_DIRECTIVES)


def _quiet_preview_robots_tag(existing: str | None) -> str:
    if not existing:
        return QUIET_PREVIEW_X_ROBOTS_TAG

    directives = tuple(
        directive.strip()
        for directive in existing.split(",")
        if directive.strip()
    )
    if any(directive.lower() == "noindex" for directive in directives):
        return existing

    # Preserve non-conflicting existing restrictions while removing explicit
    # opt-in directives that would contradict this selected response's
    # required noindex policy.
    retained = [
        directive
        for directive in directives
        if directive.lower() not in {"index", "follow"}
    ]
    retained.extend(QUIET_PREVIEW_X_ROBOTS_TAG.split(", "))
    return ", ".join(dict.fromkeys(retained))


def _is_existing_cache_stricter_than_public_fallback(
    value: str | None,
) -> bool:
    directives = _cache_directives(value)
    names = {directive.split("=", 1)[0] for directive in directives}
    if names & _REVALIDATION_CACHE_DIRECTIVES:
        return "immutable" not in names

    for directive in directives:
        name, separator, raw_value = directive.partition("=")
        if name not in {"max-age", "s-maxage"} or not separator:
            continue
        try:
            max_age = int(raw_value.strip().strip('"'))
        except ValueError:
            continue
        if max_age <= _BOUNDED_STATIC_MAX_AGE:
            return "immutable" not in names
    return False


def resolve_response_policy(
    request_path: str,
    *,
    response_mimetype: str | None,
    canonical_static_filename: str | None = None,
    status_code: int = 200,
    existing_x_robots_tag: str | None = None,
    existing_cache_control: str | None = None,
    static_cache_eligible: bool = False,
    requested_static_version: str | None = None,
    current_static_version: str | None = None,
) -> ResponsePolicy:
    """Resolve quiet-preview and public-static headers in precedence order.

    Policy order is intentional:

    1. Existing X-Robots-Tag values and cache policies containing ``private``,
       ``no-store`` or ``no-transform`` are never weakened.
    2. Every HTML response outside ``/app`` and its descendants, plus the
       exact canonical resume JSON/PDF filenames, receives quiet-preview
       noindex guidance.
    3. The public resume PDF always uses bounded caching, even when its query
       token exactly matches current content.  An already stricter bounded or
       revalidation policy is preserved.
    4. Other eligible static assets retain the established behavior: only an
       exact, non-empty current content version is immutable for one year;
       stale, wrong, or absent versions use the bounded fallback.
    5. Non-success responses and non-eligible resources keep their existing
       cache policy.
    """

    quiet_preview = is_quiet_preview_response(
        request_path,
        response_mimetype=response_mimetype,
        canonical_static_filename=canonical_static_filename,
    )
    x_robots_tag = existing_x_robots_tag
    if quiet_preview:
        x_robots_tag = _quiet_preview_robots_tag(existing_x_robots_tag)

    cache_control = existing_cache_control
    if not 200 <= status_code < 300:
        return ResponsePolicy(
            x_robots_tag=x_robots_tag,
            cache_control=cache_control,
        )

    if _has_protective_cache_directive(existing_cache_control):
        return ResponsePolicy(
            x_robots_tag=x_robots_tag,
            cache_control=existing_cache_control,
        )

    if canonical_static_filename == PUBLIC_RESUME_PDF_STATIC_FILENAME:
        if _is_existing_cache_stricter_than_public_fallback(
            existing_cache_control
        ):
            cache_control = existing_cache_control
        else:
            cache_control = PUBLIC_STATIC_FALLBACK_CACHE_CONTROL
    elif static_cache_eligible:
        if _is_existing_cache_stricter_than_public_fallback(
            existing_cache_control
        ):
            cache_control = existing_cache_control
        elif (
            requested_static_version
            and current_static_version
            and requested_static_version == current_static_version
        ):
            cache_control = PUBLIC_STATIC_IMMUTABLE_CACHE_CONTROL
        else:
            cache_control = PUBLIC_STATIC_FALLBACK_CACHE_CONTROL

    return ResponsePolicy(
        x_robots_tag=x_robots_tag,
        cache_control=cache_control,
    )


def robots_txt() -> str:
    """Return crawlable robots.txt bytes without advertising a sitemap."""

    return ROBOTS_TXT_BODY


def empty_sitemap_xml() -> str:
    """Return a valid sitemap document with no advertised public URLs."""

    return EMPTY_SITEMAP_XML


__all__ = [
    "EMPTY_SITEMAP_XML",
    "PUBLIC_RESUME_DATA_STATIC_FILENAME",
    "PUBLIC_RESUME_PDF_STATIC_FILENAME",
    "PUBLIC_RESUME_STATIC_FILENAMES",
    "PUBLIC_STATIC_FALLBACK_CACHE_CONTROL",
    "PUBLIC_STATIC_IMMUTABLE_CACHE_CONTROL",
    "QUIET_PREVIEW_X_ROBOTS_TAG",
    "ROBOTS_TXT_BODY",
    "ResponsePolicy",
    "empty_sitemap_xml",
    "is_quiet_preview_response",
    "resolve_response_policy",
    "robots_txt",
]
