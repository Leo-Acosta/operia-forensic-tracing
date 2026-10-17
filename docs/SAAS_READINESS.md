# SaaS Readiness

Registro inicial conservado como antecedente. El estado actual y los límites
verificados están en [E0/E1](E0_E1_SECURITY_BASELINE.md), actualizado al 2026-10-17.
Autenticación, aislamiento organizacional y secretos ya recibieron correcciones;
eso no acredita permisos individuales por expediente ni preparación productiva.

The platform now has initial SaaS boundaries:

- `Organization`
- `User`
- `Role`
- `Membership`
- `organization_id` added to major shared entities;
- `AuditLog` for future traceability and compliance.

This is a foundation, not complete multi-tenant enforcement yet. The next stage should add authentication, authorization, scoped queries, per-organization settings, and migration management.

## Phase 9 Security Foundation

Implemented:

- local admin bootstrap endpoint;
- PBKDF2 password hashing using Python standard library;
- HMAC-signed bearer tokens;
- token persistence and revocation table;
- `/api/identity/login`;
- `/api/identity/logout`;
- `/api/identity/me`;
- role permission catalog;
- organization-aware listing for users, organizations, memberships and audit logs;
- audit entries for identity, cases, evidence, custody actions and reports;
- `organization_id` propagation during authenticated case/evidence/report creation.

Default roles:

- `admin`
- `coordinador`
- `analista`
- `legal`
- `lector`

Important limits:

- this is a local SaaS security foundation, not production-grade identity yet;
- no external identity provider is integrated;
- password reset, email verification, MFA and refresh-token rotation are pending;
- legacy unauthenticated workflows remain partially available to avoid breaking local development.

Recommended next hardening:

- require authentication for all write routes;
- add per-case ACLs;
- add organization-scoped query helpers across every module;
- add password policy and account lockout;
- add secure secret management outside database URL-derived development secret.
