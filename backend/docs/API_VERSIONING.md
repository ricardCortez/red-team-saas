# API Versioning

Red Team SaaS uses **URL-based versioning**. The version is included in the path prefix.

---

## Current Versions

| Version | Status  | Base Path    | Sunset Date  |
|---------|---------|------------- |------------- |
| v1      | Stable  | `/api/v1/`   | 2027-01-01   |

---

## URL Format

All endpoints are prefixed with the version:

```
https://api.redteam-saas.com/api/v1/projects
https://api.redteam-saas.com/api/v1/findings
```

---

## Version Lifecycle

1. **Active** — Fully supported, receives new features and bug fixes.
2. **Deprecated** — Still functional, but no new features. Migration recommended.
3. **Sunset** — Removed after the sunset date. Requests return `410 Gone`.

---

## Breaking Changes Policy

- Breaking changes are only introduced in **new major versions** (e.g., v2).
- A minimum **6-month deprecation period** is provided before sunsetting a version.
- Deprecation notices are communicated via:
  - `Deprecation` response header
  - API changelog
  - Email notification to registered users

---

## Version-Specific Headers

You may optionally specify the desired version via the `Accept` header:

```
Accept: application/vnd.redteam.v1+json
```

When omitted, the version in the URL path is used.

---

## Migration Guide

When a new version is released, a migration guide will be published at `/docs/migration-v{N}.md` detailing all breaking changes and the recommended upgrade path.
