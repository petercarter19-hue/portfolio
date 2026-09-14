#!/usr/bin/env python3
"""Read Azure Cost Management and emit a privacy-safe continuity report."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.azure_startup_qualification import (
    build_report,
    cost_rows_from_query,
    planned_budget,
)

COST_QUERY_API_VERSION = "2025-03-01"
COST_DETAILS_API_VERSION = "2025-03-01"
AZURE_MANAGEMENT_HOST = "management.azure.com"
MAX_COST_DETAILS_POLL_ATTEMPTS = 16
MAX_COST_DETAILS_POLL_WAIT_SECONDS = 900
MAX_COST_DETAILS_CONNECT_SECONDS = 10
MAX_COST_DETAILS_AUTH_SECONDS = 10
MAX_COST_DETAILS_CONCURRENT_REPORTS = 4
MAX_COST_DETAILS_BLOBS = 4
MAX_COST_DETAILS_BYTES = 20_000_000
MAX_COST_DETAILS_ROWS = 50_000
MAX_JSON_RESPONSE_BYTES = 1_000_000


class AzureBillingReadError(RuntimeError):
    """A privacy-safe Azure billing read failure."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class LiveQueryResult:
    payload: dict[str, Any]
    source: str
    fallback_reason: str | None = None


@dataclass(frozen=True)
class HttpJsonResponse:
    status: int
    payload: dict[str, Any] | None
    headers: dict[str, str]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate five- and seven-workload continuity from Azure ActualCost data."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--input", type=Path, help="Offline Cost Management response JSON"
    )
    source.add_argument(
        "--subscription-id",
        help="Subscription UUID for a read-only az rest Cost Management query",
    )
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--days", type=int, default=75)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--require-qualified-latest-day", action="store_true")
    parser.add_argument("--require-five-qualified-latest-day", action="store_true")
    return parser.parse_args()


def _query_body(start: date, end: date) -> dict[str, Any]:
    return {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        },
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"CostUSD": {"name": "CostUSD", "function": "Sum"}},
            "grouping": [
                {"type": "Dimension", "name": "ServiceName"},
                {"type": "Dimension", "name": "ResourceId"},
            ],
        },
    }


def _validated_subscription_id(subscription_id: str) -> str:
    try:
        parsed_subscription = UUID(subscription_id)
    except (ValueError, AttributeError) as error:
        raise RuntimeError("Azure subscription identifier is invalid") from error
    if str(parsed_subscription) != subscription_id.casefold():
        raise RuntimeError("Azure subscription identifier is not canonical")
    return str(parsed_subscription)


