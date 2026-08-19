from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class Settings:
    base_url: str
    token: str
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.environ.get("ROMM_BASE_URL", "").strip().rstrip("/")
        token_file = os.environ.get("ROMM_API_TOKEN_FILE", "").strip()
        timeout_raw = os.environ.get("ROMM_TIMEOUT_SECONDS", "15").strip()

        if not base_url:
            raise RuntimeError("ROMM_BASE_URL is required")
        parsed_url = urlsplit(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise RuntimeError("ROMM_BASE_URL must be an absolute http:// or https:// URL")

        if not token_file:
            raise RuntimeError("ROMM_API_TOKEN_FILE is required")

        try:
            timeout = float(timeout_raw)
        except ValueError as exc:
            raise RuntimeError("ROMM_TIMEOUT_SECONDS must be a number") from exc
        if not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise RuntimeError("ROMM_TIMEOUT_SECONDS must be greater than 0 and at most 300")

        token = Path(token_file).read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError("ROMM_API_TOKEN_FILE is empty")
        if not token.startswith("rmm_"):
            raise RuntimeError("ROMM_API_TOKEN_FILE does not contain a RomM Client API Token")

        return cls(base_url=base_url, token=token, timeout_seconds=timeout)
