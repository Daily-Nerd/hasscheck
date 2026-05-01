import json
import os

import httpx
import pytest

from hasscheck.publish import (
    DEFAULT_ENDPOINT,
    ENDPOINT_ENV_VAR,
    OIDC_TOKEN_ENV_VAR,
    MissingTokenError,
    PublishError,
    PublishRequestError,
    publish_report,
    resolve_endpoint,
    resolve_oidc_token,
    split_slug,
    withdraw_report,
)

# ---------------------------------------------------------------------------
# Endpoint + token resolution


def test_resolve_endpoint_uses_cli_flag(monkeypatch):
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "https://env.example")
    assert resolve_endpoint("https://cli.example") == "https://cli.example"


def test_resolve_endpoint_falls_back_to_env(monkeypatch):
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "https://env.example/")
    assert resolve_endpoint(None) == "https://env.example"


def test_resolve_endpoint_default(monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    assert resolve_endpoint(None) == DEFAULT_ENDPOINT


def test_resolve_endpoint_strips_trailing_slash():
    assert resolve_endpoint("https://example.com/") == "https://example.com"


# ---------------------------------------------------------------------------
# Config-tier endpoint resolution (v0.8)


def _make_config_with_endpoint(endpoint: str | None):
    """Build a HassCheckConfig with publish.endpoint set."""
    from hasscheck.config import HassCheckConfig, PublishConfig

    return HassCheckConfig(publish=PublishConfig(endpoint=endpoint))


def test_resolve_endpoint_config_tier_wins_when_cli_and_env_absent(monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    cfg = _make_config_with_endpoint("https://cfg.example")
    result = resolve_endpoint(None, config=cfg)
    assert result == "https://cfg.example"


def test_resolve_endpoint_env_beats_config_tier(monkeypatch):
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "https://env.example")
    cfg = _make_config_with_endpoint("https://cfg.example")
    result = resolve_endpoint(None, config=cfg)
    assert result == "https://env.example"


def test_resolve_endpoint_cli_beats_all_tiers(monkeypatch):
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "https://env.example")
    cfg = _make_config_with_endpoint("https://cfg.example")
    result = resolve_endpoint("https://cli.example/", config=cfg)
    assert result == "https://cli.example"


