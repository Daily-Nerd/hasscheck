# ADR 0008 — Hosted reports publish contract

- **Status**: Accepted
- **Date**: 2026-05-01
- **Tag**: v0.7 hosted reports

## Context

`idea.md` §13 introduces opt-in hosted reports as the v0.7 milestone:
maintainers can publish their HassCheck JSON report to a hosted service that
renders it as a public report page, exposes a server-side badge endpoint, and
keeps a bounded report history per project.

The v0.7 surface raises questions that previous ADRs do not answer:

1. **Where does the server live?** Embedding a hosted service in the OSS
   repository entangles open-source code with infrastructure, deployment, and
   any future commercial concerns.
2. **How is the maintainer authenticated?** A hosted service that accepts
   reports under a project slug must verify that the publisher owns the slug.
3. **What is the persistence and retention model?** Reports accumulate over
   time; storage must be bounded.
4. **Which schema versions does the server accept?** The JSON report contract
   evolves; permissive validation invites silent drift, strict validation
   blocks rolling upgrades.
5. **How does the server-side badge endpoint avoid duplicating policy that
   already lives in the OSS badge generator?**
6. **What can a maintainer un-publish?**
7. **Is v0.7 monetized?** The HA community is OSS-first and anti-rent-seeking;
   premature commercialization would burn the trust the v0.1–v0.6 ladder built.

ADR 0001 (override honesty), ADR 0006 (ruleset versioning), and ADR 0007
(badge policy) constrain v0.7 but do not prescribe its shape. This ADR fills
that gap.

## Decision

### Two-repo split: `hasscheck` (OSS) and `hasscheck-web` (private)

The hosted service ships as a sibling private repository, `hasscheck-web`. It
is **not** part of this OSS repository.

| Repo | License | Contents | Purpose |
|---|---|---|---|
| `hasscheck` (this repo) | OSS | CLI, `action.yml`, rules, scaffolds, badges, `hasscheck publish` command, slug detection, JSON report contract (`models.py`) | Everything a maintainer runs locally or in their own CI |
| `hasscheck-web` | Private | FastAPI service, SQLAlchemy persistence, Jinja2 renderer, server-side badge endpoint, OIDC verifier, deployment infra | The hosted service |

The integration boundary is the JSON report schema in
`src/hasscheck/models.py`. `hasscheck-web` consumes `hasscheck` as a pinned
pip dependency and tracks the supported schema range explicitly.

#### Boundary discipline

- **Nothing OSS-only in `hasscheck-web`.** Logic reusable by other clients
  (e.g., a published-report SDK) ships from `hasscheck`.
- **Nothing proprietary in `hasscheck`.** No server URLs, no auth secrets, no
  phone-home by default. The CLI knows about `hasscheck-web` only via explicit
  opt-in: `hasscheck publish --to https://hasscheck.io`. The default endpoint
  is configurable; there is no implicit upload.
- **Schema breaks travel one way.** `hasscheck` bumps the schema;
  `hasscheck-web` follows in lockstep. The server never invents schema fields
  the OSS package does not define. The CLI never assumes server-specific
  behavior.

### Authentication and slug verification: GitHub OIDC

The hosted service authenticates publishers via the GitHub Actions OIDC token.

- The composite action requests a workflow OIDC token (`id-token: write`
  permission).
- `hasscheck publish` reads the token from the CI environment and presents it
  on `POST /api/reports`.
- The server validates the token's `iss`, `aud`, and `repository` claims
  against the published reports' declared project slug. The `repository`
  claim is the **authoritative source** for `owner/repo` — server-side
  takes the OIDC claim verbatim.

There is no maintainer-managed token, no API key, no per-repo registration
step. Non-GitHub publishers are out of scope for v0.7; the verification
interface is pluggable so future publisher types can be added without
re-architecting.

### Persistence: SQLite via SQLAlchemy

`hasscheck-web` uses SQLite as the v0.7 datastore, accessed through SQLAlchemy
ORM with Alembic migrations.

- SQLite for v0.7 dogfood and small-scale hosting.
- The same SQLAlchemy models target Postgres for production scaling — the
  migration is a connection-string swap.
- BigQuery is reserved as a future analytics target via a separate write
  path. It is **not** the primary store.

### Retention: last 50 reports per slug

The server keeps the most recent 50 reports per project slug. Older reports
are purged at upload time, not lazily. There is no time-based retention
window in v0.7. The bound is intentionally generous; the policy can be
revisited without breaking the contract.

### Schema validation: strict version match

`POST /api/reports` rejects any payload where `schema_version` does not match
the version the server is built against (currently `"0.3.0"`). The server
bumps in lockstep with the OSS schema; permissive validation is deferred until
multiple live schemas are supported.

This is enforced server-side. The CLI does not validate version compatibility
before upload; it sends the report it produces.

### Server-side badge endpoint

The badge endpoint at `GET /api/projects/{owner}/{repo}/badge/{category}.json`
regenerates shields.io endpoint JSON from the most recent verified report for
that slug.

- The server **trusts the uploaded report's category aggregates** at v0.7. It
  does not re-run rules against the source repository.
- ADR 0007's guards apply server-side. `assert_label_is_clean` runs on every
  rendered label. `FORBIDDEN_LABEL_TOKENS` is enforced in `hasscheck-web` by
  importing the same policy module from the `hasscheck` package.