def _az_rest_json(command: list[str], *, timeout: int, label: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise AzureBillingReadError(
            "timeout", f"Azure {label} query timed out"
        ) from error
    if completed.returncode != 0:
        stderr = completed.stderr.casefold()
        code = (
            "rate_limited"
            if "too many requests" in stderr or "429" in stderr
            else "unavailable"
        )
        raise AzureBillingReadError(code, f"Azure {label} query failed")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AzureBillingReadError(
            "invalid_response", f"Azure {label} returned invalid JSON"
        ) from error
    if not isinstance(result, dict):
        raise AzureBillingReadError(
            "invalid_response", f"Azure {label} returned an invalid document"
        )
    return result


def _cost_management_query(
    subscription_id: str, start: date, end: date
) -> dict[str, Any]:
    url = (
        "https://management.azure.com/subscriptions/"
        f"{subscription_id}/providers/Microsoft.CostManagement/query"
        f"?api-version={COST_QUERY_API_VERSION}"
    )
    return _az_rest_json(
        [
            "az",
            "rest",
            "--method",
            "post",
            "--url",
            url,
            "--body",
            json.dumps(_query_body(start, end), separators=(",", ":")),
            "--output",
            "json",
            "--only-show-errors",
        ],
        timeout=120,
        label="Cost Management",
    )


def _cost_management_client():
    try:
        from azure.identity import AzureCliCredential
        from azure.mgmt.costmanagement import CostManagementClient
    except ImportError as error:
        raise AzureBillingReadError(
            "unavailable", "Azure Cost Details client is unavailable"
        ) from error
    credential = AzureCliCredential(process_timeout=MAX_COST_DETAILS_AUTH_SECONDS)
    client = CostManagementClient(credential, polling_interval=5)
    return credential, client


def _cost_details_http_response(
    client: Any,
    *,
    url: str,
    method: str,
    body: dict[str, Any] | None,
    timeout_seconds: float,
) -> HttpJsonResponse:
    try:
        from azure.core.rest import HttpRequest
        from azure.core.exceptions import (
            ServiceRequestTimeoutError,
            ServiceResponseTimeoutError,
        )
    except ImportError as error:
        raise AzureBillingReadError(
            "unavailable", "Azure Cost Details client is unavailable"
        ) from error
    request = HttpRequest(
        method,
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=body,
    )
    if timeout_seconds <= 0:
        raise AzureBillingReadError(
            "timeout", "Azure Cost Details report generation timed out"
        )
    try:
        response = client.send_request(
            request,
            stream=False,
            permit_redirects=False,
            connection_timeout=min(MAX_COST_DETAILS_CONNECT_SECONDS, timeout_seconds),
            read_timeout=timeout_seconds,
            retry_total=0,
            retry_connect=0,
            retry_read=0,
            retry_status=0,
        )
        raw = response.read()
    except (ServiceRequestTimeoutError, ServiceResponseTimeoutError) as error:
        raise AzureBillingReadError(
            "timeout", "Azure Cost Details report generation timed out"
        ) from error
    except Exception as error:
        raise AzureBillingReadError(
            "unavailable", "Azure Cost Details query failed"
        ) from error
    if len(raw) > MAX_JSON_RESPONSE_BYTES:
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details response exceeded its size limit"
        )
    payload: dict[str, Any] | None = None
    if raw:
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as error:
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details returned invalid JSON"
            ) from error
        if not isinstance(decoded, dict):
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details returned an invalid document"
            )
        payload = decoded
    return HttpJsonResponse(
        status=response.status_code,
        payload=payload,
        headers={key.casefold(): value for key, value in response.headers.items()},
    )


def _retry_after_seconds(headers: dict[str, str]) -> int:
    raw = headers.get("retry-after") or headers.get(
        "x-ms-ratelimit-microsoft.consumption-retry-after"
    )
    try:
        value = int(raw) if raw is not None else 5
    except ValueError:
        value = 5
    return min(max(value, 1), 60)


def _validate_cost_details_poll_url(value: object, *, subscription_id: str) -> str:
    if not isinstance(value, str) or len(value) > 16_000:
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details polling URL is invalid"
        )
    parsed = urlsplit(value)
    prefix = (
        f"/subscriptions/{subscription_id}"
        "/providers/Microsoft.CostManagement/"
    )
    suffix = (
        parsed.path[len(prefix) :]
        if parsed.path.casefold().startswith(prefix.casefold())
        else ""
    )
    match = re.fullmatch(
        r"(?:costDetailsOperationResults|costDetailsOperationStatus)/([0-9A-Fa-f-]{36})",
        suffix,
    )
    query = parse_qs(parsed.query, keep_blank_values=True)
    try:
        operation_id_valid = bool(match) and (
            str(UUID(match.group(1))) == match.group(1).casefold()
        )
    except (ValueError, AttributeError):
        operation_id_valid = False
    allowed_query_keys = {"api-version", "c", "h", "s", "t"}
    signed_values_valid = all(
        len(values) == 1 and values[0] and len(values[0]) <= 12_000
        for key, values in query.items()
        if key != "api-version"
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != AZURE_MANAGEMENT_HOST
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or not operation_id_valid
        or query.get("api-version") != [COST_DETAILS_API_VERSION]
        or set(query) - allowed_query_keys
        or not signed_values_valid
    ):
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details polling URL is invalid"
        )
    return value


