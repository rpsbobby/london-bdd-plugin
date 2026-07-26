"""Regression suite for scripts/codex_implementer.py — the Codex CLI
implementer backend. Covers path-guard/violation-detection logic against
real git repos (matching test_guard.py's "real behaviour, real repos"
convention) and the entry point's protocol-error contract through the
real CLI (subprocess). Never invokes the real `codex` binary — run_codex
is monkeypatched for the orchestration tests, since that would need a
live, authenticated Codex install this suite shouldn't depend on."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
SCRIPT = SCRIPT_DIR / "codex_implementer.py"

sys.path.insert(0, str(SCRIPT_DIR))
import codex_implementer as ci  # noqa: E402


def run_git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True,
                    capture_output=True, text=True)


def init_repo(repo):
    run_git(repo, "init", "-q")
    run_git(repo, "config", "user.email", "t@t.com")
    run_git(repo, "config", "user.name", "t")
    run_git(repo, "commit", "-q", "--allow-empty", "-m", "init")


def fake_proc(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


# --- path guard: is_protected -----------------------------------------------

def test_protects_paths_under_tests_dir():
    assert ci.is_protected("tests/unit/OrderRepository_test.cpp")


def test_protects_paths_under_dot_bdd():
    assert ci.is_protected(".bdd/session.yml")


def test_protects_test_name_patterns_outside_tests_dir():
    assert ci.is_protected("src/order_service_test.py")


def test_allows_ordinary_production_paths():
    assert not ci.is_protected("src/pricing/OrderRepository.cpp")


# --- git_status / find_violations -------------------------------------------

def test_git_status_reports_new_and_modified_files(tmp_path):
    init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("a")
    run_git(tmp_path, "add", "tracked.txt")
    run_git(tmp_path, "commit", "-q", "-m", "seed")
    (tmp_path / "tracked.txt").write_text("b")
    (tmp_path / "untracked.txt").write_text("c")
    status = ci.git_status(tmp_path)
    assert "tracked.txt" in status
    assert "untracked.txt" in status


def test_find_violations_flags_new_protected_path():
    before = {"src/x.py": " M"}
    after = {"src/x.py": " M", "tests/unit/x_test.py": "??"}
    assert ci.find_violations(before, after, "tests/unit/x_test.py") == [
        "tests/unit/x_test.py"]


def test_find_violations_ignores_new_production_paths():
    before = {}
    after = {"src/pricing/OrderRepository.cpp": "??"}
    assert ci.find_violations(before, after, "tests/unit/x_test.py") == []


# --- run(): orchestration, codex itself stubbed out -------------------------

def test_run_reports_green_when_tests_pass_and_no_violation(tmp_path, monkeypatch):
    init_repo(tmp_path)
    (tmp_path / "unit_x_test.py").write_text("original")  # RED step's dirt

    def write_prod_file(cwd, prompt, model, timeout):
        (tmp_path / "prod.py").write_text("impl")
        return fake_proc(0, "wrote prod.py")
    monkeypatch.setattr(ci, "run_codex", write_prod_file)

    context = {"test": {"file": "unit_x_test.py", "name": "n"},
               "test_command": "true", "cwd": str(tmp_path)}
    result = ci.run(context)
    assert result["status"] == "green"
    assert result["violation"] is None
    assert "prod.py" in result["files_changed"]


def test_run_reports_red_when_tests_fail(tmp_path, monkeypatch):
    init_repo(tmp_path)
    (tmp_path / "unit_x_test.py").write_text("original")
    monkeypatch.setattr(ci, "run_codex",
                         lambda cwd, prompt, model, timeout: fake_proc(0, "done"))
    context = {"test": {"file": "unit_x_test.py", "name": "n"},
               "test_command": "false", "cwd": str(tmp_path)}
    result = ci.run(context)
    assert result["status"] == "red"
    assert result["violation"] is None


def test_run_flags_violation_when_test_file_is_touched(tmp_path, monkeypatch):
    init_repo(tmp_path)
    (tmp_path / "unit_x_test.py").write_text("original")

    def tamper_with_test(cwd, prompt, model, timeout):
        (tmp_path / "unit_x_test.py").write_text("tampered")
        return fake_proc(0, "done")
    monkeypatch.setattr(ci, "run_codex", tamper_with_test)

    context = {"test": {"file": "unit_x_test.py", "name": "n"},
               "test_command": "true", "cwd": str(tmp_path)}
    result = ci.run(context)
    assert result["status"] == "red"
    assert result["violation"] is not None
    assert "unit_x_test.py" in result["violation"]["paths"]


def test_run_flags_violation_when_bdd_dir_is_touched(tmp_path, monkeypatch):
    init_repo(tmp_path)
    (tmp_path / "unit_x_test.py").write_text("original")

    def touch_bdd(cwd, prompt, model, timeout):
        bdd = tmp_path / ".bdd"
        bdd.mkdir(exist_ok=True)
        (bdd / "session.yml").write_text("phase: done")
        return fake_proc(0, "done")
    monkeypatch.setattr(ci, "run_codex", touch_bdd)

    context = {"test": {"file": "unit_x_test.py", "name": "n"},
               "test_command": "true", "cwd": str(tmp_path)}
    result = ci.run(context)
    assert result["status"] == "red"
    assert any(".bdd" in p for p in result["violation"]["paths"])


def test_run_reports_red_when_codex_exec_itself_fails(tmp_path, monkeypatch):
    init_repo(tmp_path)
    (tmp_path / "unit_x_test.py").write_text("original")
    monkeypatch.setattr(
        ci, "run_codex",
        lambda cwd, prompt, model, timeout: fake_proc(1, "", "boom"))
    context = {"test": {"file": "unit_x_test.py", "name": "n"},
               "test_command": "true", "cwd": str(tmp_path)}
    result = ci.run(context)
    assert result["status"] == "red"
    assert "boom" in result["summary"]


# --- entry point: protocol errors, real CLI ---------------------------------

def test_missing_codex_binary_exits_1(tmp_path):
    init_repo(tmp_path)
    (tmp_path / "unit_x_test.py").write_text("original")
    git_dir = str(Path(shutil.which("git")).parent)
    env = {"PATH": git_dir}  # git resolvable, codex is not
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"test": {"file": "unit_x_test.py", "name": "n"},
                           "test_command": "true", "cwd": str(tmp_path)}),
        capture_output=True, text=True, env=env)
    assert proc.returncode == 1
    assert "not on PATH" in proc.stderr


def test_invalid_stdin_json_exits_1():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)], input="not json",
        capture_output=True, text=True)
    assert proc.returncode == 1
    assert "invalid JSON" in proc.stderr
