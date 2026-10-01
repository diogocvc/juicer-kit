# Release Workflow

Canonical order: `build/package < ship-approve < publish/deploy/release`.

`ship-approve` binds the working tree (`git status --porcelain` with
`.juicer/` removed), so every artifact must exist **before** approval, and
nothing outside `.juicer/` may change between approval and the release.

1. `reviewer` — final diff review.
2. `tester` — release test suite.
3. `security` — required for security-sensitive releases.
4. `devops` — build and package. Not production-impacting; runs before
   approval so the artifacts are part of the approved state.
5. Human approval before production-impacting actions — `./bin/juicer status`
   must show `ship_approved: true` (recorded by `./bin/juicer ship-approve`);
   stop while it is `false`.
6. `devops` — deploy or release. Production-impacting; requires the flag.
7. Validate the result and record release evidence in `.juicer/handoff.md`.
