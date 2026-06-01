import pytest

from live_chat.llm import gemini_client


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_client, "load_project_env", lambda: None)

    with pytest.raises(EnvironmentError, match="GEMINI_API_KEY is not set"):
        gemini_client.get_api_key()
