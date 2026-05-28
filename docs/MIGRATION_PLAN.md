# Migration Plan

The current migration successfully moved several legacy backend modules into the new platform. The next phase is architectural cleanup.

## Phase 1: Canonical Domain Modules

Create and activate:

- `operia/identity`
- `operia/cases`
- `operia/evidence`
- `operia/reports`
- `operia/exports`
- `operia/audit`

Move shared models out of `legal_report`:

- User
- Case
- TechnicalData
- Evidence
- ChainOfCustodyAction
- Finding
- Hypothesis
- DamageItem
- Report
- ReportSection
- ReportVersion
- ReportReview
- Presentation
- PresentationSlide

## Phase 2: Module Dependency Cleanup

Update modules to depend on canonical services:

- Cybercrime uses `cases`, `evidence`, `reports`, `exports`
- Geo Trace uses `cases`, `evidence`, `reports`, `exports`
- Geo Proximity uses `cases`, `reports`, `exports`
- Legal Report uses `cases`, `evidence`, `reports`, `legal`

## Phase 3: API Normalization

Target API shape:

```text
/api/cases
/api/evidence
/api/intelligence
/api/cybercrime
/api/geo/trace
/api/geo/proximity
/api/legal
/api/reports
/api/exports
/api/dashboard
/api/settings
```

## Phase 4: Frontend Migration

Build real frontend modules:

```text
apps/web/src/modules/cases
apps/web/src/modules/evidence
apps/web/src/modules/cybercrime
apps/web/src/modules/geo
apps/web/src/modules/legal
apps/web/src/modules/reports
apps/web/src/modules/settings
```

## Phase 5: SaaS Readiness

Add:

- Organization
- Membership
- Role
- User permissions
- Case permissions
- Audit logs
- `organization_id` on main entities

## Phase 6: Production Readiness

Add:

- Alembic migrations
- Authentication
- Authorization
- Test suite
- CI workflow
- Deployment documentation
- Environment-specific configuration

