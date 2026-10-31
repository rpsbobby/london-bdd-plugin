"""Regression suite for scripts/session.py — the validating writer for
.bdd/session.yml — through its real CLI, matching test_guard.py's style."""
import subprocess
import sys
from pathlib import Path

from test_guard import guard, init_repo, open_slice

SESSION = Path(__file__).resolve().parent.parent / "scripts" / "session.py"
sys.path.insert(0, str(SESSION.parent))
import guard as guard_mod  # noqa: E402

GOOD = """\
slice: place-order
mode: GREENFIELD
phase: inner
inner: batch
checks:
  tests: uv run pytest {files}
branch: feature/place-order-tmp
base_branch: feature/place-order-main
acceptance_test:
  file: tests/acceptance/place_order_test.py
  name: PlaceOrder.ReturnsId
  status: red
collaborators:
  - role: OrderService
    status: red
  - role: OrderRepository
    status: pending
tests:
  - name: should_place_order
    collaborator: OrderService
    origin: planned
    status: red
  - name: should_save_order
    collaborator: OrderRepository
    origin: planned
    status: pending
discovery_rounds: 0
current_failing_test:
  file: tests/unit/order_service_test.py
  name: OrderService.PlacesOrder

cycle: 3
last_commit: "cycle 3: earlier"
"""


