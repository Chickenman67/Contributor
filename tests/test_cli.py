from src.cli import main
from src.state import load_state


def test_dry_run_never_pushes(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    (target / "a.txt").write_text("hi   \n")
    monkeypatch.setenv("BOT_PAT", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    rc = main(["--dry-run", "--repo-path", str(target), "--state", str(tmp_path / "s.json")])
    assert rc == 0


def test_dry_run_leaves_state_unchanged(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    (target / "a.txt").write_text("hi   \n")
    state_file = tmp_path / "s.json"
    state_file.write_text('{"closed_prs": [], "blocklisted": {}}')
    monkeypatch.setenv("BOT_PAT", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    state_before = load_state(str(state_file))
    rc = main(["--dry-run", "--repo-path", str(target), "--state", str(state_file)])
    assert rc == 0
    state_after = load_state(str(state_file))
    assert state_after == state_before
