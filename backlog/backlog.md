# Backlog

## Task Template

```md
### Task: [TASK-XXX] [Title]

**Description**: [What needs to be done]

**Priority**: [P0-Critical | P1-High | P2-Medium | P3-Low]

**Status**: [Pending | In Progress | Blocked | Done]

**Dependencies**: [TASK-XXX, TASK-YYY]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Estimated Effort**: [S/M/L or hours]

**Notes**: [Any additional context]
```

## Pending Tasks

### Task: [TASK-001] Create user authentication with JWT

**Description**: Implement JWT-based authentication with access and refresh tokens.

**Priority**: P1-High

**Status**: Pending

**Dependencies**: None

**Acceptance Criteria**:
- [ ] User can register with email/password
- [ ] User can login and receive JWT tokens
- [ ] Refresh token flow works correctly
- [ ] Protected routes require valid token
- [ ] Tests cover all scenarios

**Estimated Effort**: L

**Notes**: Use bcrypt for password hashing, store tokens in httpOnly cookies.

---

### Task: [TASK-002] Create user profile API

**Description**: Build REST API for user profile management.

**Priority**: P2-Medium

**Status**: Pending

**Dependencies**: TASK-001

**Acceptance Criteria**:
- [ ] GET /api/users/:id returns profile
- [ ] PUT /api/users/:id updates profile
- [ ] DELETE /api/users/:id deletes account
- [ ] Authorization checks (user can only edit own profile)
- [ ] Tests cover all scenarios

**Estimated Effort**: M

**Notes**: Include validation with Zod.