- Categories with zero applicable rules emit no badge (consistent with
  ADR 0007's skip-N/A rule).
- Independent server-side rule evaluation is **v1.0 work** (Issue #67). The
  v0.7 endpoint is designed to be replaced by the v1.0 verified path without
  changing the URL contract.

### Public report page: server-rendered Jinja2

The public report page is rendered server-side from Jinja2 templates against
the stored JSON. There is no JavaScript framework, no static-site build step,
no client-side hydration. The page surfaces:

- Findings (rule_id, status, message, source URL, fix suggestion)
- Category signals (points awarded / possible)
- Applicability and override metadata
- Ruleset and `source_checked_at` (per ADR 0006)
- Report history listing (last 50)
- Server-side rendering keeps the surface boring and durable.

### Withdrawal endpoints

Maintainers can un-publish, per `idea.md` §13's opt-in spirit:

- `DELETE /api/projects/{owner}/{repo}/reports/{id}` — removes a single
  report.
- `DELETE /api/projects/{owner}/{repo}` — removes all reports for the slug.

Both endpoints require an OIDC token whose `repository` claim matches the
target slug. Withdrawal is immediate and unrecoverable; there is no soft-delete
or grace period in v0.7.

### Deployment: local Docker (v0.7), GCP (post-v0.7)

`hasscheck-web` ships with a Docker Compose configuration suitable for local
dogfood. Production hosting is GCP, tracked as a separate v0.7-rc issue —
the GCP deployment is **not** required for v0.7 to be considered shipped.
v0.7 ships when the local-Docker dogfood path works end-to-end.

The canonical hostname is `hasscheck.io` (developer-tool TLD convention,
matches HA ecosystem precedent of `home-assistant.io`). The `.com` domain is
reserved for any future commercial entity and is not the public service URL.

### v0.7 is free, for everyone

v0.7 hosted reports are **free for all users.** No paid tier, no signup tier,
no usage cap, no upsell, no advertising. `hasscheck-web` being a private
repository is an infrastructure-hygiene decision, not a commercial-readiness
signal.

The following are permanent rules, not v0.7-specific:

1. **Free tier is permanent and complete.** Solo maintainers have full free
   access forever. This is stated in README, in every announcement, and in
   any future pricing page.
2. **Same verdict, free or paid.** Any future paid tier produces identical
   findings to the free tier. Pricing never changes rule outcomes.
3. **Self-host path stays first-class.** The OSS CLI + GitHub Action +
   committed badge JSON path is fully usable without `hasscheck-web`.
4. **No "certified safe" badges sold for money.** ADR 0007 forbids
   certification language; selling certification compounds the violation.
5. **No selling aggregated maintainer data.**
6. **No ads in CLI or report pages.**
7. **No CLI free/paid split.** The OSS CLI ships every feature it ships.

Permitted future revenue paths (post-v1.0, only after community trust is
earned): GitHub Sponsors, an org/company tier (multi-repo dashboards,
Slack/Teams integrations, audit logs, SSO, SLA — aimed at companies running
HA fleets, not solo maintainers), and consulting (paid integration review
without a "certified" stamp).

Forbidden revenue paths: charging individual maintainers for any core
feature, gating safety information, selling data or ads, free/paid CLI
splits, anything that mimics official HA/HACS authority for revenue.

## Consequences

### Positive

- The OSS surface stays clean. Going-public on `hasscheck` does not leak
  server code, infrastructure, secrets, or commercial logic.
- GitHub OIDC eliminates maintainer-managed secrets — the publish flow has
  zero per-repo setup beyond the `emit-publish` action input.
- Schema-strict validation prevents silent drift and keeps the server and
  client in lockstep.
- ADR 0007 guards apply server-side via shared policy module — no chance of
  the hosted endpoint emitting a label the OSS generator would reject.
- Withdrawal endpoints honor the opt-in spirit: every report a maintainer
  publishes can be un-published.
- The free-for-all v0.7 launch buys community trust before any monetization
  conversation. Any future paid tier inherits a free tier the community
  already accepts as legitimate.

### Negative

- Two repos to maintain. `hasscheck` and `hasscheck-web` must coordinate
  schema bumps. CI cross-repo testing is a real cost.
- SQLite for v0.7 limits horizontal scaling. The Postgres migration is a
  separate piece of work and must happen before any production load.
- GitHub OIDC ties v0.7 publishing to GitHub Actions specifically. Maintainers
  who run HassCheck on non-GitHub CI cannot publish in v0.7. Pluggable
  verifier interface defers but does not solve this.
- Strict schema validation rejects clients on older versions of `hasscheck`.
  The CLI must produce a clear error when the server returns
  `schema_version_mismatch`.
- Last-50-per-slug retention discards older history. Some maintainers may
  want unbounded history; the retention bound is revisitable but not in v0.7.
- The "v0.7 is free" commitment forecloses charging for the v0.7 surface
  later. Future paid tiers must be orthogonal additions, not gated removals.

## References

- ADR 0001 — Config override policy: locked vs softenable, never force-pass
- ADR 0006 — Ruleset versioning policy
- ADR 0007 — Badge policy: opt-in only, forbidden language, layered-status
  contract
- `idea.md` §1 — Unofficial disclaimer, naming risk
- `idea.md` §6 Decision 4 — No global certification language
- `idea.md` §13 — Hosted reports + hub (opt-in only)
- `idea.md` §14 — FastAPI + SQLite/Postgres stack hint
- `idea.md` §15 Month 5 — Hosted reports deliverables
- `idea.md` §18 — Risk register (False authority, Public repo grading
  backlash, Trademark/brand confusion as HIGH)
- GitHub Issue #67 — v1.0 hub-verified badges layered on v0.7 hosted reports
- GitHub Issue #56 — `hasscheck init` (publish UX entry point)
- GitHub Issue #70 — `CHANGELOG.md` for cross-repo release coordination
