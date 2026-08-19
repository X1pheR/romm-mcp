from __future__ import annotations

import json
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict

from .client import RomMClient
from .config import Settings
from .output import (
    CollectionView,
    HealthView,
    ListView,
    NoteView,
    OperationView,
    PlatformView,
    PlaySessionView,
    RomUserPropertiesView,
    RomView,
    SmartCollectionView,
    UserView,
    project_collection,
    project_collection_list,
    project_health,
    project_note,
    project_note_list,
    project_platform,
    project_platform_list,
    project_play_session_list,
    project_rom,
    project_rom_list,
    project_rom_user_properties,
    project_smart_collection,
    project_smart_collection_list,
    project_user,
    project_user_list,
)

mcp = FastMCP("RomM")
_client: RomMClient | None = None

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)
DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
)

SmartFilterLogic = Literal["any", "all"]


class SmartCollectionFilterCriteria(BaseModel):
    """RomM 5.1 smart-collection filters intentionally exposed by this MCP."""

    model_config = ConfigDict(extra="forbid")

    platform_ids: list[int] | None = None
    collection_id: int | None = None
    virtual_collection_id: str | None = None
    search_term: str | None = None
    matched: bool | None = None
    favorite: bool | None = None
    duplicate: bool | None = None
    last_played: bool | None = None
    playable: bool | None = None
    has_ra: bool | None = None
    has_saves: bool | None = None
    has_states: bool | None = None
    has_soundtrack: bool | None = None
    missing: bool | None = None
    verified: bool | None = None
    genres: list[str] | None = None
    franchises: list[str] | None = None
    collections: list[str] | None = None
    companies: list[str] | None = None
    age_ratings: list[str] | None = None
    statuses: list[str] | None = None
    regions: list[str] | None = None
    languages: list[str] | None = None
    player_counts: list[str] | None = None
    metadata_providers: list[str] | None = None
    tags: list[str] | None = None
    genres_logic: SmartFilterLogic | None = None
    franchises_logic: SmartFilterLogic | None = None
    collections_logic: SmartFilterLogic | None = None
    companies_logic: SmartFilterLogic | None = None
    age_ratings_logic: SmartFilterLogic | None = None
    regions_logic: SmartFilterLogic | None = None
    languages_logic: SmartFilterLogic | None = None
    statuses_logic: SmartFilterLogic | None = None
    player_counts_logic: SmartFilterLogic | None = None
    metadata_providers_logic: SmartFilterLogic | None = None
    tags_logic: SmartFilterLogic | None = None
    order_by: str | None = None
    order_dir: Literal["asc", "desc"] | None = None


def _smart_filter_payload(filter_criteria: SmartCollectionFilterCriteria | dict[str, Any]) -> dict[str, Any]:
    criteria = SmartCollectionFilterCriteria.model_validate(filter_criteria)
    return criteria.model_dump(exclude_none=True)


def client() -> RomMClient:
    global _client
    if _client is None:
        s = Settings.from_env()
        _client = RomMClient(s.base_url, s.token, s.timeout_seconds)
    return _client


@mcp.tool(annotations=READ_ONLY)
def health() -> HealthView:
    """Verify authenticated RomM API access and return non-sensitive connectivity identity only."""
    me = client().request("GET", "/api/users/me")
    return project_health(me)


@mcp.tool(annotations=READ_ONLY)
def list_platforms() -> ListView[PlatformView]:
    """List compact RomM platform summaries visible to the token."""
    return project_platform_list(client().request("GET", "/api/platforms"))


@mcp.tool(annotations=READ_ONLY)
def get_platform(platform_id: int) -> PlatformView:
    """Get a compact RomM platform summary by internal ID."""
    return project_platform(client().request("GET", f"/api/platforms/{platform_id}"))


