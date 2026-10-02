"use strict";

// Payload materialization and the .juicer/install.json manifest.
// The payload list is package.json's "files": the single allowlist for
// what ships in the tarball and what lands in .juicer-kit/. "npm/"
// entries are the installer itself and are never copied into projects.
// Writes are byte-idempotent; the manifest keeps installed_at across
// runs that change neither kit version nor payload bytes.

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const KIT_DIR = ".juicer-kit";
const MANIFEST_PATH = path.join(".juicer", "install.json");

function sha256Hex(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    return null;
  }
}

function walkFiles(dir, prefix, out, isExcluded) {
  const names = fs.readdirSync(dir).sort();
  for (const name of names) {
    // npm always excludes .DS_Store from tarballs; mirror that here so
    // the payload matches between a git checkout and an installed package.
    if (name === ".DS_Store") continue;
    const abs = path.join(dir, name);
    const rel = prefix ? `${prefix}/${name}` : name;
    if (isExcluded(rel)) continue;
    const stat = fs.statSync(abs);
    if (stat.isDirectory()) walkFiles(abs, rel, out, isExcluded);
    else if (stat.isFile()) out.push({ rel, abs });
  }
  return out;
}

function globToRegExp(glob) {
  let out = "";
  for (let i = 0; i < glob.length; i++) {
    const ch = glob[i];
    if (ch === "*") {
      if (glob[i + 1] === "*") {
        if (glob[i + 2] === "/") {
          out += "(?:[^/]+/)*";
          i += 2;
        } else {
          out += ".*";
          i += 1;
        }
      } else {
        out += "[^/]*";
      }
    } else if (ch === "?") {
      out += "[^/]";
    } else {
      out += ch.replace(/[.+^${}()|[\]\\]/g, "\\$&");
    }
  }
  return new RegExp(`^${out}$`);
}

function payloadPlan(fileEntries) {
  const positives = [];
  const matchers = [];
  for (const entry of fileEntries || []) {
    if (entry.startsWith("!")) {
      const pattern = entry.slice(1);
      matchers.push(globToRegExp(pattern));
    } else if (!entry.startsWith("npm/")) {
      positives.push(entry);
    }
  }
  const isExcluded = (rel) => matchers.some((re) => re.test(rel));
  return { positives, isExcluded };
}

function collectEntry(packageRoot, entry, isExcluded) {
  const src = path.join(packageRoot, ...entry.split("/"));
  if (isExcluded(entry)) return [];
  const stat = fs.statSync(src);
  if (stat.isDirectory()) return walkFiles(src, entry, [], isExcluded);
  if (stat.isFile()) return [{ rel: entry, abs: src }];
  throw new Error(`payload entry is neither file nor directory: ${entry}`);
}

function destPath(projectRoot, rel) {
  return path.join(projectRoot, KIT_DIR, ...rel.split("/"));
}

function materialize(packageRoot, projectRoot, entries, isExcluded) {
  const exclude = isExcluded || (() => false);
  const files = {};
  let updated = 0;
  for (const entry of entries) {
    for (const item of collectEntry(packageRoot, entry, exclude)) {
      const buffer = fs.readFileSync(item.abs);
      files[item.rel] = sha256Hex(buffer);
      const dest = destPath(projectRoot, item.rel);
      let identical = false;
      try {
        identical = fs.readFileSync(dest).equals(buffer);
      } catch (error) {
        identical = false;
      }
      if (!identical) {
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, buffer);
        updated += 1;
      }
    }
  }
  return { files, updated };
}

function readManifest(projectRoot) {
  const found = readJson(path.join(projectRoot, MANIFEST_PATH));
  return found && found.schema === 1 && found.files ? found : null;
}

function compareVersions(a, b) {
  const parse = (v) => String(v).split("-")[0].split(".").map((n) => parseInt(n, 10) || 0);
  const left = parse(a);
  const right = parse(b);
  for (let i = 0; i < 3; i++) {
    if ((left[i] || 0) !== (right[i] || 0)) return (left[i] || 0) - (right[i] || 0);
  }
  return 0;
}

