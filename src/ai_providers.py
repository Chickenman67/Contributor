"""Pluggable AI backends: Gemini default, Grok + Mistral optional.

Live calls require valid API keys:
- Gemini: GEMINI_API_KEY (models/gemini-2.0-flash)
- Grok: XAI_API_KEY (model grok-4-latest, x.ai API)
- Mistral: MISTRAL_API_KEY (model mistral-large-latest, api.mistral.ai)

Rate limits per provider docs:
- xAI: 60 RPM / 1000 RPD (grok-4-latest)
- Mistral: 100 RPM / 5000 RPD (mistral-large-latest)
"""
from __future__ import annotations
import time
import requests
from src.scanner import Candidate

TIMEOUT = 60

SYSTEM_PROMPT = (
    "You fix only the reported safe issue. Output a unified diff only, "
    "max 200 lines. Never strip license headers. No explanations."
)


def should_retry(status: int) -> bool:
    return status == 429 or 500 <= status <= 599


def _post_with_backoff(url: str, headers: dict, payload: dict, tries: int = 3) -> requests.Response:
    delay = 2.0
    last: requests.Response | None = None
    for _ in range(tries):
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        if not should_retry(resp.status_code):
            return resp
        retry_after = resp.headers.get("retry-after")
        time.sleep(float(retry_after) if retry_after else delay)
        delay = min(delay * 4, 30.0)
        last = resp
    assert last is not None
    return last


class AiProvider:
    name: str = "base"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def generate_fix(self, candidate: Candidate, file_text: str) -> str | None:
        raise NotImplementedError


class GeminiProvider(AiProvider):
    name = "gemini"

    def generate_fix(self, candidate: Candidate, file_text: str) -> str | None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\nRule: {candidate.rule}\nFile: {candidate.file}\nExcerpt: {candidate.excerpt}\nContent:\n{file_text[:8000]}"}]}]}
        resp = _post_with_backoff(url, {}, payload)
        if resp.status_code != 200:
            return None
        try:
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts) or None
        except (KeyError, IndexError, TypeError):
            return None


class _OpenAIChatProvider(AiProvider):
    base_url: str = ""
    model: str = ""

    def generate_fix(self, candidate: Candidate, file_text: str) -> str | None:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Rule: {candidate.rule}\nFile: {candidate.file}\nExcerpt: {candidate.excerpt}\nContent:\n{file_text[:8000]}"},
            ],
        }
        resp = _post_with_backoff(url, {"Authorization": f"Bearer {self.api_key}"}, payload)
        if resp.status_code != 200:
            return None
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None


class GrokProvider(_OpenAIChatProvider):
    name = "grok"
    base_url = "https://api.x.ai/v1"
    model = "grok-4-latest"


class MistralProvider(_OpenAIChatProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"
    model = "mistral-large-latest"


def create_provider(name: str, api_key: str) -> AiProvider:
    key = name.lower()
    if key == "gemini":
        return GeminiProvider(api_key)
    if key == "grok":
        return GrokProvider(api_key)
    if key == "mistral":
        return MistralProvider(api_key)
    raise ValueError(f"unknown provider: {name}")
