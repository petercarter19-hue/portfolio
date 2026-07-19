"""Read-only Azure DevOps REST adapter (Control Room Tier 1).

Server-side only, standard library only (``urllib.request``) — no new project
dependency. Calls exactly five GET endpoints (branch refs, main-branch commits,
active pull requests, recently completed pull requests, pipeline runs) using a
Personal Access Token that Pete creates and configures himself. This module
never sees the token as anything but a request header it builds fresh each
call: it is never logged, never echoed back in an error, and never appears in
the returned data.

Least privilege: the PAT needs only "Code (Read)" and "Build (Read)" scopes.

Configuration is four environment variables, all optional:

    PEERSLATE_ADO_ORG_URL   e.g. https://dev.azure.com/peerslate19
    PEERSLATE_ADO_PROJECT   e.g. portfolio-site
    PEERSLATE_ADO_REPO      e.g. portfolio-site
    PEERSLATE_ADO_READ_PAT  Personal Access Token (Code: Read, Build: Read)

Any one missing => the whole tier reports ``not_configured``. A fetch failure
never raises past this module and never blanks out a previously good result
without saying so: it degrades to ``stale`` (serving a recent cache) or
``unavailable`` (nothing usable), per ``fetch_repository_activity``.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

API_VERSION = "7.1"
TIMEOUT_SECONDS = 5
CACHE_TTL_SECONDS = 60
STALE_CACHE_MAX_AGE_SECONDS = 600  # 10 minutes

NOT_CONFIGURED = "not_configured"
OK = "ok"
UNAVAILABLE = "unavailable"
STALE = "stale"

# Per-call outcome reasons (never include response bodies or credentials).
_CREDENTIAL_INVALID = "credential_invalid"
_HTTP_ERROR = "http_error"
_NETWORK_ERROR = "network_error"
_INVALID_RESPONSE = "invalid_response"

_CONFIG_KEYS = (
    "PEERSLATE_ADO_ORG_URL",
    "PEERSLATE_ADO_PROJECT",
    "PEERSLATE_ADO_REPO",
    "PEERSLATE_ADO_READ_PAT",
)

# Module-level, in-process TTL cache. Deliberately not shared across worker
# processes (see NFR-4: no new dependency, no Redis) — each gunicorn worker
# caches independently, which is an acceptable tradeoff for a 60s TTL.
_cache = {"monotonic_fetched": None, "fetched_at": None, "data": None}


def reset_cache():
    """Testing hook: clear the in-process cache so tests do not leak state
    into one another."""
    _cache["monotonic_fetched"] = None
    _cache["fetched_at"] = None
    _cache["data"] = None


def is_configured(app_config):
    return _config(app_config) is not None


def _config(app_config):
    values = {key: (app_config.get(key) or "").strip() for key in _CONFIG_KEYS}
    if not all(values.values()):
        return None
    org_url = values["PEERSLATE_ADO_ORG_URL"].rstrip("/")
    parsed_org_url = urlparse(org_url)
    if parsed_org_url.scheme != "https" or not parsed_org_url.netloc:
        return None
    return {
        "org_url": org_url,
        "project": values["PEERSLATE_ADO_PROJECT"],
        "repo": values["PEERSLATE_ADO_REPO"],
        "pat": values["PEERSLATE_ADO_READ_PAT"],
    }


def _auth_header(pat):
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _get(url, pat):
    """One GET call. Returns parsed JSON. Raises on any failure; the PAT is
    used only to build this request's Authorization header and is never
    included in the URL, so it cannot leak through an exception's message."""
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": _auth_header(pat),
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read()
    return json.loads(body.decode("utf-8"))


def _safe_get(url, pat):
    """Never raises. Returns ``(status, payload_or_None)``."""
    try:
        return OK, _get(url, pat)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            return _CREDENTIAL_INVALID, None
        return _HTTP_ERROR, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return _NETWORK_ERROR, None
    except (ValueError, TypeError):
        return _INVALID_RESPONSE, None


