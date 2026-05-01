# Publish handshake architecture (v0.7)

## Overview

`hasscheck publish` is the opt-in CLI command that uploads a HassCheck JSON
report to a hosted service. v0.7 ships with one supported destination:
`hasscheck-web` running at `https://hasscheck.io` (or any URL the maintainer
points to).

Publishing is **opt-in only** — `hasscheck check` and the GitHub Action never
upload anything by default. The CLI must be invoked explicitly, or the
composite action input `emit-publish: 'true'` must be set. See
ADR 0008 for the policy rationale.

This document describes the **client-side** of the handshake. The server
architecture lives in the private `hasscheck-web` repository.

## Authentication: GitHub Actions OIDC

v0.7 publishing is supported only from GitHub Actions runners. The composite
action requests a workflow OIDC token and passes it to the CLI:

```yaml
permissions:
  id-token: write          # required to mint the OIDC token
  contents: read

steps:
  - uses: Daily-Nerd/hasscheck@v1
    with:
      emit-publish: 'true'
      publish-endpoint: 'https://hasscheck.io'   # optional; defaults below
```

Internally the action does the equivalent of:

```bash
ID_TOKEN=$(curl -fsSL \
  -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
  "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=hasscheck-web")

hasscheck publish \
  --path . \
  --to "$PUBLISH_ENDPOINT" \
  --oidc-token "$ID_TOKEN"
```

The CLI itself does not request the OIDC token; it consumes one passed in via
flag or environment variable (`HASSCHECK_OIDC_TOKEN`). This keeps the CLI
runnable in non-CI contexts (where it would simply fail to publish without a
token) and avoids embedding GitHub-specific token-acquisition logic in the
CLI itself.

The OIDC token's `repository` claim is the **authoritative source** for the
project slug. The server does not accept a slug from the request body; it
takes `owner/repo` from the verified token.

## Default endpoint

The CLI's default `--to` value is `https://hasscheck.io`. Maintainers can
override at any time:

- Per-invocation: `hasscheck publish --to https://my-private-host.example`
- Per-repo: `publish.endpoint` in `hasscheck.yaml` (config-file support TBD
  in implementation issues).
- Self-hosted: maintainers running their own `hasscheck-web` instance simply
  point at it.

There is no implicit upload to any URL. The CLI emits no network traffic
unless `publish` is explicitly invoked.

## Request shape

`POST {endpoint}/api/reports`

Headers:

```
Authorization: Bearer <oidc-token>
Content-Type: application/json
User-Agent: hasscheck/<version>
```

Body: the full HassCheck JSON report as produced by `report_to_json()`
(`src/hasscheck/output.py`). The body is the unmodified output of
`hasscheck check --format json`. The CLI does not strip, transform, or
augment the report before upload.

A successful response returns:

```json
{
  "report_id": "<server-assigned id>",
  "report_url": "https://hasscheck.io/<owner>/<repo>/reports/<id>",
  "badge_url_template": "https://hasscheck.io/api/projects/<owner>/<repo>/badge/{category}.json",
  "schema_version": "0.3.0"
}
```

The `report_url` is the public report page for the just-uploaded report.

## Schema version compatibility

The server validates `schema_version` strictly. If the report's
`schema_version` does not match what the server is built against, the server
returns:

```json
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "error": "schema_version_mismatch",
  "expected": "0.3.0",
  "received": "0.4.0",
  "message": "Server does not support this report schema. Update hasscheck-web or pin the OSS CLI to a compatible version."
}
```

The CLI surfaces this error verbatim to the maintainer and exits with a
non-zero code. There is no auto-retry, no version negotiation, no fallback.
ADR 0006 governs schema bumps; ADR 0008 commits the server to lockstep
versioning.

## Error semantics

| HTTP status | Meaning | CLI behavior |
|---|---|---|
| 200 OK | Report accepted and published | Print `report_url`, exit 0 |
| 400 Bad Request | Malformed JSON or missing required field | Print server error, exit 1 |
| 401 Unauthorized | Missing OIDC token | Print "no OIDC token; not running in CI?", exit 1 |
| 403 Forbidden | OIDC token's `repository` claim does not match the report's project | Print server error, exit 1 |
| 422 Unprocessable Entity | `schema_version_mismatch` (see above) | Print server error, exit 1 |
| 429 Too Many Requests | Rate limit | Print retry-after value, exit 1 (no auto-retry in v0.7) |
| 5xx | Server error | Print server error, exit 1 |

The CLI does not retry on its own. CI workflows that want retries should
wrap the action invocation.

## Withdrawal

Per ADR 0008, maintainers can un-publish their own reports:

- `hasscheck publish --withdraw --report-id <id>` →
  `DELETE {endpoint}/api/projects/{owner}/{repo}/reports/{id}`
- `hasscheck publish --withdraw-all` →
  `DELETE {endpoint}/api/projects/{owner}/{repo}`

Both require the same OIDC handshake. Withdrawal is immediate and
unrecoverable; the CLI prints a confirmation prompt unless `--force` is
passed.

## Privacy posture

- The CLI uploads the report **only** when explicitly invoked. No
  telemetry, no diagnostics phone-home, no implicit network calls.
- The default endpoint (`https://hasscheck.io`) can be replaced or omitted.
- Maintainers running on self-hosted CI without GitHub OIDC cannot publish
  in v0.7. This is a known limitation; pluggable verifiers are deferred
  post-v0.7.
- Reports belong to the publisher. Withdrawal is unconditional and immediate.
- The server retains at most 50 reports per slug (ADR 0008). Older reports
  are purged at upload time.

## What v0.7 publish does NOT do

- Does not crawl or upload reports for any repo other than the one named in
  the OIDC token's `repository` claim.
- Does not run rules server-side; the server trusts the uploaded report
  (server-side rule re-execution is v1.0 work, Issue #67).
- Does not produce ranked, filtered, or score-sorted listings — that is
  the v1.0 hub.
- Does not require a maintainer-managed API key, secret, or signup.
- Does not charge anything (ADR 0008's free-for-all v0.7 commitment).

## References

- ADR 0008 — Hosted reports publish contract (policy)
- ADR 0006 — Ruleset versioning
- ADR 0007 — Badge policy (server-side badge endpoint inherits these
  guards)
- `idea.md` §13 — Hosted reports + hub (opt-in only)
- `src/hasscheck/output.py` — `report_to_json()` produces the upload body
- `src/hasscheck/models.py` — JSON report schema (the integration boundary
  with `hasscheck-web`)
- GitHub Actions docs — [About security hardening with OpenID Connect](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