def test_resolve_endpoint_default_when_all_tiers_absent(monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    result = resolve_endpoint(None, config=None)
    assert result == DEFAULT_ENDPOINT


def test_resolve_endpoint_config_none_skips_without_error(monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    result = resolve_endpoint(None, config=None)
    assert result == DEFAULT_ENDPOINT


def test_resolve_endpoint_config_publish_none_skips_without_error(monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    from hasscheck.config import HassCheckConfig

    cfg = HassCheckConfig()  # no publish block → publish is None
    result = resolve_endpoint(None, config=cfg)
    assert result == DEFAULT_ENDPOINT


def test_resolve_endpoint_config_tier_strips_trailing_slash(monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    cfg = _make_config_with_endpoint("https://cfg.example/")
    result = resolve_endpoint(None, config=cfg)
    assert result == "https://cfg.example"


def test_resolve_oidc_token_from_cli(monkeypatch):
    monkeypatch.delenv(OIDC_TOKEN_ENV_VAR, raising=False)
    assert resolve_oidc_token("cli-tok") == "cli-tok"


def test_resolve_oidc_token_from_env(monkeypatch):
    monkeypatch.setenv(OIDC_TOKEN_ENV_VAR, "env-tok")
    assert resolve_oidc_token(None) == "env-tok"


def test_resolve_oidc_token_missing_raises(monkeypatch):
    monkeypatch.delenv(OIDC_TOKEN_ENV_VAR, raising=False)
    with pytest.raises(MissingTokenError):
        resolve_oidc_token(None)


# ---------------------------------------------------------------------------
# Slug splitting


def test_split_slug_valid():
    assert split_slug("owner/repo") == ("owner", "repo")


@pytest.mark.parametrize(
    "bad", ["", "no-slash", "/repo", "owner/", "a/b/c", "owner//repo"]
)
def test_split_slug_invalid(bad):
    with pytest.raises(PublishError):
        split_slug(bad)


# ---------------------------------------------------------------------------
# publish_report — uses MockTransport


def _good_fixture(path):
    return path / "examples" / "good_integration"


def _make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_publish_report_success(tmp_path, monkeypatch):
    # Use the in-tree good fixture by resolving relative to repo root.
    repo_root = os.path.dirname(os.path.dirname(__file__))
    fixture = os.path.join(repo_root, "examples", "good_integration")

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["auth"] = request.headers.get("Authorization")
        captured["ua"] = request.headers.get("User-Agent")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "report_id": "rep_abc",
                "report_url": "https://hasscheck.io/owner/repo/reports/rep_abc",
                "badge_url_template": "https://hasscheck.io/api/projects/owner/repo/badge/{category}.json",
                "schema_version": "0.3.0",
            },
        )

    with _make_client(handler) as client:
        result = publish_report(
            fixture,
            endpoint="https://hasscheck.io",
            oidc_token="tok-abc",
            no_config=True,
            client=client,
        )

    assert result.report_id == "rep_abc"
    assert result.report_url.endswith("/rep_abc")
    assert result.schema_version == "0.3.0"

    assert captured["method"] == "POST"
    assert captured["url"] == "https://hasscheck.io/api/reports"
    assert captured["auth"] == "Bearer tok-abc"
    assert captured["ua"].startswith("hasscheck/")
    assert captured["body"]["schema_version"] == "0.3.0"
    assert captured["body"]["tool"]["name"] == "hasscheck"


def test_publish_report_raises_on_4xx():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    fixture = os.path.join(repo_root, "examples", "good_integration")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "error": "schema_version_mismatch",
                "expected": "0.4.0",
                "received": "0.3.0",
                "message": "Server does not support this report schema.",
            },
        )

    with _make_client(handler) as client:
        with pytest.raises(PublishRequestError) as ex:
            publish_report(
                fixture,
                endpoint="https://hasscheck.io",
                oidc_token="tok",
                no_config=True,
                client=client,
            )
    assert ex.value.status_code == 422
    assert "schema_version_mismatch" in str(ex.value)


def test_publish_report_raises_on_5xx():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    fixture = os.path.join(repo_root, "examples", "good_integration")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="server unavailable")

    with _make_client(handler) as client:
        with pytest.raises(PublishRequestError) as ex:
            publish_report(
                fixture,
                endpoint="https://hasscheck.io",
                oidc_token="tok",
                no_config=True,
                client=client,
            )
    assert ex.value.status_code == 503


def test_publish_report_unauthorized_returns_401():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    fixture = os.path.join(repo_root, "examples", "good_integration")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "missing_token"})

    with _make_client(handler) as client:
        with pytest.raises(PublishRequestError) as ex:
            publish_report(
                fixture,
                endpoint="https://hasscheck.io",
                oidc_token="tok",
                no_config=True,
                client=client,
            )
    assert ex.value.status_code == 401


# ---------------------------------------------------------------------------
# withdraw_report


def test_withdraw_single_report():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(204)

    with _make_client(handler) as client:
        withdraw_report(
            endpoint="https://hasscheck.io",
            oidc_token="tok",
            owner="owner",
            repo="repo",
            report_id="rep_abc",
            client=client,
        )

    assert captured["method"] == "DELETE"
    assert (
        captured["url"]
        == "https://hasscheck.io/api/projects/owner/repo/reports/rep_abc"
    )


def test_withdraw_all_reports_for_slug():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(204)

    with _make_client(handler) as client:
        withdraw_report(
            endpoint="https://hasscheck.io",
            oidc_token="tok",
            owner="owner",
            repo="repo",
            report_id=None,
            client=client,
        )

    assert captured["method"] == "DELETE"
    assert captured["url"] == "https://hasscheck.io/api/projects/owner/repo"


def test_withdraw_raises_on_403():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "forbidden"})

    with _make_client(handler) as client:
        with pytest.raises(PublishRequestError) as ex:
            withdraw_report(
                endpoint="https://hasscheck.io",
                oidc_token="tok",
                owner="owner",
                repo="repo",
                report_id="rep_abc",
                client=client,
            )
    assert ex.value.status_code == 403
