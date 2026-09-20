from src.ai_providers import create_provider, should_retry, GeminiProvider, GrokProvider, MistralProvider

def test_factory_names():
    assert isinstance(create_provider("gemini", "k"), GeminiProvider)
    assert isinstance(create_provider("grok", "k"), GrokProvider)
    assert isinstance(create_provider("mistral", "k"), MistralProvider)

def test_retry_policy():
    assert should_retry(429) is True
    assert should_retry(500) is True
    assert should_retry(400) is False
    assert should_retry(200) is False

def test_prompt_constrains_diff_size(monkeypatch):
    captured = {}
    import src.ai_providers as m
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["body"] = json
        class R:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "diff-ok"}}]}
            def raise_for_status(self):
                pass
        return R()
    monkeypatch.setattr(m.requests, "post", fake_post)
    p = create_provider("mistral", "k")
    from src.scanner import Candidate
    out = p.generate_fix(Candidate("a.md", "trailing-whitespace", "x", "ctx"), "file text")
    assert out == "diff-ok"
    assert captured["body"]["model"] == "mistral-large-latest"


def test_grok_model_name(monkeypatch):
    captured = {}
    import src.ai_providers as m
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["body"] = json
        class R:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "diff-ok"}}]}
            def raise_for_status(self):
                pass
        return R()
    monkeypatch.setattr(m.requests, "post", fake_post)
    p = create_provider("grok", "k")
    from src.scanner import Candidate
    out = p.generate_fix(Candidate("a.md", "trailing-whitespace", "x", "ctx"), "file text")
    assert out == "diff-ok"
    assert captured["body"]["model"] == "grok-4-latest"
