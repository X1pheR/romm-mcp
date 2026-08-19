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


def test_request_sanitizes_deeply_nested_secret_urls():
    fake_secret = "synthetic-secret-never-real"
    payload = {
        "outer": [{"provider_url": f"https://metadata.example/api?game=7&api_key={fake_secret}"}],
        "plain": "ok",
    }
    client = make_client(lambda req: httpx.Response(200, json=payload))
    result = client.request("GET", "/api/roms")
    text = str(result)
    assert fake_secret not in text
    assert "game=7" in text
    assert result["plain"] == "ok"


def test_request_sanitizes_mixed_case_secret_query_parameters():
    fake_secret = "mixed-case-synthetic"
    payload = {
        "url": f"https://metadata.example/item?Api_Key={fake_secret}&ACCESS_TOKEN={fake_secret}&page=2"
    }
    client = make_client(lambda req: httpx.Response(200, json=payload))
    result = client.request("GET", "/api/roms/7")
    text = str(result)
    assert fake_secret not in text
    assert "page=2" in text


def test_request_preserves_ordinary_safe_urls():
    safe_url = "https://metadata.example/item?id=7&locale=en"
    client = make_client(lambda req: httpx.Response(200, json={"url": safe_url}))
    assert client.request("GET", "/api/platforms/1")["url"] == safe_url


def test_request_sanitizes_secret_url_inside_upstream_error_detail():
    fake_secret = "error-synthetic-secret"
    detail = f"Provider failed at https://metadata.example/item?id=7&token={fake_secret}"
    client = make_client(lambda req: httpx.Response(502, json={"detail": detail}))
    with pytest.raises(RomMError) as exc:
        client.request("GET", "/api/roms")
    assert fake_secret not in str(exc.value)
    assert "HTTP 502" in str(exc.value)
