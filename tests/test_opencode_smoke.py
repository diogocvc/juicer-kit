"""Opt-in smoke against the real OpenCode V2 binary.

Run with:

    JUICER_OPENCODE_SMOKE=1 uv tool run pytest -q tests/test_opencode_smoke.py

This test makes a real model call. It is skipped by default so the normal
suite stays deterministic and offline.
"""

from __future__ import annotations

import os

import pytest

from juicer.harness import opencode
from juicer.harness.contract import ExecutionRequest


pytestmark = pytest.mark.skipif(
    os.environ.get("JUICER_OPENCODE_SMOKE") != "1",
    reason="set JUICER_OPENCODE_SMOKE=1 to run the real OpenCode smoke",
)


def test_real_opencode_v2_smoke(tmp_path):
    info = opencode.discover()
    assert info["status"] in ("supported", "degraded"), info["detail"]
    assert info["binary"]
    assert info["version"]
    assert info["capabilities"]["v2"] is True, info
    assert info["capabilities"]["run_json"] is True
    assert info["capabilities"]["standalone_flag"] is True

    request = ExecutionRequest(
        prompt="Reply with exactly SMOKE-OK-7Q2. Do not edit any files.",
        cwd=tmp_path,
        timeout=180,
    )
    result = opencode.run(request)
    assert result.ok, result.detail
    assert result.exit_code == 0
    assert result.session_id
    assert "--standalone" in (result.command or [])
    assert "--dir" not in (result.command or [])
    parsed = opencode.parse_run_output(result.output)
    assert "SMOKE-OK-7Q2" in parsed["text"]
