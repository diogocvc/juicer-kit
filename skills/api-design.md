# Skill: API Design

Use this skill when designing or reviewing RESTful APIs.

## Standards

### URL Structure

- Use nouns, not verbs: `GET /users`, not `GET /getUsers`.
- Use plural nouns: `/users`, `/products`.
- Use lowercase and hyphens: `/user-profiles`, not `/userProfiles`.
- Version APIs: `/api/v1/users`.

### HTTP Methods

- `GET`: Retrieve resources (idempotent, no side effects).
- `POST`: Create resources.
- `PUT`: Replace entire resource.
- `PATCH`: Partial update.
- `DELETE`: Remove resource.

### Request/Response Format

- Always use JSON.
- Use consistent casing: `snake_case` or `camelCase` (pick one and stick to it).
- Include metadata in responses:

```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "perPage": 20,
    "total": 100
  }
}
```

### Pagination

- Use query params: `?page=1&perPage=20`.
- Return pagination metadata in `meta` object.
- Set reasonable defaults (e.g., `perPage=20`, max `perPage=100`).

### Filtering & Sorting

- Filtering: `?status=active&role=admin`.
- Sorting: `?sort=createdAt&order=desc`.
- Search: `?q=searchTerm`.

### Error Handling

- Use standard HTTP status codes:
  - `200`: Success.
  - `201`: Created.
  - `400`: Bad Request (invalid input).
  - `401`: Unauthorized (not authenticated).
  - `403`: Forbidden (no permission).
  - `404`: Not Found.
  - `409`: Conflict (e.g., duplicate).
  - `422`: Unprocessable Entity (validation error).
  - `500`: Internal Server Error.

- Error response format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": [
      { "field": "email", "message": "Email is required" }
    ]
  }
}
```

### Authentication

- Use JWT or session-based auth.
- Include token in `Authorization: Bearer <token>` header.
- Return `401` for missing/invalid tokens.
- Return `403` for insufficient permissions.

### Rate Limiting

- Implement rate limiting on public endpoints.
- Return `429 Too Many Requests` when limit exceeded.
- Include headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

### Documentation

- Document all endpoints with:
  - URL and method.
  - Request schema (body, query, params).
  - Response schema (success and error).
  - Authentication requirements.
  - Example requests and responses.

## Output Format

When designing an API, provide:

```
## API: [Endpoint Name]

### Endpoint
- **URL**: `POST /api/v1/resource`
- **Method**: `POST`
- **Auth**: Required (Bearer token)

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
  "data": { ... },
  "meta": { ... }
}
```

### Response (400 Bad Request)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "...",
    "details": [...]
  }
}
```

### Notes
- [Any special considerations]
```
