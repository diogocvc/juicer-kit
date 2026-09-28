# Release Workflow

1. `reviewer` — final diff review.
2. `tester` — release test suite.
3. `security` — required for security-sensitive releases.
4. Human approval before production-impacting actions — `./bin/juicer status` must show `ship_approved: true` (recorded by `./bin/juicer ship-approve`); stop while it is `false`.
5. `devops` — build, package, deploy or release.
6. Record release evidence in `.juicer/handoff.md`.