def _monthly_ranges(start: date, end: date) -> tuple[tuple[date, date], ...]:
    ranges: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        next_month = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
        range_end = min(end, next_month - timedelta(days=1))
        ranges.append((cursor, range_end))
        cursor = range_end + timedelta(days=1)
    return tuple(ranges)


def _cost_details_report(
    subscription_id: str, start: date, end: date
) -> dict[str, Any] | None:
    credential, client = _cost_management_client()
    url = (
        f"https://{AZURE_MANAGEMENT_HOST}/subscriptions/{subscription_id}"
        "/providers/Microsoft.CostManagement/generateCostDetailsReport"
        f"?api-version={COST_DETAILS_API_VERSION}"
    )
    method = "POST"
    body: dict[str, Any] | None = {
        "metric": "ActualCost",
        "timePeriod": {"start": start.isoformat(), "end": end.isoformat()},
    }
    deadline = time.monotonic() + MAX_COST_DETAILS_POLL_WAIT_SECONDS
    try:
        for attempt in range(MAX_COST_DETAILS_POLL_ATTEMPTS):
            remaining = deadline - time.monotonic()
            reserved = MAX_COST_DETAILS_AUTH_SECONDS + MAX_COST_DETAILS_CONNECT_SECONDS
            if remaining <= reserved:
                break
            response = _cost_details_http_response(
                client,
                url=url,
                method=method,
                body=body,
                timeout_seconds=remaining - reserved,
            )
            if response.status == 204:
                return None
            if response.status == 200:
                if response.payload is None:
                    raise AzureBillingReadError(
                        "invalid_response",
                        "Azure Cost Details returned an empty result",
                    )
                return response.payload
            if response.status not in {202, 429, 503}:
                raise AzureBillingReadError(
                    "invalid_response",
                    "Azure Cost Details returned an invalid status",
                )
            if response.status == 202:
                location = response.headers.get("location")
                if location:
                    url = _validate_cost_details_poll_url(
                        location, subscription_id=subscription_id
                    )
                elif method == "POST":
                    raise AzureBillingReadError(
                        "invalid_response",
                        "Azure Cost Details omitted its polling URL",
                    )
                method = "GET"
                body = None
            if attempt == MAX_COST_DETAILS_POLL_ATTEMPTS - 1:
                break
            delay = _retry_after_seconds(response.headers)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(delay, remaining))
        raise AzureBillingReadError(
            "timeout", "Azure Cost Details report generation timed out"
        )
    finally:
        client.close()
        credential.close()


def _validated_cost_details_blobs(
    report: dict[str, Any], *, subscription_id: str, start: date, end: date
) -> tuple[tuple[str, int, bool], ...]:
    status = report.get("status")
    if status == "NoDataFound":
        return ()
    manifest = report.get("manifest")
    if status != "Completed" or not isinstance(manifest, dict):
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details report was not completed"
        )
    context = manifest.get("requestContext")
    request_body = context.get("requestBody") if isinstance(context, dict) else None
    period = request_body.get("timePeriod") if isinstance(request_body, dict) else None
    request_scope = context.get("requestScope") if isinstance(context, dict) else None
    expected_scope = f"subscriptions/{subscription_id}"
    if (
        not isinstance(request_body, dict)
        or request_body.get("metric") != "ActualCost"
        or period != {"start": start.isoformat(), "end": end.isoformat()}
        or not isinstance(request_scope, str)
        or request_scope.lstrip("/").casefold() != expected_scope.casefold()
        or manifest.get("dataFormat") != "Csv"
        or not isinstance(manifest.get("compressData"), bool)
    ):
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details manifest is invalid"
        )
    blobs = manifest.get("blobs")
    if (
        not isinstance(blobs, list)
        or not 1 <= len(blobs) <= MAX_COST_DETAILS_BLOBS
        or manifest.get("blobCount") != len(blobs)
    ):
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details manifest is invalid"
        )
    validated: list[tuple[str, int, bool]] = []
    total_bytes = 0
    for blob in blobs:
        if not isinstance(blob, dict):
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details manifest is invalid"
            )
        link = blob.get("blobLink")
        byte_count = blob.get("byteCount")
        parsed = urlsplit(link) if isinstance(link, str) else None
        if (
            parsed is None
            or parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".blob.core.windows.net")
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or not parse_qs(parsed.query).get("sig")
            or not isinstance(byte_count, int)
            or byte_count < 1
        ):
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details blob manifest is invalid"
            )
        total_bytes += byte_count
        validated.append((link, byte_count, manifest["compressData"]))
    if total_bytes > MAX_COST_DETAILS_BYTES or manifest.get("byteCount") != total_bytes:
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details report exceeded its size limit"
        )
    return tuple(validated)


