---
name: api-design
description: Use this skill when designing or reviewing RESTful APIs, including versioning and breaking changes.
---

# Skill: API Design

Use this skill when designing or reviewing RESTful APIs. It follows the
Microsoft REST API Guidelines, Google API Improvement Proposals (AIPs), RFC
9457 (Problem Details for HTTP APIs) and semantic versioning practice.

## Standards

### URL Structure

- Use nouns, not verbs: `GET /users`, not `GET /getUsers`.
- Use plural nouns: `/users`, `/products`.
- Use lowercase and hyphens: `/user-profiles`, not `/userProfiles`.
- Version APIs in the path or a header, consistently: `/api/v1/users`.
- Resource identifiers are opaque and stable; never expose internal ids.

### HTTP Methods

- `GET`: retrieve (safe, idempotent, no side effects).
- `POST`: create or non-idempotent action.
- `PUT`: replace the entire resource (idempotent).
- `PATCH`: partial update (document merge semantics).
- `DELETE`: remove (idempotent; `204` or `404` as documented).

### Request/Response Format

- Use JSON; be explicit about content type.
- Use one casing convention (`snake_case` or `camelCase`) everywhere.
- Return the resource representation, not a transport wrapper, unless the
  project standard requires one.
- Include metadata when paginating:

```json
{
  "data": { },
  "meta": {
    "page": 1,
    "perPage": 20,
    "total": 100
  }
}
```

### Pagination

- Cursor pagination for large or changing collections; offset pagination only
  when stable ordering is guaranteed.
- Query params: `?page=1&perPage=20` or `?cursor=...&limit=50`.
- Set defaults and maximums (`perPage=20`, max `100`).
- Document ordering and whether the cursor is opaque.

### Filtering and Sorting

- Filtering: `?status=active&role=admin`.
- Sorting: `?sort=createdAt&order=desc`.
- Search: `?q=searchTerm`.
- Validate allowed fields; unknown filters are rejected, not ignored.

### Error Handling

Use standard HTTP status codes:

- `200` success, `201` created, `204` no content.
- `400` malformed request, `401` unauthenticated, `403` forbidden.
- `404` not found, `409` conflict, `412` precondition failed.
- `422` semantically invalid, `429` rate limited.
- `500` server error, `503` unavailable.

Use RFC 9457 Problem Details:

```json
{
  "type": "https://example.com/problems/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "Email is required",
  "instance": "/api/v1/users",
  "errors": [
    {"field": "email", "message": "Email is required"}
  ]
}
```

- Never leak stack traces, SQL or secrets in production errors.
- Include a stable machine-readable `type` or `code`.

### Authentication and Authorization

- Use OAuth 2.1 / OIDC or session auth appropriate to the client.
- Send tokens in `Authorization: Bearer <token>`; never in URLs.
- Return `401` for missing/invalid credentials, `403` for insufficient
  permission.
- Enforce **object-level** authorization on every resource.
- Document scopes and token lifetime.

### Rate Limiting

- Rate limit public and auth endpoints.
- Return `429` with `Retry-After`.
- Include `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (or the
  project's chosen standard).

### Idempotency and Retries

- Support `Idempotency-Key` on unsafe creates when clients may retry.
- Define retry semantics for `429`/`503`; use exponential backoff with jitter.
- Make consumers tolerate at-least-once delivery where applicable.

## Versioning

Versioning is a contract, not a deployment detail.

### When to bump

- **Major / new version** — any breaking change:
  - removing or renaming a field, endpoint, parameter or enum value;
  - changing a type, format, default, status code or error shape;
  - making an optional request field required;
  - tightening validation so previously valid requests fail;
  - changing authorization or idempotency semantics.
- **Minor / additive** — new optional fields, new endpoints, new enum values
  that clients are required to tolerate. Document client tolerance rules.
- **Patch** — no contract change.

### How to version

- Choose **one** scheme and apply it everywhere: URL major version
  (`/api/v1`) or media-type/header version. Do not mix.
- A new major version is a new contract surface; it may share implementation
  but must be documented and tested independently.
- Never silently change the meaning of an existing field or status code.
- Keep at most two major versions active unless policy says otherwise.

### Deprecation and sunset

- Mark deprecated fields/endpoints in the docs and OpenAPI (`deprecated: true`).
- Announce a timeline; send `Deprecation` and `Sunset` headers where supported.
- Monitor usage before removal; provide a migration guide.
- Remove only after the announced window and with a recorded decision.

### Compatibility testing

- Contract tests for each supported major version.
- Consumer-driven contract tests where consumers exist.
- OpenAPI diff in CI; a breaking diff fails the build unless approved.

## Documentation

Document every endpoint with:

- URL, method, version and auth requirements.
- Request schema (body, query, path, headers).
- Response schema for success and every error.
- Pagination, filtering, rate limits and idempotency.
- Example requests/responses and a changelog of contract changes.
- An OpenAPI (or equivalent) artifact checked into the repository.

## Output Format

When designing an API, provide:

```
## API: [Endpoint Name]

### Endpoint
- **URL**: `POST /api/v1/resource`
- **Method**: `POST`
- **Auth**: Required (Bearer token, scope)
- **Version**: v1
- **Idempotency**: [key/semantics]

### Request
```json
{
  "field1": "type",
  "field2": "type"
}
```

### Response (201 Created)
```json
{
  "data": { },
  "meta": { }
}
```

### Errors
- `400` — [when]
- `422` — [when], RFC 9457 body

### Compatibility
- Breaking changes: [none / new major version]
- Deprecations: [field, sunset date]

### Notes
- [Pagination, rate limit, caching, special considerations]
```

## Rules

- A breaking change requires a new major version and a migration path.
- Never change field meaning or type in place.
- Never expose internal identifiers or implementation details.
- Validate and authorize at the boundary; do not trust the client.
- Errors are part of the contract; document and test them.
