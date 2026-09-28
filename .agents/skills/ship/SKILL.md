---
name: ship
description: Prepare and execute a controlled release with review, verification and explicit human approval for production impact.
---

# Ship

Required sequence:

1. review
2. test
3. security when applicable
4. build/package
5. human production approval — `./bin/juicer status` must show `ship_approved: true`; if it is `false`, stop and ask the human to run `./bin/juicer ship-approve`
6. release
7. record evidence

Never infer production approval, and never treat it as present without checking `.juicer/state.json` first.
