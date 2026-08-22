"""Deterministic guarded source-fragment projection for app.py (B2).

Hashing all of app.py would make every unrelated PeerSlate change move
Interview identity, which §2 forbids. Instead, the exact
Interview-affecting boundary inside app.py — signing-serializer
construction with its key derivation and salt, the effective provider
client construction, and the complete route boundary (decorators, rate
limits, refusal ordering/status/copy, request JSON handoff, response
serialization, the JobDeps assembly, and the signed-context wrappers) —
is fenced by named fragment markers, and the exact bytes between the
markers are bound into guarded-paths.json as `app.py#fragment=<name>`
entries.

The extractor is deliberately strict: a missing, unknown, duplicated,
nested, or unterminated fragment is an error, and a fragment that no
longer contains its expected executed symbols/decorators is an error —
so behaviour cannot drift out of a fragment leaving a dead guarded copy
behind, and marker games cannot silently shrink the boundary. Runtime
release resolution runs this same extractor, so a deployed app.py whose
fragments do not verify fails closed to `service_not_configured`.
"""

FRAGMENT_OPEN = "# >>> INTERVIEW-GUARDED-FRAGMENT: "
FRAGMENT_CLOSE = "# <<< END-INTERVIEW-GUARDED-FRAGMENT: "

# The closed fragment set and, per fragment, the executed symbols whose
# presence the builder and runtime both require (B2: "reject a fragment
# that no longer contains the expected executed symbol/decorator").
EXPECTED_FRAGMENTS = {
    # Correction B2 (consolidated review): the guarded closure covers every
    # app.py helper, global, and hook that can alter authorization, refusal
    # precedence, provider bytes, status, headers, response serialization,
    # evidence, context, or call eligibility for the Interview boundary.
    "interview_hostname_pattern": (
        "_HOSTNAME_PATTERN",
    ),
    "interview_canonical_host_helpers": (
        "def _hostname_without_port",
        "def _configured_canonical_host",
        "def _canonical_location",
        "def _canonical_redirect_or_reject",
    ),
    "interview_provider_key_binding": (
        "ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')",
    ),
    "interview_abuse_and_rate_limit": (
        "def _address_without_port",
        "def _cross_site_refusal",
        "def _client_rate_limit_key",
        "limiter = Limiter(",
        "_client_rate_limit_key,",
    ),
    "interview_response_compression": (
        "@app.after_request",
        "def _compress_public_text_response",
    ),
    "interview_privacy_and_cache_hook": (
        "@app.after_request",
        "def prevent_stale_html",
    ),
    "interview_legacy_path_registries": (
        "RETIRED_PORTFOLIO_PATHS",
        "LEGACY_INTERVIEW_PATHS",
    ),
    "interview_canonical_request_gate": (
        "@app.before_request",
        "def keep_portfolio_on_canonical_path",
    ),
    "interview_entitlements_and_evidence": (
        "def get_interview_entitlements",
        "def _interview_metric_tag",
        "def _interview_evidence_from_profile",
        "def _interview_page_context",
        "def _interview_member_profile",
        "def _interview_identity_evidence_context",
    ),
    "interview_profile_fixture_registry": (
        "RESUME_PROFILE_FILES",
    ),
    "interview_resume_profile_loader": (
        "def _load_resume_profile",
    ),
    "interview_legacy_redirect_target": (
        "def _legacy_interview_redirect_target",
    ),
    "interview_profile_projects_loader": (
        "def _load_profile_projects",
    ),
    "interview_platform_hostname_check": (
        "def is_platform_hostname",
    ),
    "interview_compression_support": (
        "_VERSIONED_STATIC_SUFFIXES",
        "_COMPRESSIBLE_STATIC_SUFFIXES",
        "_GZIP_MINIMUM_BYTES",
        "def _canonical_static_file",
        "def _static_file_version",
    ),
    "interview_retired_coach_contract": (
        "@app.route('/api/interview/coach', methods=['POST'])",
        "@limiter.limit('10 per minute')",
        "def interview_coach",
        "), 410",
    ),
    "interview_error_contracts": (
        "def _is_private_json_request",
        "def _auth_recovery_response",
        "def _rate_limit_retry_after_seconds",
        "@app.errorhandler(404)",
        "@app.errorhandler(429)",
        "@app.errorhandler(500)",
        "@app.errorhandler(AuthenticationPrincipalInvalid)",
        "@app.errorhandler(IdentityMappingError)",
    ),
    "interview_signing_serializer": (
        "INTERVIEW_CONTEXT_SIGNING_KEY",
        "peerslate-interview-context-v1:",
        "URLSafeTimedSerializer(",
        "salt='peerslate-interview-model-answer-v1'",
    ),
    "interview_provider_client": (
        "client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)",
    ),
    "interview_route_boundary": (
        "@app.route('/api/interview/review', methods=['POST'])",
        "@app.route('/api/interview/improve', methods=['POST'])",
        "@app.route('/api/interview/nudge', methods=['POST'])",
        "@app.route('/api/interview/model-answer', methods=['POST'])",
        "@limiter.limit('6 per minute')",
        "@limiter.limit('8 per minute')",
        "def _interview_api_authenticated_identity",
        "def _interview_job_deps",
        "def _sign_interview_model_context",
        "def _load_interview_model_context",
        # The binding must exist in the fragment; its VALUE is fixture
        # content owned by the app boundary (never named in reusable
        # code) and is locked by the fragment's byte hash instead.
        "default_public_profile_slug=",
        "jsonify(payload), status",
    ),
}


