from src.cli import main


def test_dry_run_never_pushes(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    (target / "a.txt").write_text("hi   \n")
    monkeypatch.setenv("BOT_PAT", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    rc = main(["--dry-run", "--repo-path", str(target), "--state", str(tmp_path / "s.json")])
    assert rc == 0
