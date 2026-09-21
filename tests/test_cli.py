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


def test_live_refuses_external_repo(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    (target / "a.txt").write_text("hi   \n")
    monkeypatch.setenv("BOT_PAT", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.setenv("GITHUB_REPOSITORY", "someone-else/other")
    rc = main(["--repo-path", str(target), "--state", str(tmp_path / "s.json")])
    assert rc == 2


def test_apply_patch_via_git(tmp_path):
    import subprocess
    from src.pr_bot import apply_patch_via_git

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=str(tmp_path), capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "t"], cwd=str(tmp_path), capture_output=True
    )
    (tmp_path / "a.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-hello\n+hello world\n"
    assert apply_patch_via_git(str(tmp_path), patch) is True
    assert (tmp_path / "a.txt").read_text() == "hello world\n"
    assert apply_patch_via_git(str(tmp_path), "not a patch") is False