class FragmentError(ValueError):
    """The guarded fragment projection is missing, ambiguous, or stale."""


def extract_fragments(source_bytes):
    """Return {fragment_name: exact_content_bytes} or raise FragmentError.

    Content is the exact bytes between the newline that ends the opening
    marker line and the start of the closing marker line — executed bytes,
    never line numbers, so surrounding edits cannot shift the binding.
    """
    fragments = {}
    current_name = None
    current_start = None
    offset = 0
    for raw_line in source_bytes.splitlines(keepends=True):
        line = raw_line.decode("utf-8", errors="replace").strip()
        if line.startswith(FRAGMENT_OPEN.strip()) and FRAGMENT_OPEN.strip() != line:
            name = line[len(FRAGMENT_OPEN.strip()):].strip()
            if current_name is not None:
                raise FragmentError(
                    "nested or overlapping fragment marker: %s inside %s"
                    % (name, current_name)
                )
            if name not in EXPECTED_FRAGMENTS:
                raise FragmentError("unknown guarded fragment: %s" % name)
            if name in fragments:
                raise FragmentError("duplicate guarded fragment: %s" % name)
            current_name = name
            current_start = offset + len(raw_line)
        elif line.startswith(FRAGMENT_CLOSE.strip()) and FRAGMENT_CLOSE.strip() != line:
            name = line[len(FRAGMENT_CLOSE.strip()):].strip()
            if current_name is None:
                raise FragmentError(
                    "closing marker without an open fragment: %s" % name
                )
            if name != current_name:
                raise FragmentError(
                    "mismatched fragment markers: %s closed by %s"
                    % (current_name, name)
                )
            fragments[current_name] = source_bytes[current_start:offset]
            current_name = None
            current_start = None
        offset += len(raw_line)
    if current_name is not None:
        raise FragmentError("unterminated guarded fragment: %s" % current_name)

    missing = set(EXPECTED_FRAGMENTS) - set(fragments)
    if missing:
        raise FragmentError(
            "missing guarded fragments: %s" % sorted(missing)
        )
    for name, expected_symbols in EXPECTED_FRAGMENTS.items():
        content = fragments[name].decode("utf-8", errors="replace")
        for symbol in expected_symbols:
            if symbol not in content:
                raise FragmentError(
                    "fragment %s no longer contains its expected executed "
                    "symbol: %s" % (name, symbol)
                )
    return fragments


def fragment_entry_path(base_path, name):
    return "%s#fragment=%s" % (base_path, name)


def split_fragment_path(entry_path):
    """Return (base_path, fragment_name) or (entry_path, None)."""
    if "#fragment=" in entry_path:
        base_path, name = entry_path.split("#fragment=", 1)
        return base_path, name
    return entry_path, None
