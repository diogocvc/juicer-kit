"use strict";

// Root guard for file-writing commands. Shared case table with the
// Python implementation in bin/juicer (root_guard_error):
//   uid 0         → refused, unless --force-root is given
//   any other uid → allowed
//   uid unknown   → allowed (platform without getuid)
// --yes is accepted by the CLI but never bypasses this guard.
function rootGuardError(options) {
  const opts = options || {};
  const uid = opts.uid;
  if (uid !== 0) return null;
  if (opts.forceRoot) return null;
  return "refusing to run as root without --force-root "
    + "(this writes project files; --yes does not bypass this guard)";
}

module.exports = { rootGuardError };