def _download_cost_details_blob(link: str, byte_count: int, compressed: bool) -> str:
    try:
        import requests
    except ImportError as error:
        raise AzureBillingReadError(
            "unavailable", "Azure Cost Details download client is unavailable"
        ) from error
    try:
        with requests.get(
            link,
            allow_redirects=False,
            stream=True,
            timeout=(10, 120),
            headers={"Accept": "text/csv"},
        ) as response:
            if response.status_code != 200 or response.url != link:
                raise AzureBillingReadError(
                    "invalid_response",
                    "Azure Cost Details report download was redirected",
                )
            chunks: list[bytes] = []
            downloaded = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > MAX_COST_DETAILS_BYTES:
                    raise AzureBillingReadError(
                        "invalid_response",
                        "Azure Cost Details report exceeded its size limit",
                    )
                chunks.append(chunk)
    except AzureBillingReadError:
        raise
    except requests.RequestException as error:
        raise AzureBillingReadError(
            "unavailable", "Azure Cost Details report download failed"
        ) from error
    raw = b"".join(chunks)
    if len(raw) != byte_count:
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details report size is invalid"
        )
    if compressed:
        try:
            raw = gzip.decompress(raw)
        except (OSError, EOFError) as error:
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details compression is invalid"
            ) from error
        if len(raw) > MAX_COST_DETAILS_BYTES:
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details report exceeded its size limit"
            )
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details report encoding is invalid"
        ) from error


def _cost_details_csv_rows(
    content: str, *, start: date, end: date
) -> list[list[object]]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details CSV has no header"
        )
    names = {name.casefold(): name for name in reader.fieldnames}

    def value(row: dict[str, str], *candidates: str) -> str | None:
        for candidate in candidates:
            name = names.get(candidate.casefold())
            if name is not None and row.get(name) not in {None, ""}:
                return row[name]
        return None

    rows: list[list[object]] = []
    for item in reader:
        charge_type = value(item, "ChargeType")
        if charge_type != "Usage":
            continue
        day_value = value(item, "Date", "UsageDateTime", "UsageDate")
        try:
            usage_day = date.fromisoformat((day_value or "")[:10])
        except ValueError as error:
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details CSV has an invalid date"
            ) from error
        if usage_day < start or usage_day > end:
            continue
        service = value(item, "MeterCategory")
        resource = value(item, "ResourceId", "InstanceId", "InstanceName") or ""
        cost = value(item, "CostInUSD")
        if cost is None:
            cost = value(item, "CostInBillingCurrency", "PreTaxCost", "Cost")
            currency = value(item, "BillingCurrency", "BillingCurrencyCode", "Currency")
            if currency != "USD":
                raise AzureBillingReadError(
                    "invalid_response", "Azure Cost Details CSV is not in USD"
                )
        if not service or cost is None:
            raise AzureBillingReadError(
                "invalid_response", "Azure Cost Details CSV is missing required fields"
            )
        rows.append([cost, usage_day.isoformat(), service, resource, "USD"])
        if len(rows) > MAX_COST_DETAILS_ROWS:
            raise AzureBillingReadError(
                "row_limit", "Azure Cost Details exceeded the bounded row limit"
            )
    return rows


