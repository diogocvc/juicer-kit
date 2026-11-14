---
description: "Remove a task from the planning backlog after dependency and state checks."
---

# Command: /remove-backlog

**Core integration.** This edits the Markdown planning source only. After a
validated `juicer import-backlog`, `.juicer/` is canonical and there is no
bidirectional sync; removing a Markdown entry does not remove or cancel a
mission task. For an imported task, use the core's state and report that the
Markdown board must be reconciled manually.

## Steps

1. **Read the task**
   - Load it from `backlog/backlog.md`, `backlog/in-progress.md` and
     `backlog/done/`.

2. **Check dependents and state**
   - Find every task that lists this id in its dependencies.
   - If dependents exist, **stop**: either repoint their dependencies or remove
     them first. Never leave a dangling reference.
   - If the task is `In Progress`, require explicit confirmation and explain
     that work may already exist in a branch/worktree.
   - If the task is `Done`, do not delete history; archive it instead.

3. **Confirm removal**
   - Show the task details, dependents and the exact files to change.
   - Ask for an explicit confirmation.

4. **Remove**
   - Delete it from the planning files only.
   - Do not touch `.juicer/` or Git history.

5. **Confirm**
   - Report what was removed and any follow-up needed to reconcile the core
     mission.

## Output Format

```
⚠️ Remove Task: TASK-XXX [Title]

**Task Details**:
- Description: [description]
- Priority: [P0-P3]
- Status: [Pending/In Progress/Blocked/Done]
- Dependents: [TASK-YYY or None]
- Imported into a mission: [yes/no/unknown]

**Are you sure you want to remove this task?** (yes/no)

✅ Task Removed from planning backlog

- Removed from: [files]
- Dependents needing update: [none/list]
- Core mission reconciliation: [required/not applicable]
```

## Rules

- Always confirm before removing.
- Never remove a task that still has dependents.
- Never delete a Done task; archive it.
- Never edit `.juicer/`, branches or worktrees from this command.
- Report `UNKNOWN` if you cannot determine whether the task was imported.
- Notify the user of any follow-up reconciliation.
