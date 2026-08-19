import pytest

import romm_mcp.server as server


class FakeClient:
    def __init__(self):
        self.calls = []
    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return {"method": method, "path": path, **kwargs}


@pytest.fixture()
def fake(monkeypatch):
    value = FakeClient()
    monkeypatch.setattr(server, "client", lambda: value)
    return value


def test_update_rom_metadata_is_bounded(fake):
    result = server.update_rom_metadata(7, name="Chrono Trigger", summary="Classic")
    method, path, kwargs = fake.calls[-1]
    assert method == "PUT"
    assert path == "/api/roms/7"
    assert kwargs["multipart"] == {"name": "Chrono Trigger", "summary": "Classic"}
    assert result.id == 7


def test_update_rom_properties_validates_rating(fake):
    with pytest.raises(ValueError, match="rating"):
        server.update_rom_user_properties(7, rating=11)


def test_collection_membership_never_calls_rom_delete(fake):
    server.remove_roms_from_collection(3, [7, 8])
    method, path, kwargs = fake.calls[-1]
    assert method == "DELETE"
    assert path == "/api/collections/3/roms"
    assert kwargs["json"] == {"rom_ids": [7, 8]}


def test_smart_collection_serializes_filter_criteria(fake):
    server.create_smart_collection("JRPG", {"genres": ["Role-playing (RPG)"]})
    method, path, kwargs = fake.calls[-1]
    assert method == "POST"
    assert path == "/api/collections/smart"
    assert '"genres"' in kwargs["data"]["filter_criteria"]


def test_smart_collection_rejects_unknown_filter_key(fake):
    with pytest.raises(ValueError):
        server.create_smart_collection("JRPG", {"unexpected_filter": True})
    assert fake.calls == []


@pytest.mark.asyncio
async def test_expected_management_tools_are_registered():
    tools = await server.mcp.list_tools()
    names = {tool.name for tool in tools}
    expected = {
        "health", "list_roms", "get_rom", "update_rom_metadata",
        "update_rom_user_properties", "create_rom_note", "delete_rom_note",
        "create_collection", "update_collection", "delete_collection",
        "add_roms_to_collection", "remove_roms_from_collection",
        "create_smart_collection", "update_smart_collection", "delete_smart_collection",
        "list_users", "list_play_sessions",
    }
    assert expected <= names
    assert "delete_rom" not in names
    assert "run_task" not in names
    assert "update_user_permissions" not in names


def test_delete_collection_requires_confirmation(fake):
    with pytest.raises(ValueError, match="confirm=true"):
        server.delete_collection(3)
    assert fake.calls == []


def test_update_collection_preserves_membership_when_omitted(fake):
    calls = []
    def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"rom_ids": [7, 8]} if method == "GET" else {"id": 3, "name": "Renamed"}
    fake.request = request
    result = server.update_collection(3, name="Renamed")
    assert calls[-1][2]["multipart"]["rom_ids"] == "[7, 8]"
    assert result.id == 3


def test_create_note_is_typed_and_bounded(fake):
    server.create_rom_note(7, "Hints", content="Use magic", tags=["guide"])
    method, path, kwargs = fake.calls[-1]
    assert method == "POST"
    assert path == "/api/roms/7/notes"
    assert kwargs["json"] == {
        "title": "Hints",
        "content": "Use magic",
        "is_public": False,
        "tags": ["guide"],
    }


def test_update_note_requires_supported_field(fake):
    with pytest.raises(ValueError, match="At least one"):
        server.update_rom_note(7, 2)


@pytest.mark.asyncio
async def test_update_rom_metadata_schema_excludes_remote_asset_urls():
    tools = await server.mcp.list_tools()
    tool = next(tool for tool in tools if tool.name == "update_rom_metadata")
    properties = tool.inputSchema["properties"]
    assert "url_cover" not in properties
    assert "url_manual" not in properties
    assert {"rom_id", "name", "name_sort_key", "summary"} <= set(properties)