@mcp.tool(annotations=READ_ONLY)
def list_roms(
    search_term: str | None = None,
    platform_ids: list[int] | None = None,
    collection_id: int | None = None,
    smart_collection_id: int | None = None,
    favorite: bool | None = None,
    matched: bool | None = None,
    missing: bool | None = None,
    order_by: str = "",
    order_dir: Literal["asc", "desc"] = "asc",
    limit: int = 50,
    offset: int = 0,
) -> ListView[RomView]:
    """Search/list ROMs with bounded pagination and a compact provider-internal-free response."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    params: dict[str, Any] = {
        "with_char_index": False,
        "with_filter_values": False,
        "with_rom_id_index": False,
        "limit": limit,
        "offset": offset,
        "order_by": order_by,
        "order_dir": order_dir,
    }
    optional = {
        "search_term": search_term,
        "platform_ids": platform_ids,
        "collection_id": collection_id,
        "smart_collection_id": smart_collection_id,
        "favorite": favorite,
        "matched": matched,
        "missing": missing,
    }
    params.update({k: v for k, v in optional.items() if v is not None})
    raw = client().request("GET", "/api/roms", params=params)
    return project_rom_list(raw, limit=limit, offset=offset)


@mcp.tool(annotations=READ_ONLY)
def get_rom(rom_id: int) -> RomView:
    """Get one bounded ROM view without provider internals, filesystem details, hashes or credential URLs."""
    return project_rom(client().request("GET", f"/api/roms/{rom_id}"), fallback_id=rom_id)


@mcp.tool(annotations=WRITE)
def update_rom_metadata(
    rom_id: int,
    name: str | None = None,
    name_sort_key: str | None = None,
    summary: str | None = None,
) -> RomView:
    """Update bounded text metadata only; asset fetch/write and provider-ID mutation are excluded."""
    data = {k: v for k, v in {
        "name": name,
        "name_sort_key": name_sort_key,
        "summary": summary,
    }.items() if v is not None}
    if not data:
        raise ValueError("At least one metadata field must be provided")
    raw = client().request("PUT", f"/api/roms/{rom_id}", multipart=data)
    return project_rom(raw, fallback_id=rom_id)


@mcp.tool(annotations=WRITE)
def update_rom_user_properties(
    rom_id: int,
    status: Literal["incomplete", "finished", "completed_100", "retired", "never_playing"] | None = None,
    rating: int | None = None,
    difficulty: int | None = None,
    completion: int | None = None,
    backlogged: bool | None = None,
    hidden: bool | None = None,
) -> RomUserPropertiesView:
    """Update personal ROM status/rating/completion properties for the token owner."""
    for field, value, low, high in (("rating", rating, 0, 10), ("difficulty", difficulty, 0, 10), ("completion", completion, 0, 100)):
        if value is not None and not low <= value <= high:
            raise ValueError(f"{field} must be between {low} and {high}")
    payload = {k: v for k, v in {
        "status": status,
        "rating": rating,
        "difficulty": difficulty,
        "completion": completion,
        "backlogged": backlogged,
        "hidden": hidden,
    }.items() if v is not None}
    if not payload:
        raise ValueError("At least one user property must be provided")
    raw = client().request("PUT", f"/api/roms/{rom_id}/props", json=payload)
    return project_rom_user_properties(raw, fallback_rom_id=rom_id)


@mcp.tool(annotations=READ_ONLY)
def list_rom_notes(rom_id: int) -> ListView[NoteView]:
    """List up to 100 bounded notes attached to a ROM."""
    return project_note_list(client().request("GET", f"/api/roms/{rom_id}/notes"), rom_id=rom_id)


@mcp.tool(annotations=WRITE)
def create_rom_note(
    rom_id: int,
    title: str,
    content: str = "",
    is_public: bool = False,
    tags: list[str] | None = None,
) -> NoteView:
    """Create a RomM note with explicit supported fields."""
    if not title.strip():
        raise ValueError("title must not be empty")
    payload = {"title": title, "content": content, "is_public": is_public, "tags": tags or []}
    raw = client().request("POST", f"/api/roms/{rom_id}/notes", json=payload)
    return project_note(raw, fallback_rom_id=rom_id)


@mcp.tool(annotations=WRITE)
def update_rom_note(
    rom_id: int,
    note_id: int,
    title: str | None = None,
    content: str | None = None,
    is_public: bool | None = None,
    tags: list[str] | None = None,
) -> NoteView:
    """Update only the explicit fields supported by RomM notes."""
    payload = {k: v for k, v in {
        "title": title,
        "content": content,
        "is_public": is_public,
        "tags": tags,
    }.items() if v is not None}
    if not payload:
        raise ValueError("At least one note field must be provided")
    if title is not None and not title.strip():
        raise ValueError("title must not be empty")
    raw = client().request("PUT", f"/api/roms/{rom_id}/notes/{note_id}", json=payload)
    return project_note(raw, fallback_rom_id=rom_id, fallback_note_id=note_id)


@mcp.tool(annotations=DESTRUCTIVE)
def delete_rom_note(rom_id: int, note_id: int, confirm: bool = False) -> OperationView:
    """Delete one RomM note after explicit confirmation. This does not delete ROM files."""
    if not confirm:
        raise ValueError("confirm=true is required to delete a note")
    client().request("DELETE", f"/api/roms/{rom_id}/notes/{note_id}")
    return OperationView(action="delete_rom_note", resource_id=note_id)


@mcp.tool(annotations=READ_ONLY)
def list_collections() -> ListView[CollectionView]:
    """List compact normal RomM collections."""
    return project_collection_list(client().request("GET", "/api/collections"))


@mcp.tool(annotations=READ_ONLY)
def get_collection(collection_id: int) -> CollectionView:
    """Get one compact normal RomM collection."""
    return project_collection(client().request("GET", f"/api/collections/{collection_id}"), fallback_id=collection_id)


@mcp.tool(annotations=WRITE)
def create_collection(name: str, description: str = "", is_public: bool | None = None, is_favorite: bool | None = None) -> CollectionView:
    """Create a normal RomM collection without uploading artwork."""
    if not name.strip():
        raise ValueError("name must not be empty")
    params = {k: v for k, v in {"is_public": is_public, "is_favorite": is_favorite}.items() if v is not None}
    raw = client().request("POST", "/api/collections", params=params, multipart={"name": name, "description": description})
    return project_collection(raw)


@mcp.tool(annotations=WRITE)
def update_collection(
    collection_id: int,
    rom_ids: list[int] | None = None,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
) -> CollectionView:
    """Update collection metadata/membership without artwork changes."""
    if rom_ids is None:
        current = client().request("GET", f"/api/collections/{collection_id}")
        rom_ids = current.get("rom_ids", []) if isinstance(current, dict) else []
    data: dict[str, Any] = {"rom_ids": json.dumps(rom_ids)}
    if name is not None:
        if not name.strip():
            raise ValueError("name must not be empty")
        data["name"] = name
    if description is not None:
        data["description"] = description
    params = {"is_public": is_public} if is_public is not None else None
    raw = client().request("PUT", f"/api/collections/{collection_id}", params=params, multipart=data)
    return project_collection(raw, fallback_id=collection_id)


@mcp.tool(annotations=DESTRUCTIVE)
def delete_collection(collection_id: int, confirm: bool = False) -> OperationView:
    """Delete a collection after explicit confirmation; ROM files are never deleted."""
    if not confirm:
        raise ValueError("confirm=true is required to delete a collection")
    client().request("DELETE", f"/api/collections/{collection_id}")
    return OperationView(action="delete_collection", resource_id=collection_id)


@mcp.tool(annotations=WRITE)
def add_roms_to_collection(collection_id: int, rom_ids: list[int]) -> OperationView:
    """Add ROM IDs to an existing collection."""
    if not rom_ids:
        raise ValueError("rom_ids must not be empty")
    client().request("POST", f"/api/collections/{collection_id}/roms", json={"rom_ids": rom_ids})
    return OperationView(action="add_roms_to_collection", collection_id=collection_id, rom_ids=rom_ids)


@mcp.tool(annotations=WRITE)
def remove_roms_from_collection(collection_id: int, rom_ids: list[int]) -> OperationView:
    """Remove ROM IDs from a collection without deleting ROMs."""
    if not rom_ids:
        raise ValueError("rom_ids must not be empty")
    client().request("DELETE", f"/api/collections/{collection_id}/roms", json={"rom_ids": rom_ids})
    return OperationView(action="remove_roms_from_collection", collection_id=collection_id, rom_ids=rom_ids)


@mcp.tool(annotations=READ_ONLY)
def list_smart_collections() -> ListView[SmartCollectionView]:
    """List compact RomM smart collections with only the explicit supported filter schema."""
    return project_smart_collection_list(client().request("GET", "/api/collections/smart"))


@mcp.tool(annotations=READ_ONLY)
def get_smart_collection(collection_id: int) -> SmartCollectionView:
    """Get one bounded RomM smart collection."""
    return project_smart_collection(client().request("GET", f"/api/collections/smart/{collection_id}"), fallback_id=collection_id)


@mcp.tool(annotations=WRITE)
def create_smart_collection(name: str, filter_criteria: SmartCollectionFilterCriteria, description: str = "", is_public: bool | None = None) -> SmartCollectionView:
    """Create a smart collection from explicit RomM filter criteria."""
    if not name.strip():
        raise ValueError("name must not be empty")
    params = {"is_public": is_public} if is_public is not None else None
    data = {"name": name, "description": description, "filter_criteria": json.dumps(_smart_filter_payload(filter_criteria))}
    raw = client().request("POST", "/api/collections/smart", params=params, data=data)
    return project_smart_collection(raw)


@mcp.tool(annotations=WRITE)
def update_smart_collection(
    collection_id: int,
    name: str | None = None,
    description: str | None = None,
    filter_criteria: SmartCollectionFilterCriteria | None = None,
    is_public: bool | None = None,
) -> SmartCollectionView:
    """Update a smart collection."""
    data: dict[str, Any] = {}
    if name is not None:
        if not name.strip():
            raise ValueError("name must not be empty")
        data["name"] = name
    if description is not None:
        data["description"] = description
    if filter_criteria is not None:
        data["filter_criteria"] = json.dumps(_smart_filter_payload(filter_criteria))
    if not data and is_public is None:
        raise ValueError("At least one field must be provided")
    params = {"is_public": is_public} if is_public is not None else None
    raw = client().request("PUT", f"/api/collections/smart/{collection_id}", params=params, data=data)
    return project_smart_collection(raw, fallback_id=collection_id)


@mcp.tool(annotations=DESTRUCTIVE)
def delete_smart_collection(collection_id: int, confirm: bool = False) -> OperationView:
    """Delete a smart collection definition after explicit confirmation; this does not delete ROM files."""
    if not confirm:
        raise ValueError("confirm=true is required to delete a smart collection")
    client().request("DELETE", f"/api/collections/smart/{collection_id}")
    return OperationView(action="delete_smart_collection", resource_id=collection_id)


@mcp.tool(annotations=READ_ONLY)
def list_users() -> ListView[UserView]:
    """List minimal user identity needed for follow-up calls; email, roles, OAuth scopes and UI/device settings are excluded."""
    return project_user_list(client().request("GET", "/api/users"))


@mcp.tool(annotations=READ_ONLY)
def get_user(user_id: int) -> UserView:
    """Get minimal RomM user identity; authorization and UI/device details are excluded."""
    return project_user(client().request("GET", f"/api/users/{user_id}"))


@mcp.tool(annotations=READ_ONLY)
def list_play_sessions(limit: int = 100, offset: int = 0) -> ListView[PlaySessionView]:
    """List bounded play-session summaries for the token owner without device/sync internals."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    raw = client().request("GET", "/api/play-sessions", params={"limit": limit, "offset": offset})
    return project_play_session_list(raw, limit=limit, offset=offset)
