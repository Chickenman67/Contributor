from src.pr_bot import build_branch_name, build_pr_title, build_pr_body, diff_line_count
from src.scanner import Candidate

def test_builders_and_gate():
    c = Candidate("docs/a.md", "trailing-whitespace", "line 3", "ctx")
    assert build_branch_name("trailing-whitespace", "20260920") == "ai/trailing-whitespace-20260920"
    assert "trailing-whitespace" in build_pr_title(c)
    body = build_pr_body(c, "ruff ok", "bot", "owner")
    assert "AI-assisted" in body and "bot" in body and "owner" in body and "ruff ok" in body
    assert diff_line_count("a\nb\nc") == 3
    assert diff_line_count("\n".join([f"l{i}" for i in range(250)])) == 250


def test_gate_blocks_over_limits():
    from src.pr_bot import exceeds_caps
    big_diff = "\n".join([f"l{i}" for i in range(250)])
    assert exceeds_caps(6, 0, "small") is True
    assert exceeds_caps(0, 2, "small") is True
    assert exceeds_caps(0, 0, big_diff) is True
    assert exceeds_caps(1, 0, "small") is False
