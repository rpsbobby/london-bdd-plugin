"""Regression suite for scripts/openai_implementer.py — the external
implementer backend. Covers the path guard directly (pure functions, no
network) and the entry-point's protocol-error contract through the real
CLI (subprocess), matching test_guard.py's conventions. Never calls the
real OpenAI API — that would need a live key and a network egress this
suite shouldn't depend on."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPT_DIR / "openai_implementer.py"

sys.path.insert(0, str(SCRIPT_DIR))
import openai_implementer as oi  # noqa: E402


def run_cli(stdin_payload, env=None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(stdin_payload),
        capture_output=True, text=True, env=env)
    return proc


# --- path guard: is_protected ------------------------------------------------

def test_protects_paths_under_tests_dir():
    assert oi.is_protected("tests/unit/OrderRepository_test.cpp")


def test_protects_paths_under_dot_bdd():
    assert oi.is_protected(".bdd/session.yml")


def test_protects_test_name_patterns_outside_tests_dir():
    assert oi.is_protected("src/order_service_test.py")
    assert oi.is_protected("src/OrderServiceTest.java")
    assert oi.is_protected("src/order.test.ts")


def test_allows_ordinary_production_paths():
    assert not oi.is_protected("src/pricing/OrderRepository.cpp")
    assert not oi.is_protected("src/pricing/OrderRepository.h")


# --- path guard: tool_write_file --------------------------------------------

def test_write_file_refuses_the_exact_test_file(tmp_path):
    changed = []
    result = oi.tool_write_file(
        str(tmp_path),
        {"path": "tests/unit/OrderRepository_test.cpp", "content": "x"},
        changed, test_file="tests/unit/OrderRepository_test.cpp")
    assert result.startswith("refused")
    assert changed == []
    assert not (tmp_path / "tests/unit/OrderRepository_test.cpp").exists()


def test_write_file_refuses_dot_bdd(tmp_path):
    changed = []
    result = oi.tool_write_file(
        str(tmp_path), {"path": ".bdd/session.yml", "content": "phase: done"},
        changed, test_file="tests/unit/x_test.py")
    assert result.startswith("refused")
    assert changed == []


def test_write_file_writes_production_code(tmp_path):
    changed = []
    result = oi.tool_write_file(
        str(tmp_path),
        {"path": "src/pricing/OrderRepository.cpp", "content": "// impl"},
        changed, test_file="tests/unit/x_test.py")
    assert result == "ok"
    assert changed == ["src/pricing/OrderRepository.cpp"]
    assert (tmp_path / "src/pricing/OrderRepository.cpp").read_text() == "// impl"


def test_resolve_blocks_path_escape(tmp_path):
    try:
        oi.resolve(str(tmp_path), "../../etc/passwd")
        assert False, "expected ProtocolError"
    except oi.ProtocolError:
        pass


# --- entry point: protocol errors, real CLI ---------------------------------

def test_missing_api_key_exits_1_with_message(tmp_path, monkeypatch):
    env = {"PATH": "/usr/bin:/bin"}  # no OPENAI_API_KEY
    proc = run_cli({"test": {"file": "tests/unit/x_test.py", "name": "n"},
                     "cwd": str(tmp_path)}, env=env)
    assert proc.returncode == 1
    assert "OPENAI_API_KEY" in proc.stderr


def test_invalid_stdin_json_exits_1(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], input="not json",
        capture_output=True, text=True)
    assert proc.returncode == 1
    assert "invalid JSON" in proc.stderr
