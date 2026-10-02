"""Documentation consistency guards.

Phase 0 audit: no placeholder tokens in tracked files, one canonical
repository URL, version unity between VERSION, README and the guides,
no broken install claims, no instruction to commit generated mirrors or
copy the live `.juicer/` state, `init` before `sync` in the migration
path, and `.gitignore` coverage of `PROJECT_MIRRORS`.
"""

import importlib.machinery
import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

KIT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
CANONICAL_URL = "https://github.com/diogocvc/juicer-kit"
VERSION = (KIT / "VERSION").read_text().strip()

FORBIDDEN = [re.compile(p, re.I) for p in (
    r"your[-_]username",
    r"github\.com/your",
    r"github\.com/owner",
    r"@backlog",
)]

CURRENT_VERSION_DOCS = ("README.md", "docs/GUIDE.md", "docs/GUIDE.pt-BR.md")


def load_cli(name="juicer_cli_docs_test"):
    loader = importlib.machinery.SourceFileLoader(name, str(KIT / "bin" / "juicer"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_no_placeholder_tokens_in_tracked_files():
    out = subprocess.run(["git", "-C", str(KIT), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    offenders = []
    for rel in out.splitlines():
        path = KIT / rel
        if not path.is_file() or path.resolve() == SELF:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in FORBIDDEN:
            if pattern.search(text):
                offenders.append(f"{rel}: {pattern.pattern}")
    assert not offenders, offenders


def test_readme_has_canonical_repository_url():
    assert CANONICAL_URL in (KIT / "README.md").read_text()


def test_readme_title_matches_version_file():
    first = (KIT / "README.md").read_text().splitlines()[0]
    assert first == f"# Juicer Kit v{VERSION}"


def test_guides_and_readme_use_current_version_only():
    """One version repo-wide: every vN.N(.N) token equals VERSION."""
    for rel in CURRENT_VERSION_DOCS:
        found = set(re.findall(r"v\d+\.\d+(?:\.\d+)?", (KIT / rel).read_text()))
        assert found == {f"v{VERSION}"}, f"{rel}: {found}"


def test_changelog_has_current_version_entry():
    assert f"## {VERSION}" in (KIT / "CHANGELOG.md").read_text()


def test_readme_does_not_instruct_committing_mirrors():
    """A commit instruction mentioning mirrors/generated adapters needs a
    negation; guidance to leave them uncommitted is allowed."""
    text = (KIT / "README.md").read_text()
    bad = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        low = sentence.lower()
        if not re.search(r"\bcommit(?:s|ted|ting)?\b", low):
            continue
        if not re.search(r"\bmirror|generated adapter", low):
            continue
        if not re.search(r"\b(?:not|never|no|n't)\b", low):
            bad.append(sentence.strip())
    assert not bad, bad


def test_readme_does_not_copy_live_kit_state():
    text = (KIT / "README.md").read_text()
    assert "juicer-kit-v2" not in text
    assert re.search(r"\brm\s+-rf\s+\.juicer\b", text) is None
    assert re.search(r"cp\s+-R\s+\S*juicer-kit\S*/\.(?:juicer|agents)", text) is None


def test_installation_doc_install_claims():
    text = (KIT / "docs" / "installation.md").read_text()
    assert "Or copy `bin/juicer` somewhere on your PATH" not in text
    assert "must stay inside the kit" in text
    assert CANONICAL_URL in text
    assert "./juicer-kit/bin/juicer init" in text
    assert "npx @juicer-kit/cli install" in text
    assert "npx @juicer-kit/cli update" in text
    assert "--force-root" in text


def test_migration_doc_runs_init_before_sync():
    text = (KIT / "docs" / "migration-v1.md").read_text()
    i_init = text.index("juicer init")
    i_sync = text.index("juicer sync all")
    assert i_init < i_sync


def test_adapter_contract_uses_canonical_workflow_path():
    text = (KIT / "docs" / "adapter-contract.md").read_text()
    assert re.search(r"(?m)^\s*workflows/\s*$", text) is None
    assert ".juicer/workflows/" in text


def test_gitignore_covers_project_mirrors():
    module = load_cli()
    lines = set((KIT / ".gitignore").read_text().splitlines())
    missing = [m for m in module.PROJECT_MIRRORS if m not in lines]
    assert not missing, missing


def test_tests_readme_lists_every_suite():
    readme = (KIT / "tests" / "README.md").read_text()
    missing = [p.name for p in sorted((KIT / "tests").glob("test_*.py"))
               if p.name not in readme]
    assert not missing, missing
