# Worker Protocol

Every worker follows the same contract.

## Input

- mission
- active unit
- relevant project instructions
- role definition
- acceptance criteria

## Execution

- inspect only necessary context
- perform assigned work
- verify where possible
- do not expand scope silently

## Output

```text
RESULT
What changed or was discovered.

EVIDENCE
Commands, files, tests, observations.

RISKS
Unresolved risks.

NEXT ACTION
Smallest useful next step.
```

## State update

If work changes project state, update:

- `.juicer/handoff.md`
- `.juicer/learnings.md` when knowledge is reusable
- `.juicer/plan.md` only when the plan itself changes
