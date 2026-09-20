from src.state import load_state, save_state, is_blocklisted, record_closed, already_tried

def test_blocklist_and_idempotency(tmp_path):
    p = tmp_path / "s.json"
    p.write_text('{"closed_prs": [], "blocklisted": {}}')
    state = load_state(str(p))
    assert is_blocklisted(state, "o/r", "2026-09-20") is False
    state["blocklisted"]["o/r"] = "2026-09-27"
    assert is_blocklisted(state, "o/r", "2026-09-20") is True
    assert is_blocklisted(state, "o/r", "2026-09-28") is False
    record_closed(state, "ai/typo-20260920", "fix: typo")
    assert already_tried(state, "ai/typo-20260920", "fix: typo") is True
    assert already_tried(state, "ai/other-20260920", "fix: typo") is False
    save_state(str(p), state)
    reloaded = load_state(str(p))
    assert already_tried(reloaded, "ai/typo-20260920", "fix: typo") is True