def _collection(status, payload, normalizer):
    """Normalize one endpoint's response into ``{"status", "items"}``. A
    normalizer error on one row is skipped, not fatal to the collection."""
    if status != OK:
        return {"status": status, "items": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
        return {"status": _INVALID_RESPONSE, "items": []}
    items = []
    for raw in payload["value"]:
        try:
            normalized = normalizer(raw)
        except Exception:
            continue
        if normalized is not None:
            items.append(normalized)
    return {"status": OK, "items": items}


def _strip_ref_prefix(name):
    prefix = "refs/heads/"
    return name[len(prefix):] if name.startswith(prefix) else name


def _normalize_branch(ref):
    object_id = ref.get("objectId") or ""
    return {
        "name": _strip_ref_prefix(ref.get("name") or ""),
        "commit": object_id[:7] or None,
        "commit_full": object_id or None,
    }


def _normalize_commit(commit):
    commit_id = commit.get("commitId") or ""
    author = commit.get("author") or {}
    comment = commit.get("comment") or ""
    return {
        "commit": commit_id[:7] or None,
        "commit_full": commit_id or None,
        "author": author.get("name"),
        "date": (author.get("date") or "")[:10] or None,
        "subject": comment.splitlines()[0] if comment else None,
    }


def _normalize_pr(pr, org_url, project, repo):
    pr_id = pr.get("pullRequestId")
    created_by = pr.get("createdBy") or {}
    return {
        "id": pr_id,
        "title": pr.get("title"),
        "source_branch": _strip_ref_prefix(pr.get("sourceRefName") or ""),
        "target_branch": _strip_ref_prefix(pr.get("targetRefName") or ""),
        "author": created_by.get("displayName"),
        "created": (pr.get("creationDate") or "")[:10] or None,
        "closed": (pr.get("closedDate") or "")[:10] or None,
        "status": pr.get("status"),
        "link": (
            f"{org_url}/{project}/_git/{repo}/pullrequest/{pr_id}"
            if pr_id is not None
            else None
        ),
    }


def _normalize_build(build):
    build_id = build.get("id")
    source_version = build.get("sourceVersion") or ""
    finish_time = build.get("finishTime") or ""
    web_link = ((build.get("_links") or {}).get("web") or {}).get("href")
    if web_link:
        parsed_link = urlparse(web_link)
        if parsed_link.scheme != "https" or not parsed_link.netloc:
            web_link = None
    return {
        "id": build_id,
        "build_number": build.get("buildNumber"),
        "status": build.get("status"),
        "result": build.get("result"),
        "commit": source_version[:7] or None,
        "commit_full": source_version or None,
        "finished": finish_time[:16].replace("T", " ") or None,
        "link": web_link,
    }


def _fetch_all(config):
    """Five independent GETs. Returns ``(collections_dict, any_succeeded)``.
    One endpoint's failure never blanks the others. Calls run concurrently so
    the cold-path wait is bounded by one endpoint timeout, not five in series."""
    org, project, repo, pat = (
        config["org_url"],
        config["project"],
        config["repo"],
        config["pat"],
    )
    repo_base = f"{org}/{quote(project)}/_apis/git/repositories/{quote(repo)}"
    build_base = f"{org}/{quote(project)}/_apis/build"

    endpoints = {
        "branches": f"{repo_base}/refs?filter=heads/&api-version={API_VERSION}",
        "commits": (
            f"{repo_base}/commits?searchCriteria.itemVersion.version=main"
            f"&searchCriteria.$top=30&api-version={API_VERSION}"
        ),
        "active": (
            f"{repo_base}/pullrequests?searchCriteria.status=active"
            f"&api-version={API_VERSION}"
        ),
        "completed": (
            f"{repo_base}/pullrequests?searchCriteria.status=completed"
            f"&searchCriteria.$top=10&api-version={API_VERSION}"
        ),
        "builds": f"{build_base}/builds?$top=10&api-version={API_VERSION}",
    }
    with ThreadPoolExecutor(max_workers=len(endpoints)) as executor:
        futures = {
            name: executor.submit(_safe_get, url, pat)
            for name, url in endpoints.items()
        }
        results = {name: future.result() for name, future in futures.items()}

    branches_status, branches_payload = results["branches"]
    commits_status, commits_payload = results["commits"]
    active_status, active_payload = results["active"]
    completed_status, completed_payload = results["completed"]
    builds_status, builds_payload = results["builds"]

    def _pr_normalizer(pr):
        return _normalize_pr(pr, org, project, repo)

    collections = {
        "branches": _collection(branches_status, branches_payload, _normalize_branch),
        "commits_main": _collection(commits_status, commits_payload, _normalize_commit),
        "prs_active": _collection(active_status, active_payload, _pr_normalizer),
        "prs_completed": _collection(
            completed_status, completed_payload, _pr_normalizer
        ),
        "pipeline_runs": _collection(builds_status, builds_payload, _normalize_build),
    }
    any_succeeded = any(item["status"] == OK for item in collections.values())
    return collections, any_succeeded


def _empty_collections(status):
    return {
        key: {"status": status, "items": []}
        for key in (
            "branches",
            "commits_main",
            "prs_active",
            "prs_completed",
            "pipeline_runs",
        )
    }


def fetch_repository_activity(app_config):
    """Live Azure DevOps activity: branches, main commits, PRs, pipeline runs.

    Returns a dict with a top-level ``status`` (``not_configured`` / ``ok`` /
    ``stale`` / ``unavailable``), ``fetched_at``, one entry per collection
    (each with its own ``status`` + ``items``), and an optional ``note``.
    ``app_config`` is the Flask app's config mapping, passed in rather than
    imported here so this module stays testable without an app context.
    """
    config = _config(app_config)
    if config is None:
        return {
            "status": NOT_CONFIGURED,
            "fetched_at": None,
            "note": (
                "Live Azure DevOps sync is not configured. Set "
                "PEERSLATE_ADO_ORG_URL, PEERSLATE_ADO_PROJECT, "
                "PEERSLATE_ADO_REPO, and PEERSLATE_ADO_READ_PAT to enable "
                "it (see docs/control-room/V2_LIVE_SYNC_SPEC.md)."
            ),
            **_empty_collections(NOT_CONFIGURED),
        }

    now = time.monotonic()
    if (
        _cache["data"] is not None
        and _cache["monotonic_fetched"] is not None
        and now - _cache["monotonic_fetched"] < CACHE_TTL_SECONDS
    ):
        return {
            "status": OK,
            "fetched_at": _cache["fetched_at"],
            "note": None,
            **_cache["data"],
        }

    collections, any_succeeded = _fetch_all(config)

    if any_succeeded:
        _cache["data"] = collections
        _cache["monotonic_fetched"] = now
        _cache["fetched_at"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        return {
            "status": OK,
            "fetched_at": _cache["fetched_at"],
            "note": None,
            **collections,
        }

    if _cache["data"] is not None and _cache["monotonic_fetched"] is not None:
        age = now - _cache["monotonic_fetched"]
        if age <= STALE_CACHE_MAX_AGE_SECONDS:
            return {
                "status": STALE,
                "fetched_at": _cache["fetched_at"],
                "note": (
                    "Azure DevOps could not be reached just now; showing "
                    "the last successful result."
                ),
                **_cache["data"],
            }

    reason_note = "Azure DevOps is unreachable, and no recent cached result is available."
    if any(
        status == _CREDENTIAL_INVALID
        for status in (
            collections["branches"]["status"],
            collections["commits_main"]["status"],
            collections["prs_active"]["status"],
            collections["prs_completed"]["status"],
            collections["pipeline_runs"]["status"],
        )
    ):
        reason_note = "The configured Azure DevOps credential is invalid or expired."

    return {
        "status": UNAVAILABLE,
        "fetched_at": None,
        "note": reason_note,
        **_empty_collections(UNAVAILABLE),
    }