def _cost_details_query(
    subscription_id: str, start: date, end: date
) -> dict[str, Any]:
    rows: list[list[object]] = []
    downloads: list[tuple[date, date, str, int, bool]] = []
    total_blob_bytes = 0
    ranges = _monthly_ranges(start, end)
    with ThreadPoolExecutor(
        max_workers=min(MAX_COST_DETAILS_CONCURRENT_REPORTS, len(ranges))
    ) as executor:
        reports = executor.map(
            lambda period: _cost_details_report(
                subscription_id, period[0], period[1]
            ),
            ranges,
        )
        period_reports = zip(ranges, reports, strict=True)
        completed_reports = tuple(period_reports)
    for (range_start, range_end), report in completed_reports:
        if report is None:
            continue
        blobs = _validated_cost_details_blobs(
            report,
            subscription_id=subscription_id,
            start=range_start,
            end=range_end,
        )
        for link, byte_count, compressed in blobs:
            total_blob_bytes += byte_count
            downloads.append(
                (range_start, range_end, link, byte_count, compressed)
            )
    if (
        len(downloads) > MAX_COST_DETAILS_BLOBS
        or total_blob_bytes > MAX_COST_DETAILS_BYTES
    ):
        raise AzureBillingReadError(
            "invalid_response", "Azure Cost Details fallback exceeded its global limit"
        )
    for range_start, range_end, link, byte_count, compressed in downloads:
        rows.extend(
            _cost_details_csv_rows(
                _download_cost_details_blob(link, byte_count, compressed),
                start=range_start,
                end=range_end,
            )
        )
        if len(rows) > MAX_COST_DETAILS_ROWS:
            raise AzureBillingReadError(
                "row_limit", "Azure Cost Details exceeded the bounded row limit"
            )
    return {
        "properties": {
            "columns": [
                {"name": "CostUSD", "type": "Number"},
                {"name": "UsageDate", "type": "String"},
                {"name": "ServiceName", "type": "String"},
                {"name": "ResourceId", "type": "String"},
                {"name": "Currency", "type": "String"},
            ],
            "rows": rows,
        }
    }


def _live_query(subscription_id: str, start: date, end: date) -> LiveQueryResult:
    subscription_id = _validated_subscription_id(subscription_id)
    try:
        return LiveQueryResult(
            payload=_cost_management_query(subscription_id, start, end),
            source="Azure Cost Management ActualCost estimate",
        )
    except AzureBillingReadError as error:
        if error.code != "rate_limited":
            raise
        return LiveQueryResult(
            payload=_cost_details_query(subscription_id, start, end),
            source="Azure Cost Management Cost Details ActualCost fallback",
            fallback_reason="cost_management_rate_limited",
        )


def main() -> int:
    args = _arguments()
    now = datetime.now(timezone.utc)
    if args.days < 1 or args.days > 366:
        raise SystemExit("--days must be between 1 and 366")
    start = args.start or now.date() - timedelta(days=args.days)
    end = args.end or now.date()
    if end < start:
        raise SystemExit("--end cannot be before --start")

    if args.input:
        try:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"status unavailable: {error}", file=sys.stderr)
            return 2
    else:
        try:
            live_result = _live_query(args.subscription_id, start, end)
            payload = live_result.payload
        except (RuntimeError, TypeError) as error:
            print(str(error), file=sys.stderr)
            return 2

    try:
        report = build_report(cost_rows_from_query(payload), generated_at=now)
    except (TypeError, ValueError) as error:
        print(f"status unavailable: {error}", file=sys.stderr)
        return 2
    output = report.as_privacy_safe_dict()
    if not args.input:
        output["status_source"] = live_result.source
        if live_result.fallback_reason:
            output["fallback_reason"] = live_result.fallback_reason
    output["budget"] = planned_budget()
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    if args.require_qualified_latest_day:
        latest = output.get("latest_day")
        if not isinstance(latest, dict) or not latest.get("qualifies"):
            return 3
    if args.require_five_qualified_latest_day:
        latest = output.get("latest_day")
        if not isinstance(latest, dict) or not latest.get("qualifies_five"):
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
