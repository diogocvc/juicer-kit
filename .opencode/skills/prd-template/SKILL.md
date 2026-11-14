---
name: prd-template
description: Use this skill when creating a Product Requirements Document (PRD) for a new feature or product. Technical requirements stay high-level; detailed design belongs to the architecture activity.
---

# Skill: PRD Template

Use this skill when creating a Product Requirements Document. A PRD states the
problem, outcome and constraints; it is **not** a design document.

> **Boundary with architecture.** "Technical Requirements" in this template are
> intentionally high-level: known constraints, integrations and non-functional
> targets. Detailed components, interfaces, data models, API contracts and
> trade-offs belong to the `@architect` design activity (see the `api-design`
> skill). Do not let a PRD hard-code an implementation before the design is
> evaluated.

## Template

```md
# PRD: [Feature Name]

## Overview

**Problem**: [What problem are we solving, for whom?]

**Goal**: [Desired outcome in one sentence.]

**Success Metrics**: [Measurable outcome, baseline and target. If unknown,
write UNKNOWN and the question to answer.]

## Context and Assumptions

- **Given**: [Facts, prior decisions, links.]
- **Assumptions**: [What must be true; how each will be validated.]
- **Non-goals**: [What we are explicitly not solving now.]

## Scope

### In Scope

- [Capability 1]
- [Capability 2]
- [Capability 3]

### Out of Scope

- [What we are NOT building now, and why]

## Users and Stories

### Story 1: [Title]

**As a** [user type]
**I want** [goal]
**So that** [benefit]

**Acceptance Criteria**:
- [ ] Observable and verifiable criterion 1
- [ ] Observable and verifiable criterion 2

### Story 2: [Title]

...

## Technical Requirements (high level)

- **Constraints**: [Platform, language, compliance, latency/cost envelope.]
- **Integrations**: [External systems and ownership; contract details are a
  design decision.]
- **Non-functional targets**: [Availability, performance, privacy, security.
  Give numbers only when known.]
- **Data**: [What data is needed, classification and retention. No schema
  detail here.]
- **Compatibility**: [Public APIs or formats that must keep working.]

> Detailed architecture, interfaces, schemas and API versioning are produced by
> the `@architect` activity and recorded as ADRs/contracts. Do not duplicate
> them here.

## Security & Compliance

- [Authentication/authorization requirements.]
- [Data protection (PII, encryption, retention).]
- [Compliance standards (GDPR, LGPD, SOC 2, etc.) or UNKNOWN.]
- [Threats and abuse cases to consider.]

## Risks & Mitigations

- **Risk**: [Description]
  - **Likelihood / impact**:
  - **Mitigation**:
- **Risk**: ...

## Rollout and Measurement

- **Rollout**: [Flag, cohort, migration, rollback.]
- **Instrumentation**: [Events/metrics needed to evaluate success.]
- **Definition of done**: [Outcome, not just shipped code.]

## Timeline

- **Phase 1**: [Milestone and dependency, not a promise.]
- **Phase 2**: [Milestone and dependency.]

## Open Questions

- [Question, owner, why it blocks or shapes the work.]

## Decision Log

- [Date, decision, alternatives, link to ADR.]
```

## Rules

- Keep the PRD concise; link to artifacts instead of duplicating them.
- Define success metrics upfront; mark unknown metrics explicitly.
- List non-goals and open questions; do not hide uncertainty.
- Technical requirements stay at the constraint level; detailed design is a
  separate activity.
- Acceptance criteria must be observable and verifiable.
- Update the PRD when requirements change; record the decision.
