"""Tests for the read-only Azure DevOps adapter (Control Room Tier 1).

Coverage:
* Configuration — all four env vars required; any one missing => not_configured
  with zero network calls.
* Live fetch — mocked HTTP 200s parse into normalized collections; one
  endpoint failing never blanks the others.
* Caching — a call within the TTL reuses the cache without a new network
  call; a failed refresh with a recent cache serves it as ``stale``; an
  old-enough failure with nothing fresh renders ``unavailable``.
* Credentials — a 401/403 is reported as a credential problem without ever
  leaking the response body or the PAT value anywhere in the result.
"""

import json
import unittest
import urllib.error
from unittest.mock import patch

import services.azure_devops_read as ado


FULL_CONFIG = {
    "PEERSLATE_ADO_ORG_URL": "https://dev.azure.com/peerslate19",
    "PEERSLATE_ADO_PROJECT": "portfolio-site",
    "PEERSLATE_ADO_REPO": "portfolio-site",
    "PEERSLATE_ADO_READ_PAT": "super-secret-pat-value",
}

BRANCHES_PAYLOAD = {
    "value": [
        {"name": "refs/heads/main", "objectId": "a" * 40},
        {"name": "refs/heads/work/x", "objectId": "b" * 40},
    ]
}
COMMITS_PAYLOAD = {
    "value": [
        {
            "commitId": "a" * 40,
            "author": {"name": "Pete Carter", "date": "2026-07-19T10:00:00Z"},
            "comment": "Merge pull request 74\n\nmore detail",
        }
    ]
}
ACTIVE_PR_PAYLOAD = {
    "value": [
        {
            "pullRequestId": 75,
            "title": "Add feature",
            "sourceRefName": "refs/heads/work/x",
            "targetRefName": "refs/heads/main",
            "createdBy": {"displayName": "Pete Carter"},
            "creationDate": "2026-07-19T09:00:00Z",
            "status": "active",
        }
    ]
}
COMPLETED_PR_PAYLOAD = {"value": []}
BUILDS_PAYLOAD = {
    "value": [
        {
            "id": 112,
            "buildNumber": "112",
            "status": "completed",
            "result": "succeeded",
            "sourceVersion": "a" * 40,
            "finishTime": "2026-07-19T10:05:00Z",
            "_links": {"web": {"href": "https://dev.azure.com/x/112"}},
        }
    ]
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _responses_for(url):
    if "/refs" in url:
        return _FakeResponse(BRANCHES_PAYLOAD)
    if "/commits" in url:
        return _FakeResponse(COMMITS_PAYLOAD)
    if "status=active" in url:
        return _FakeResponse(ACTIVE_PR_PAYLOAD)
    if "status=completed" in url:
        return _FakeResponse(COMPLETED_PR_PAYLOAD)
    if "/builds" in url:
        return _FakeResponse(BUILDS_PAYLOAD)
    raise AssertionError(f"unexpected URL requested: {url}")


def _success_side_effect(request, timeout=None):
    return _responses_for(request.full_url)


class AzureDevOpsConfigTests(unittest.TestCase):
    def setUp(self):
        ado.reset_cache()

    def test_all_vars_present_is_configured(self):
        self.assertTrue(ado.is_configured(FULL_CONFIG))

    def test_any_missing_var_is_not_configured(self):
        for missing_key in FULL_CONFIG:
            partial = dict(FULL_CONFIG)
            partial[missing_key] = ""
            self.assertFalse(ado.is_configured(partial), missing_key)

    def test_org_url_must_be_an_absolute_https_url(self):
        for unsafe_url in ("javascript:alert(1)", "http://dev.azure.com/example", "dev.azure.com/example"):
            config = dict(FULL_CONFIG, PEERSLATE_ADO_ORG_URL=unsafe_url)
            self.assertFalse(ado.is_configured(config), unsafe_url)

    @patch("urllib.request.urlopen")
    def test_not_configured_makes_zero_network_calls(self, urlopen):
        result = ado.fetch_repository_activity({})
        self.assertEqual(result["status"], ado.NOT_CONFIGURED)
        urlopen.assert_not_called()
        for key in (
            "branches", "commits_main", "prs_active",
            "prs_completed", "pipeline_runs",
        ):
            self.assertEqual(result[key]["items"], [])


class AzureDevOpsFetchTests(unittest.TestCase):
    def setUp(self):
        ado.reset_cache()

    def test_successful_fetch_parses_all_collections(self):
        with patch("urllib.request.urlopen", side_effect=_success_side_effect):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(result["status"], ado.OK)
        self.assertEqual(result["branches"]["items"][0]["name"], "main")
        self.assertEqual(
            result["commits_main"]["items"][0]["commit_full"], "a" * 40
        )
        self.assertEqual(result["commits_main"]["items"][0]["subject"],
                          "Merge pull request 74")
        self.assertEqual(result["prs_active"]["items"][0]["id"], 75)
        self.assertEqual(
            result["prs_active"]["items"][0]["link"],
            "https://dev.azure.com/peerslate19/portfolio-site/_git/"
            "portfolio-site/pullrequest/75",
        )
        self.assertEqual(result["prs_completed"]["items"], [])
        self.assertEqual(
            result["pipeline_runs"]["items"][0]["result"], "succeeded"
        )
        self.assertIsNotNone(result["fetched_at"])

    def test_unsafe_pipeline_link_is_not_returned_to_the_client(self):
        payload = json.loads(json.dumps(BUILDS_PAYLOAD))
        payload["value"][0]["_links"]["web"]["href"] = "javascript:alert(1)"

        def side_effect(request, timeout=None):
            if "/builds" in request.full_url:
                return _FakeResponse(payload)
            return _responses_for(request.full_url)

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertIsNone(result["pipeline_runs"]["items"][0]["link"])

    def test_one_endpoint_failing_does_not_blank_the_others(self):
        def side_effect(request, timeout=None):
            if "/builds" in request.full_url:
                raise urllib.error.URLError("network down")
            return _responses_for(request.full_url)

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(result["status"], ado.OK)
        self.assertEqual(result["pipeline_runs"]["status"], "network_error")
        self.assertEqual(result["pipeline_runs"]["items"], [])
        self.assertEqual(result["branches"]["status"], ado.OK)
        self.assertGreater(len(result["branches"]["items"]), 0)

    def test_all_endpoints_failing_with_no_cache_is_unavailable(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("network down"),
        ):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(result["status"], ado.UNAVAILABLE)
        self.assertEqual(result["branches"]["items"], [])

    def test_credential_invalid_reported_without_leaking_pat_or_body(self):
        http_error = urllib.error.HTTPError(
            url="https://example.invalid", code=401, msg="Unauthorized",
            hdrs=None, fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(result["status"], ado.UNAVAILABLE)
        self.assertIn("credential", result["note"].lower())
        serialized = json.dumps(result)
        self.assertNotIn(FULL_CONFIG["PEERSLATE_ADO_READ_PAT"], serialized)

    def test_pat_never_appears_in_a_successful_result(self):
        with patch("urllib.request.urlopen", side_effect=_success_side_effect):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        serialized = json.dumps(result)
        self.assertNotIn(FULL_CONFIG["PEERSLATE_ADO_READ_PAT"], serialized)


class AzureDevOpsCacheTests(unittest.TestCase):
    def setUp(self):
        ado.reset_cache()

    def test_cache_hit_within_ttl_avoids_a_second_network_call(self):
        with patch(
            "urllib.request.urlopen", side_effect=_success_side_effect
        ) as urlopen:
            ado.fetch_repository_activity(FULL_CONFIG)
            calls_after_first = urlopen.call_count
            second = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(urlopen.call_count, calls_after_first)
        self.assertEqual(second["status"], ado.OK)

    def test_stale_cache_served_when_refresh_fails_but_recent(self):
        with patch("urllib.request.urlopen", side_effect=_success_side_effect):
            ado.fetch_repository_activity(FULL_CONFIG)

        elapsed = ado._cache["monotonic_fetched"] + ado.CACHE_TTL_SECONDS + 1
        with patch.object(ado.time, "monotonic", return_value=elapsed), patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(result["status"], ado.STALE)
        self.assertGreater(len(result["branches"]["items"]), 0)

    def test_old_cache_beyond_stale_window_is_unavailable(self):
        with patch("urllib.request.urlopen", side_effect=_success_side_effect):
            ado.fetch_repository_activity(FULL_CONFIG)

        elapsed = (
            ado._cache["monotonic_fetched"]
            + ado.STALE_CACHE_MAX_AGE_SECONDS
            + 1
        )
        with patch.object(ado.time, "monotonic", return_value=elapsed), patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            result = ado.fetch_repository_activity(FULL_CONFIG)
        self.assertEqual(result["status"], ado.UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
