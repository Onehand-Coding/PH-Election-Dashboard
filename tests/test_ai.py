import json

import pandas as pd

from ph_election_dashboard import ai


def sample_frame():
    return pd.DataFrame(
        {
            "position": ["Senator"] * 6,
            "candidate_name": [f"Candidate {index}" for index in range(1, 7)],
            "party": [
                "Party A",
                "Party B",
                "Party A",
                "Party B",
                "Party A",
                "Party B",
            ],
            "total_votes": [60, 50, 40, 30, 20, 10],
            "region": [
                "Luzon",
                "Visayas",
                "Luzon",
                "Visayas",
                "Luzon",
                "Visayas",
            ],
        }
    )


def test_provider_key_lookup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    provider = ai.BUILTIN_PROVIDERS["openai"]
    assert provider.api_key() == "secret"
    assert provider.configured() is True


def test_provider_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = ai.BUILTIN_PROVIDERS["openai"]
    assert provider.api_key() is None
    assert provider.configured() is False


def test_ollama_does_not_require_key():
    assert ai.BUILTIN_PROVIDERS["ollama"].configured() is True


def test_load_custom_providers(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "lmstudio",
                        "kind": "openai",
                        "base_url": "http://localhost:1234/v1",
                        "api_key_env": None,
                        "model": "local-model",
                    }
                ]
            }
        )
    )
    providers = ai.load_custom_providers(path)
    assert providers["lmstudio"].kind == "openai"
    assert providers["lmstudio"].configured() is True


def test_custom_provider_ignores_invalid_headers(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "badheaders",
                        "kind": "openai",
                        "base_url": "http://example.test/v1",
                        "api_key_env": None,
                        "model": "my-model",
                        "headers": ["not", "a", "dict"],
                    }
                ]
            }
        )
    )
    providers = ai.load_custom_providers(path)
    assert providers["badheaders"].headers == {}


def test_build_stats_without_party_column():
    frame = pd.DataFrame(
        {
            "position": ["Senator"],
            "candidate_name": ["Alice"],
            "total_votes": [10],
            "region": ["Luzon"],
        }
    )
    stats = ai.build_stats(frame, "national")
    assert stats["party_shares"] == []


def test_available_providers_merges_custom(tmp_path):
    path = tmp_path / "providers.json"
    path.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "myprovider",
                        "kind": "openai",
                        "base_url": "http://example.test/v1",
                        "api_key_env": "MY_KEY",
                        "model": "my-model",
                    }
                ]
            }
        )
    )
    providers = ai.available_providers(path)
    assert "openai" in providers
    assert "myprovider" in providers


def test_build_stats_aggregates():
    stats = ai.build_stats(sample_frame(), "national")
    assert stats["rows"] == 6
    assert stats["total_votes"] == 210
    assert stats["top_candidates"][0]["candidate"] == "Candidate 1"
    assert stats["party_shares"]
    assert "map_mapped" in stats


def test_build_prompt_uses_only_top_five():
    stats = ai.build_stats(sample_frame(), "national")
    prompt = ai.build_prompt(stats)
    assert "Candidate 1" in prompt
    assert "Candidate 6" not in prompt
    assert "Rows: 6" in prompt


def test_fallback_summary_mentions_top_candidate():
    stats = ai.build_stats(sample_frame(), "national")
    summary = ai.fallback_summary(stats)
    assert "Candidate 1" in summary
    assert "Total votes" in summary
    assert "Map coverage" in summary


def test_generate_summary_without_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = ai.generate_summary(
        sample_frame(),
        "national",
        ai.BUILTIN_PROVIDERS["openai"],
        "gpt-4o-mini",
    )
    assert result.used_fallback is True
    assert "Candidate 1" in result.text


def test_generate_summary_openai_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Model summary"}}]}

    def fake_post(url, headers, json, timeout):
        assert url == "https://api.openai.com/v1/chat/completions"
        assert headers["Authorization"] == "Bearer secret"
        assert json["model"] == "gpt-4o-mini"
        return FakeResponse()

    monkeypatch.setattr(ai.requests, "post", fake_post)
    result = ai.generate_summary(
        sample_frame(),
        "national",
        ai.BUILTIN_PROVIDERS["openai"],
        "gpt-4o-mini",
    )
    assert result.used_fallback is False
    assert result.text == "Model summary"


def test_gemini_sends_key_in_header(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gem-key")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [{"content": {"parts": [{"text": "Gemini summary"}]}}]
            }

    def fake_post(url, headers, json, timeout):
        assert url == (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-2.5-flash:generateContent"
        )
        assert headers["x-goog-api-key"] == "gem-key"
        assert "gem-key" not in url
        return FakeResponse()

    monkeypatch.setattr(ai.requests, "post", fake_post)
    result = ai.generate_summary(
        sample_frame(),
        "national",
        ai.BUILTIN_PROVIDERS["gemini"],
        "gemini-2.5-flash",
    )
    assert result.used_fallback is False
    assert result.text == "Gemini summary"


def test_generate_summary_error_is_redacted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret")

    class FakeResponse:
        status_code = 401

        def json(self):
            return {}

    monkeypatch.setattr(ai.requests, "post", lambda *args, **kwargs: FakeResponse())
    result = ai.generate_summary(
        sample_frame(),
        "national",
        ai.BUILTIN_PROVIDERS["openai"],
        "gpt-4o-mini",
    )
    assert result.used_fallback is True
    assert result.error == "HTTP 401"
    assert "super-secret" not in result.error


def test_redact_replaces_secret():
    assert ai.redact("key=super-secret", "super-secret") == "key=***"
