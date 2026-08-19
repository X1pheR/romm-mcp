from pathlib import Path

import pytest

from romm_mcp.config import Settings


def test_settings_reads_file_backed_token(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("rmm_" + "a" * 64 + "\n", encoding="utf-8")
    monkeypatch.setenv("ROMM_BASE_URL", "http://romm:8080/")
    monkeypatch.setenv("ROMM_API_TOKEN_FILE", str(token_file))
    settings = Settings.from_env()
    assert settings.base_url == "http://romm:8080"
    assert settings.token.startswith("rmm_")


def test_settings_rejects_non_client_token(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("not-a-token", encoding="utf-8")
    monkeypatch.setenv("ROMM_BASE_URL", "http://romm:8080")
    monkeypatch.setenv("ROMM_API_TOKEN_FILE", str(token_file))
    with pytest.raises(RuntimeError, match="Client API Token"):
        Settings.from_env()


def test_settings_rejects_non_http_base_url(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("rmm_" + "a" * 64, encoding="utf-8")
    monkeypatch.setenv("ROMM_BASE_URL", "ftp://romm.example.com")
    monkeypatch.setenv("ROMM_API_TOKEN_FILE", str(token_file))
    with pytest.raises(RuntimeError, match="http"):
        Settings.from_env()


def test_settings_rejects_invalid_timeout(monkeypatch, tmp_path: Path):
    token_file = tmp_path / "token"
    token_file.write_text("rmm_" + "a" * 64, encoding="utf-8")
    monkeypatch.setenv("ROMM_BASE_URL", "https://romm.example.com")
    monkeypatch.setenv("ROMM_API_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("ROMM_TIMEOUT_SECONDS", "0")
    with pytest.raises(RuntimeError, match="greater than 0"):
        Settings.from_env()
