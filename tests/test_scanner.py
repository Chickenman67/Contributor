from pathlib import Path
from src.scanner import load_candidates

def test_detects_whitespace_and_eof(tmp_path):
    f1 = tmp_path / "doc.md"
    f1.write_text("hello   \nworld\n")
    f2 = tmp_path / "ok.txt"
    f2.write_text("clean\n")
    f3 = tmp_path / "noeof.txt"
    f3.write_text("no newline at eof")
    cands = load_candidates(str(tmp_path))
    rules = {(c.file, c.rule) for c in cands}
    assert ("doc.md", "trailing-whitespace") in rules
    assert ("noeof.txt", "missing-eof-newline") in rules
    assert all(c.file != "ok.txt" for c in cands)

def test_detects_unpinned_action(tmp_path):
    wf = tmp_path / "action.yml"
    wf.write_text("steps:\n  - uses: actions/checkout@v4\n")
    cands = load_candidates(str(tmp_path))
    assert any(c.rule == "unpinned-action" and c.file == "action.yml" for c in cands)
