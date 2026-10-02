#!/usr/bin/env node
"use strict";

// @juicer-kit/cli — npm entrypoint. Materializes the kit payload into
// .juicer-kit/, records .juicer/install.json, then runs the kit's own
// `juicer init` under python3 (>= 3.8). The root guard runs before any
// file is written or Python is launched; --yes never bypasses it.

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { rootGuardError } = require("../lib/root-guard.js");
const {
  materialize,
  payloadPlan,
  writeManifest,
  pythonVersionError,
} = require("../lib/install.js");

const packageRoot = path.resolve(__dirname, "..", "..");
const pkg = JSON.parse(fs.readFileSync(path.join(packageRoot, "package.json"), "utf8"));

const USAGE = [
  "usage: juicer-kit <command> [options]",
  "",
  "commands:",
  "  install       materialize the kit into .juicer-kit/ and run juicer init",
  "",
  "options:",
  "  --force-root  allow running as root (normally refused)",
  "  --yes         accepted for automation; does not bypass the root guard",
  "  --version     print the package version",
  "  --help        show this help",
  "",
].join("\n");

function install(forceRoot) {
  const uid = typeof process.getuid === "function" ? process.getuid() : null;
  const refusal = rootGuardError({ uid, forceRoot });
  if (refusal) {
    console.error(`juicer-kit: ${refusal}`);
    return 1;
  }
  const plan = payloadPlan(pkg.files);
  if (plan.positives.length === 0) {
    console.error('juicer-kit: package.json "files" has no payload entries');
    return 1;
  }
  const projectRoot = process.cwd();
  const payload = materialize(packageRoot, projectRoot, plan.positives, plan.isExcluded);
  console.log(
    `kit payload: ${Object.keys(payload.files).length} files `
    + `(${payload.updated} written) under .juicer-kit/`,
  );
  const manifestState = writeManifest(projectRoot, pkg.version, payload.files);
  console.log(`install manifest: ${manifestState} (.juicer/install.json)`);

  const probe = spawnSync(
    "python3",
    ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
    { encoding: "utf8" },
  );
  if (probe.error) {
    console.error("juicer-kit: python3 not found — Juicer Kit requires Python >= 3.8");
    return 1;
  }
  if (probe.status !== 0) {
    const detail = probe.stderr ? `: ${probe.stderr.trim()}` : "";
    console.error(`juicer-kit: unable to query python3${detail}`);
    return 1;
  }
  const versionProblem = pythonVersionError(probe.stdout);
  if (versionProblem) {
    console.error(`juicer-kit: ${versionProblem}`);
    return 1;
  }

  const kitCli = path.join(projectRoot, ".juicer-kit", "bin", "juicer");
  const initArgs = [kitCli, "init"];
  if (forceRoot) initArgs.push("--force-root");
  console.log("running: python3 .juicer-kit/bin/juicer init");
  const init = spawnSync("python3", initArgs, { cwd: projectRoot, stdio: "inherit" });
  if (init.error) {
    console.error(`juicer-kit: failed to launch juicer init: ${init.error.message}`);
    return 1;
  }
  return init.status === null || init.status === undefined ? 1 : init.status;
}

function main(argv) {
  let forceRoot = false;
  let wantHelp = false;
  let wantVersion = false;
  const positional = [];
  for (const arg of argv.slice(2)) {
    if (arg === "--force-root") forceRoot = true;
    else if (arg === "--yes" || arg === "-y") { /* accepted; never bypasses the root guard */ }
    else if (arg === "--help" || arg === "-h") wantHelp = true;
    else if (arg === "--version" || arg === "-v") wantVersion = true;
    else if (arg.startsWith("-")) {
      console.error(`juicer-kit: unknown option ${arg}`);
      console.error(USAGE);
      return 1;
    } else positional.push(arg);
  }
  if (wantHelp) {
    console.log(USAGE);
    return 0;
  }
  if (wantVersion) {
    console.log(pkg.version);
    return 0;
  }
  const command = positional[0];
  if (command === "install") return install(forceRoot);
  console.error(
    command === undefined
      ? "juicer-kit: missing command"
      : `juicer-kit: unknown command ${command}`,
  );
  console.error(USAGE);
  return 1;
}

try {
  process.exit(main(process.argv));
} catch (error) {
  console.error(`juicer-kit: ${error && error.message ? error.message : error}`);
  process.exit(1);
}
