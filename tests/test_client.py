import httpx
import pytest

from romm_mcp.client import RomMClient, RomMError


def make_client(handler):
    client = RomMClient("http://romm", "rmm_" + "a" * 64)
    client._client.close()
    client._client = httpx.Client(
        base_url="http://romm",
        headers={"Authorization": "Bearer rmm_" + "a" * 64},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_request_uses_bearer_token_and_returns_json():
    def handler(request):
        assert request.headers["authorization"].startswith("Bearer rmm_")
        return httpx.Response(200, json={"ok": True})
    client = make_client(handler)
    assert client.request("GET", "/api/users/me") == {"ok": True}


def test_request_redacts_credential_from_errors():
    token = "rmm_" + "b" * 64
    client = RomMClient("http://romm", token)
    client._client.close()
    client._client = httpx.Client(base_url="http://romm", transport=httpx.MockTransport(lambda req: httpx.Response(403, json={"detail": "Forbidden"})))
    with pytest.raises(RomMError) as exc:
        client.request("GET", "/api/roms")
    assert token not in str(exc.value)
    assert "HTTP 403" in str(exc.value)


def test_request_sends_multipart_form_data():
    def handler(request):
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        body = request.content.decode("utf-8")
        assert 'name="name"' in body
        assert "Chrono Trigger" in body
        return httpx.Response(200, json={"ok": True})
    client = make_client(handler)
    assert client.request("PUT", "/api/roms/7", multipart={"name": "Chrono Trigger"}) == {"ok": True}
