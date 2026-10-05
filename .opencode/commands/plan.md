---
description: "Create a detailed implementation plan for a task."
---

# Command: /plan

When invoked, create a detailed implementation plan for the given task.

## Steps

1. **Understand the Task**
   - Read the task description.
   - Ask clarifying questions if needed.

2. **Analyze the Codebase**
   - Use @finder to map relevant files.
   - Use @analyst to understand dependencies and risks.

3. **Design the Solution**
   - Use @architect to propose architecture.
   - Document components, interfaces, and data models.

4. **Break Down Tasks**
   - Use @planner to decompose into atomic tasks.
   - Define dependencies, ordering, and acceptance criteria.

5. **Output the Plan**
   - Present the plan in a clear, structured format.
   - Include timeline estimates and risks.

## Output Format

```
## Plan: [Task Name]

### Overview
[Brief description of what we're building]

### Architecture
- **Components**: [List and responsibilities]
- **Data Models**: [Schemas]
- **APIs**: [Endpoints]

### Task List

#### Task 1: [Name]
- **Description**: [What to do]
- **Dependencies**: [None / Task X]
- **Acceptance Criteria**:
  - [ ] Criterion 1
  - [ ] Criterion 2
- **Complexity**: [S/M/L]
- **Estimated Time**: [X hours]

#### Task 2: [Name]
...

### Critical Path
Task 1 → Task 3 → Task 5

### Risks & Blockers
- [Risk and mitigation]

### Next Steps
1. [Action 1]
2. [Action 2]
```

## Rules

- Do not implement code — only plan.
- Ensure tasks are small enough to implement in one session.
- Highlight tasks that require user confirmation.
