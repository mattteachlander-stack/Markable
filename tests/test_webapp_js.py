"""Bridge: run the node unit tests for the browser bundle's pure module."""

import shutil
import subprocess

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_pure_suite():
    out = subprocess.run(
        ["node", "--test", "tests/js/pure.test.mjs"],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0, out.stdout + out.stderr
