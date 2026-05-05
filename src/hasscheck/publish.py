"""Opt-in client for uploading HassCheck reports to a hosted service.

See ADR 0008 (publish contract) and docs/architecture/publish-handshake.md.
The CLI never publishes by default — `hasscheck publish` must be invoked
explicitly, or `emit-publish: 'true'` set on the composite GitHub Action.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from hasscheck import __version__
from hasscheck.checker import run_check
from hasscheck.config import HassCheckConfig

DEFAULT_ENDPOINT = "https://hasscheck.io"
ENDPOINT_ENV_VAR = "HASSCHECK_PUBLISH_ENDPOINT"
OIDC_TOKEN_ENV_VAR = "HASSCHECK_OIDC_TOKEN"
USER_AGENT = f"hasscheck/{__version__}"
DEFAULT_TIMEOUT_SECONDS = 30.0


class PublishError(Exception):
    """Base error raised when the publish flow cannot complete."""


class MissingTokenError(PublishError):
    """Raised when no OIDC token is available."""


class PublishRequestError(PublishError):
    """Raised when the server returns a non-2xx response."""

    def __init__(self, status_code: int, body: dict[str, Any] | str):
        self.status_code = status_code
        self.body = body
        super().__init__(self._format())

    def _format(self) -> str:
        if isinstance(self.body, dict):
            error = self.body.get("error") or "unknown"
            message = self.body.get("message") or ""
            return f"HTTP {self.status_code} {error}: {message}".rstrip(": ")
        return f"HTTP {self.status_code}: {self.body}"


@dataclass(frozen=True)
class PublishResult:
    report_id: str
    report_url: str
    badge_url_template: str
    schema_version: str


def resolve_endpoint_with_source(
    cli_value: str | None,
    *,
    config: HassCheckConfig | None = None,
) -> tuple[str, str]:
    """Resolve publish endpoint and return (endpoint, source_label).

    Precedence: CLI flag > $HASSCHECK_PUBLISH_ENDPOINT > config.publish.endpoint > DEFAULT_ENDPOINT.
    """
    if cli_value:
        return cli_value.rstrip("/"), "--to flag"
    env_value = os.environ.get(ENDPOINT_ENV_VAR)
    if env_value:
        return env_value.rstrip("/"), f"${ENDPOINT_ENV_VAR}"
    if config is not None and config.publish is not None and config.publish.endpoint:
        return config.publish.endpoint.rstrip("/"), "hasscheck.yaml"
    return DEFAULT_ENDPOINT, "default"


def resolve_endpoint(
    cli_value: str | None,
    *,
    config: HassCheckConfig | None = None,
) -> str:
    """Resolve publish endpoint.

    Precedence: CLI flag > $HASSCHECK_PUBLISH_ENDPOINT > config.publish.endpoint > DEFAULT_ENDPOINT.
    """
    endpoint, _ = resolve_endpoint_with_source(cli_value, config=config)
    return endpoint


def resolve_oidc_token(cli_value: str | None) -> str:
    """Resolve OIDC token with precedence: CLI flag > env var. Raises if absent."""
    if cli_value:
        return cli_value
    env_value = os.environ.get(OIDC_TOKEN_ENV_VAR)
    if env_value:
        return env_value
    raise MissingTokenError(
        "no OIDC token available — pass --oidc-token or set "
        f"{OIDC_TOKEN_ENV_VAR}. Publishing requires GitHub Actions OIDC."
    )


def detect_oidc_token(cli_value: str | None) -> tuple[str | None, str]:
    """Detect OIDC token presence and source without raising.

    Returns (token_or_None, source_label). Safe to call in dry-run contexts.
    """
    if cli_value:
        return cli_value, "--oidc-token flag"
    env_value = os.environ.get(OIDC_TOKEN_ENV_VAR)
    if env_value:
        return env_value, f"${OIDC_TOKEN_ENV_VAR}"
    return None, "not detected"


def _headers(oidc_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {oidc_token}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }


def _parse_body(response: httpx.Response) -> dict[str, Any] | str:
    try:
        parsed = response.json()
    except json.JSONDecodeError:
        return response.text
    if not isinstance(parsed, dict):
        return response.text
    return parsed


def _raise_for_status(response: httpx.Response) -> None:
    if 200 <= response.status_code < 300:
        return
    raise PublishRequestError(response.status_code, _parse_body(response))


def publish_report(
    path: Path,
    *,
    endpoint: str,
    oidc_token: str,
    config: HassCheckConfig | None = None,
    no_config: bool = False,
    client: httpx.Client | None = None,
    ha_version: str | None = None,
) -> PublishResult:
    """Run a check and POST the resulting JSON report to the hosted service."""
    report = run_check(path, config=config, no_config=no_config, ha_version=ha_version)
    body = report.to_json_dict()

    owns_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = client.post(
            f"{endpoint}/api/reports",
            json=body,
            headers=_headers(oidc_token),
        )
    finally:
        if owns_client:
            client.close()

    _raise_for_status(response)

    parsed = _parse_body(response)
    if not isinstance(parsed, dict):
        raise PublishRequestError(response.status_code, parsed)

    return PublishResult(
        report_id=str(parsed.get("report_id", "")),
        report_url=str(parsed.get("report_url", "")),
        badge_url_template=str(parsed.get("badge_url_template", "")),
        schema_version=str(parsed.get("schema_version", "")),
    )


def withdraw_report(
    *,
    endpoint: str,
    oidc_token: str,
    owner: str,
    repo: str,
    report_id: str | None = None,
    client: httpx.Client | None = None,
) -> None:
    """Delete one report (when report_id is given) or all reports for a slug."""
    if report_id is not None:
        url = f"{endpoint}/api/projects/{owner}/{repo}/reports/{report_id}"
    else:
        url = f"{endpoint}/api/projects/{owner}/{repo}"

    owns_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = client.delete(url, headers=_headers(oidc_token))
    finally:
        if owns_client:
            client.close()

    _raise_for_status(response)


def split_slug(slug: str) -> tuple[str, str]:
    """Split `owner/repo` into `(owner, repo)` or raise PublishError."""
    parts = slug.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise PublishError(f"invalid slug '{slug}'; expected 'owner/repo'")
    return parts[0], parts[1]