// Manifest-driven update: refresh what the manifest proves untouched,
// keep what the user edited (unless --force), prune stale kit files
// whose recorded hash still matches. No manifest (legacy layout) →
// adopt: only fill in missing files, never overwrite, never prune.
function updatePayload(packageRoot, projectRoot, entries, isExcluded, options) {
  const force = Boolean(options && options.force);
  const prev = readManifest(projectRoot);
  const prevFiles = prev ? prev.files : {};
  const exclude = isExcluded || (() => false);
  const stats = { written: 0, unchanged: 0, kept: 0, pruned: 0 };
  const kept = [];
  const pruned = [];
  const files = {};
  const seen = new Set();

  for (const entry of entries) {
    for (const item of collectEntry(packageRoot, entry, exclude)) {
      seen.add(item.rel);
      const buffer = fs.readFileSync(item.abs);
      files[item.rel] = sha256Hex(buffer);
      const dest = destPath(projectRoot, item.rel);
      let destBuf = null;
      try {
        destBuf = fs.readFileSync(dest);
      } catch (error) {
        destBuf = null;
      }
      if (destBuf === null) {
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, buffer);
        stats.written += 1;
        continue;
      }
      if (destBuf.equals(buffer)) {
        stats.unchanged += 1;
        continue;
      }
      const destHash = sha256Hex(destBuf);
      const destUnmodified = prevFiles[item.rel] !== undefined
        && destHash === prevFiles[item.rel];
      if (destUnmodified || force) {
        fs.writeFileSync(dest, buffer);
        stats.written += 1;
      } else {
        stats.kept += 1;
        kept.push(item.rel);
      }
    }
  }

  for (const rel of Object.keys(prevFiles).sort()) {
    if (seen.has(rel)) continue;
    const dest = destPath(projectRoot, rel);
    let destBuf = null;
    try {
      destBuf = fs.readFileSync(dest);
    } catch (error) {
      continue;
    }
    const destUnmodified = sha256Hex(destBuf) === prevFiles[rel];
    if (destUnmodified || force) {
      fs.unlinkSync(dest);
      stats.pruned += 1;
      pruned.push(rel);
    } else {
      stats.kept += 1;
      kept.push(rel);
    }
  }

  return {
    stats, kept, pruned, legacy: prev === null, previous: prev, files,
  };
}

function sortedFileMap(files) {
  const sorted = {};
  for (const key of Object.keys(files).sort()) sorted[key] = files[key];
  return sorted;
}

function writeManifest(projectRoot, kitVersion, files) {
  const manifestFile = path.join(projectRoot, MANIFEST_PATH);
  const existing = readJson(manifestFile);
  const sorted = sortedFileMap(files);
  const current = Boolean(existing && existing.schema === 1);
  if (current && existing.kit_version === kitVersion
      && JSON.stringify(existing.files) === JSON.stringify(sorted)) {
    return "unchanged";
  }
  const sameVersion = Boolean(current && existing.kit_version === kitVersion);
  const next = {
    schema: 1,
    kit_version: kitVersion,
    installed_at: sameVersion && existing.installed_at
      ? existing.installed_at
      : new Date().toISOString(),
    files: sorted,
  };
  fs.mkdirSync(path.dirname(manifestFile), { recursive: true });
  fs.writeFileSync(manifestFile, `${JSON.stringify(next, null, 2)}\n`);
  return existing ? "updated" : "installed";
}

function pythonVersionError(output) {
  const match = /^(\d+)\.(\d+)/.exec(String(output).trim());
  if (!match) {
    return `could not read a python3 version from: ${JSON.stringify(String(output).slice(0, 40))}`;
  }
  const major = Number(match[1]);
  const minor = Number(match[2]);
  if (major > 3 || (major === 3 && minor >= 8)) return null;
  return `python3 ${major}.${minor} found; Juicer Kit requires Python >= 3.8`;
}

module.exports = {
  KIT_DIR,
  MANIFEST_PATH,
  materialize,
  payloadPlan,
  readManifest,
  compareVersions,
  updatePayload,
  writeManifest,
  pythonVersionError,
  sha256Hex,
};