def run(*args):
    proc = subprocess.run([sys.executable, str(SESSION), *map(str, args)],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def session_file(tmp_path, text=GOOD):
    p = tmp_path / "session.yml"
    p.write_text(text)
    return p


# ---- validate ---------------------------------------------------------

def test_validate_passes_good_file(tmp_path):
    code, out, _ = run("validate", session_file(tmp_path))
    assert code == 0 and out.startswith("ok")


def test_validate_flags_stray_keys_under_collaborators(tmp_path):
    bad = GOOD.replace("    status: red\n  - role: OrderRepository",
                       "    status: red\n    file: x\n    name: y\n"
                       "  - role: OrderRepository")
    code, _, err = run("validate", session_file(tmp_path, bad))
    assert code != 0 and "stray key" in err


def test_validate_flags_missing_cycle(tmp_path):
    code, _, err = run("validate", session_file(
        tmp_path, GOOD.replace("cycle: 3\n", "")))
    assert code != 0 and "'cycle'" in err


def test_validate_flags_non_integer_cycle(tmp_path):
    code, _, err = run("validate", session_file(
        tmp_path, GOOD.replace("cycle: 3", "cycle: three")))
    assert code != 0 and "cycle" in err


def test_validate_flags_bad_enums(tmp_path):
    bad = (GOOD.replace("phase: inner", "phase: middle")
           .replace("mode: GREENFIELD", "mode: YOLO")
           .replace("inner: batch", "inner: sometimes")
           .replace("origin: planned\n    status: pending",
                    "origin: guessed\n    status: stuck"))
    code, _, err = run("validate", session_file(tmp_path, bad))
    assert code != 0
    for what in ("phase", "mode", "inner", "origin", "tests[2].status"):
        assert what in err


def test_validate_flags_test_with_unknown_collaborator(tmp_path):
    bad = GOOD.replace("collaborator: OrderRepository",
                       "collaborator: Ghost")
    code, _, err = run("validate", session_file(tmp_path, bad))
    assert code != 0 and "Ghost" in err


def test_validate_reports_every_problem_at_once(tmp_path):
    bad = GOOD.replace("cycle: 3\n", "").replace("phase: inner",
                                                  "phase: nope")
    _, _, err = run("validate", session_file(tmp_path, bad))
    assert err.count("error:") >= 2


def test_validate_warns_but_passes_on_unknown_top_level_key(tmp_path):
    code, _, err = run("validate", session_file(tmp_path, GOOD + "extra: 1\n"))
    assert code == 0 and "warning" in err and "extra" in err


def test_validate_missing_file_fails(tmp_path):
    code, _, _ = run("validate", tmp_path / "nope.yml")
    assert code != 0


# ---- updates ----------------------------------------------------------

def test_set_test_changes_only_that_test(tmp_path):
    p = session_file(tmp_path)
    code, _, _ = run("set-test", "should_place_order", "--status", "green",
                     "--file", p)
    assert code == 0
    s = guard_mod.parse_session(str(p))
    assert [t["status"] for t in s["tests"]] == ["green", "pending"]
    assert s["phase"] == "inner"


def test_set_test_rejects_bad_status_and_unknown_name(tmp_path):
    p = session_file(tmp_path)
    assert run("set-test", "should_place_order", "--status", "bogus",
               "--file", p)[0] != 0
    assert run("set-test", "nope", "--status", "done", "--file", p)[0] != 0
    assert p.read_text() == GOOD


def test_set_collaborator(tmp_path):
    p = session_file(tmp_path)
    code, _, _ = run("set-collaborator", "OrderService", "--status", "done",
                     "--file", p)
    assert code == 0
    s = guard_mod.parse_session(str(p))
    assert [c["status"] for c in s["collaborators"]] == ["done", "pending"]


def test_commit_cycle_bumps_cycle_sets_last_commit_clears_failing(tmp_path):
    p = session_file(tmp_path)
    code, _, _ = run("commit-cycle", "--message", "cycle 4: A: does B",
                     "--file", p)
    assert code == 0
    s = guard_mod.parse_session(str(p))
    assert s["cycle"] == 4 and not s["current_failing_test"]
    assert 'last_commit: "cycle 4: A: does B"' in p.read_text()
    assert run("validate", p)[0] == 0


def test_set_failing_test_records_file_and_name(tmp_path):
    p = session_file(tmp_path)
    run("commit-cycle", "--message", "m", "--file", p)
    code, _, _ = run("set-failing-test", "--test-file", "tests/u_test.py",
                     "--name", "U.Does", "--file", p)
    assert code == 0
    assert guard_mod.parse_session(str(p))["current_failing_test"]
    assert "name: U.Does" in p.read_text()
    assert p.read_text().count("current_failing_test:") == 1


def test_set_discovery_rounds(tmp_path):
    p = session_file(tmp_path)
    assert run("set-discovery-rounds", "1", "--file", p)[0] == 0
    assert "discovery_rounds: 1" in p.read_text()
    assert run("set-discovery-rounds", "2", "--file", p)[0] != 0


def test_update_can_repair_missing_cycle_and_last_commit(tmp_path):
    broken = GOOD.replace("cycle: 3\n", "").replace(
        'last_commit: "cycle 3: earlier"\n', "")
    p = session_file(tmp_path, broken)
    assert run("validate", p)[0] != 0
    code, _, _ = run("commit-cycle", "--message", "cycle 1: x", "--file", p)
    assert code == 0 and run("validate", p)[0] == 0
    assert guard_mod.parse_session(str(p))["cycle"] == 1


def test_write_checked_refuses_new_problem_and_keeps_file(tmp_path):
    import session as session_mod
    p = session_file(tmp_path)
    broken = GOOD.replace("cycle: 3\n", "")
    assert session_mod.write_checked(str(p), broken) == 1
    assert p.read_text() == GOOD
    assert [f.name for f in tmp_path.iterdir()] == ["session.yml"]
    # a problem the file already had does not block an unrelated update
    p.write_text(broken)
    old, _ = session_mod.problems(broken, str(p))
    assert session_mod.write_checked(
        str(p), broken.replace("red\n  - role", "done\n  - role"), old) == 0


def test_update_leaves_no_temp_files(tmp_path):
    p = session_file(tmp_path)
    run("set-test", "should_place_order", "--status", "done", "--file", p)
    run("set-test", "nope", "--status", "done", "--file", p)
    assert [f.name for f in tmp_path.iterdir()] == ["session.yml"]


def test_default_path_finds_nearest_session(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x", phase="inner", cycle=0)
    # open_slice's file lacks collaborators; validate still locates it
    proc = subprocess.run(
        [sys.executable, str(SESSION), "validate"], cwd=tmp_path,
        capture_output=True, text=True)
    assert "session.yml" in proc.stdout + proc.stderr


# ---- phase / guard interaction ---------------------------------------

def test_helper_never_changes_phase(tmp_path):
    p = session_file(tmp_path)
    run("set-test", "should_place_order", "--status", "done", "--file", p)
    run("commit-cycle", "--message", "m", "--file", p)
    run("set-discovery-rounds", "1", "--file", p)
    assert "phase: inner\n" in p.read_text()


def test_guard_does_not_block_helper_invocations(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x")
    for cmd in (
        "python3 /plug/scripts/session.py validate .bdd/session.yml",
        "python3 /plug/scripts/session.py commit-cycle --message "
        "'cycle 1: a > b' --file .bdd/session.yml",
        "python3 /plug/scripts/session.py validate 2>&1",
    ):
        code, err = guard(tmp_path, "bash", command=cmd)
        assert code != 2, err


def test_guard_still_blocks_redirect_to_session_yml(tmp_path):
    init_repo(tmp_path)
    open_slice(tmp_path, "x")
    code, err = guard(tmp_path, "bash",
                      command="python3 s.py init > .bdd/session.yml")
    assert code == 2 and "Rule D" in err