@pytest.mark.asyncio
async def test_smart_collection_filter_schema_is_explicit():
    tools = await server.mcp.list_tools()
    tool = next(tool for tool in tools if tool.name == "create_smart_collection")
    schema_text = str(tool.inputSchema)
    assert "filter_criteria" in tool.inputSchema["properties"]
    assert "genres_logic" in schema_text
    assert "metadata_providers" in schema_text
    assert "additionalProperties': False" in schema_text or '"additionalProperties": False' in schema_text


class StaticClient:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return self.value


def _use_static(monkeypatch, value):
    fake_client = StaticClient(value)
    monkeypatch.setattr(server, "client", lambda: fake_client)
    return fake_client


def test_user_outputs_exclude_pii_authorization_and_ui_settings(monkeypatch):
    fake_secret = "user-synthetic-secret"
    upstream = [{
        "id": 4,
        "username": "operator",
        "enabled": True,
        "email": "operator@example.invalid",
        "role": "admin",
        "permission_group_id": 2,
        "oauth_scopes": ["roms.read", "users.write"],
        "ui_settings": {"provider_url": f"https://metadata.example/?api_key={fake_secret}"},
        "current_device_id": "device-private",
    }]
    _use_static(monkeypatch, upstream)
    result = server.list_users().model_dump()
    assert result["items"] == [{"id": 4, "username": "operator", "enabled": True}]
    text = str(result)
    assert "operator@example.invalid" not in text
    assert "oauth_scopes" not in text
    assert "ui_settings" not in text
    assert fake_secret not in text


def test_rom_list_and_get_are_bounded_projections(monkeypatch):
    fake_secret = "rom-synthetic-secret"
    rom = {
        "id": 7,
        "name": "Chrono Trigger",
        "platform_id": 1,
        "platform_display_name": "SNES",
        "slug": "chrono-trigger",
        "summary": "Classic",
        "regions": ["USA"],
        "languages": ["English"],
        "tags": ["jrpg"],
        "missing_from_fs": False,
        "has_notes": True,
        "rom_user": {"status": "finished", "rating": 9, "completion": 100, "backlogged": False, "hidden": False},
        "igdb_metadata": {"url": f"https://metadata.example/game?API_KEY={fake_secret}", "huge": [1] * 1000},
        "files": [{"full_path": "/private/library/game.sfc", "sha1_hash": "deadbeef"}],
        "url_cover": f"https://metadata.example/cover?token={fake_secret}",
    }
    _use_static(monkeypatch, {"items": [rom], "total": 1, "unrelated": {"secret": fake_secret}})
    listed = server.list_roms(limit=10).model_dump()
    assert listed["count"] == 1
    assert listed["items"][0]["id"] == 7
    assert listed["items"][0]["name"] == "Chrono Trigger"
    assert fake_secret not in str(listed)
    assert "igdb_metadata" not in str(listed)
    assert "files" not in str(listed)
    assert "url_cover" not in str(listed)

    _use_static(monkeypatch, rom)
    detail = server.get_rom(7).model_dump()
    assert detail["id"] == 7
    assert detail["summary"] == "Classic"
    assert detail["status"] == "finished"
    assert fake_secret not in str(detail)
    assert "igdb_metadata" not in str(detail)
    assert "full_path" not in str(detail)


