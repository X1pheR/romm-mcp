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
    assert result["path"] == "/api/roms/7"
    assert result["multipart"] == {"name": "Chrono Trigger", "summary": "Classic"}


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
    result = server.create_smart_collection("JRPG", {"genres": ["Role-playing (RPG)"]})
    assert result["path"] == "/api/collections/smart"
    assert '"genres"' in result["data"]["filter_criteria"]


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
    fake.request = lambda method, path, **kwargs: ({"rom_ids": [7, 8]} if method == "GET" else {"method": method, "path": path, **kwargs})
    result = server.update_collection(3, name="Renamed")
    assert result["multipart"]["rom_ids"] == "[7, 8]"


def test_create_note_is_typed_and_bounded(fake):
    result = server.create_rom_note(7, "Hints", content="Use magic", tags=["guide"])
    assert result["json"] == {
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
