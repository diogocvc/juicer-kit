---
name: prd-template
description: Use this skill when creating a Product Requirements Document (PRD) for a new feature or product.
---

# Skill: PRD Template

Use this skill when creating a Product Requirements Document (PRD) for a new feature or product.

## Template

```md
# PRD: [Feature Name]

## Overview

**Problem**: [What problem are we solving?]

**Goal**: [What is the desired outcome?]

**Success Metrics**: [How will we measure success?]

## Scope

### In Scope

- [Feature 1]
- [Feature 2]
- [Feature 3]

### Out of Scope

- [What we are NOT building now]

## User Stories

### Story 1: [Title]

**As a** [user type]  
**I want** [goal]  
**So that** [benefit]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Story 2: [Title]

...

## Technical Requirements

### Architecture

- [High-level architecture description]
- [Components and their responsibilities]

### APIs

- **Endpoint**: `POST /api/resource`
  - **Request**: [schema]
  - **Response**: [schema]

### Data Models

- **Model Name**: [fields and types]

### Dependencies

- [External services or internal modules]

## Security & Compliance

- [Authentication/authorization requirements]
- [Data protection requirements (PII, encryption)]
- [Compliance standards (GDPR, LGPD, etc.)]

## Risks & Mitigations

- **Risk**: [Description]
  - **Mitigation**: [How to reduce risk]

## Timeline

- **Phase 1**: [Milestone and date]
- **Phase 2**: [Milestone and date]
- **Phase 3**: [Milestone and date]

## Open Questions

- [Question 1]
- [Question 2]
```

## Rules

- Keep the PRD concise but complete.
- Use clear, non-technical language when possible.
- Define success metrics upfront.
- List open questions explicitly — do not hide uncertainties.
- Update the PRD as requirements evolve.