@pytest.mark.asyncio
async def test_all_26_tools_have_explicit_annotations_and_output_schemas():
    tools = await server.mcp.list_tools()
    by_name = {tool.name: tool for tool in tools}
    expected = {
        "health", "list_platforms", "get_platform", "list_roms", "get_rom",
        "update_rom_metadata", "update_rom_user_properties", "list_rom_notes",
        "create_rom_note", "update_rom_note", "delete_rom_note",
        "list_collections", "get_collection", "create_collection", "update_collection",
        "delete_collection", "add_roms_to_collection", "remove_roms_from_collection",
        "list_smart_collections", "get_smart_collection", "create_smart_collection",
        "update_smart_collection", "delete_smart_collection", "list_users", "get_user",
        "list_play_sessions",
    }
    assert set(by_name) == expected
    read_only = {
        "health", "list_platforms", "get_platform", "list_roms", "get_rom",
        "list_rom_notes", "list_collections", "get_collection", "list_smart_collections",
        "get_smart_collection", "list_users", "get_user", "list_play_sessions",
    }
    destructive = {"delete_rom_note", "delete_collection", "delete_smart_collection"}
    for name, tool in by_name.items():
        assert tool.outputSchema is not None, name
        assert tool.annotations is not None, name
        assert tool.annotations.openWorldHint is True, name
        assert tool.annotations.readOnlyHint is (name in read_only), name
        assert tool.annotations.destructiveHint is (name in destructive), name
        if name in read_only:
            assert tool.annotations.idempotentHint is True, name
    assert "delete_rom" not in by_name
    assert "run_task" not in by_name
    assert "update_user_permissions" not in by_name


def test_health_is_minimal_and_does_not_read_permissions(monkeypatch):
    upstream = {
        "id": 4,
        "username": "operator",
        "email": "operator@example.invalid",
        "oauth_scopes": ["users.write"],
        "ui_settings": {"theme": "private"},
    }
    fake_client = _use_static(monkeypatch, upstream)
    result = server.health().model_dump()
    assert result == {
        "ok": True,
        "romm_reachable": True,
        "authenticated": True,
        "user_id": 4,
        "username": "operator",
    }
    assert [call[1] for call in fake_client.calls] == ["/api/users/me"]


def test_collection_note_and_play_session_outputs_drop_upstream_internals(monkeypatch):
    fake_secret = "projection-synthetic-secret"
    _use_static(monkeypatch, [{
        "id": 9, "name": "Favorites", "description": "Games", "rom_count": 2,
        "rom_ids": [7, 8], "user_id": 4, "owner_username": "operator",
        "url_cover": f"https://metadata.example/cover?token={fake_secret}",
        "path_covers_large": ["/private/cover.jpg"],
    }])
    collections = server.list_collections().model_dump()
    assert collections["items"][0]["id"] == 9
    assert "rom_ids" not in str(collections)
    assert "url_cover" not in str(collections)
    assert fake_secret not in str(collections)

    _use_static(monkeypatch, [{
        "id": 2, "rom_id": 7, "title": "Hint", "content": f"See https://example.invalid/?Api_Key={fake_secret}",
        "is_public": False, "tags": ["guide"], "user_id": 4, "username": "operator",
        "user_avatar_path": "/private/avatar.png",
    }])
    notes = server.list_rom_notes(7).model_dump()
    assert fake_secret not in str(notes)
    assert "user_avatar_path" not in str(notes)

    _use_static(monkeypatch, [{
        "id": 5, "rom_id": 7, "user_id": 4, "device_id": "private-device",
        "sync_session_id": 11, "save_slot": "private-slot", "start_time": "2026-08-19T08:00:00Z",
        "end_time": "2026-08-19T09:00:00Z", "duration_ms": 3600000,
    }])
    sessions = server.list_play_sessions().model_dump()
    assert sessions["items"][0]["rom_id"] == 7
    assert "device_id" not in str(sessions)
    assert "sync_session_id" not in str(sessions)
    assert "save_slot" not in str(sessions)


def test_update_rom_user_properties_uses_rom_id_not_internal_property_id(monkeypatch):
    upstream = {
        "id": 991,
        "user_id": 4,
        "rom_id": 7,
        "status": "finished",
        "rating": 9,
        "difficulty": 4,
        "completion": 100,
        "backlogged": False,
        "hidden": False,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-08-19T00:00:00Z",
    }
    _use_static(monkeypatch, upstream)
    result = server.update_rom_user_properties(7, rating=9).model_dump()
    assert result["rom_id"] == 7
    assert result["status"] == "finished"
    assert result["rating"] == 9
    assert "991" not in str(result)
    assert "user_id" not in str(result)
