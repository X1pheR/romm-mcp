from __future__ import annotations

from typing import Any

import httpx

from .output import safe_error_detail, sanitize_outbound


class RomMError(RuntimeError):
    pass


class RomMClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: float = 15.0) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: dict[str, Any] | None = None,
        multipart: dict[str, Any] | None = None,
    ) -> Any:
        files = None
        if multipart is not None:
            files = {key: (None, str(value)) for key, value in multipart.items()}
        try:
            response = self._client.request(method, path, params=params, json=json, data=data, files=files)
        except httpx.HTTPError as exc:
            raise RomMError(f"RomM request failed: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            detail = ""
            try:
                body = sanitize_outbound(response.json())
                if isinstance(body, dict):
                    detail = safe_error_detail(body.get("detail") or body.get("message") or "")
            except ValueError:
                pass
            suffix = f": {detail}" if detail else ""
            raise RomMError(f"RomM returned HTTP {response.status_code}{suffix}")
        if response.status_code == 204 or not response.content:
            return {"ok": True}
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return sanitize_outbound(response.json())
        return {"ok": True, "status_code": response.status_code}
