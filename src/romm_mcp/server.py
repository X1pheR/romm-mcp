from __future__ import annotations

import json
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict

from .client import RomMClient
from .config import Settings

mcp = FastMCP("RomM")
_client: RomMClient | None = None


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


def _compact_list(value: Any, limit: int) -> Any:
    if isinstance(value, list):
        return value[:limit]
    if isinstance(value, dict):
        for key in ("items", "results", "roms"):
            if isinstance(value.get(key), list):
                copy = dict(value)
                copy[key] = copy[key][:limit]
                return copy
    return value


@mcp.tool()
def health() -> dict[str, Any]:
    """Verify authenticated RomM API access and return current user/permission information."""
    me = client().request("GET", "/api/users/me")
    permissions = client().request("GET", "/api/permissions/me")
    return {"ok": True, "user": me, "permissions": permissions}


@mcp.tool()
def list_platforms() -> Any:
    """List RomM platforms visible to the token."""
    return client().request("GET", "/api/platforms")


@mcp.tool()
def get_platform(platform_id: int) -> Any:
    """Get one RomM platform by internal ID."""
    return client().request("GET", f"/api/platforms/{platform_id}")


@mcp.tool()
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
) -> Any:
    """Search/list ROMs with bounded pagination and common RomM filters."""
    limit = max(1, min(limit, 200))
    params: dict[str, Any] = {
        "with_char_index": False,
        "with_filter_values": False,
        "with_rom_id_index": False,
        "limit": limit,
        "offset": max(0, offset),
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
    return _compact_list(client().request("GET", "/api/roms", params=params), limit)


@mcp.tool()
def get_rom(rom_id: int) -> Any:
    """Get one ROM by internal ID."""
    return client().request("GET", f"/api/roms/{rom_id}")


@mcp.tool()
def update_rom_metadata(
    rom_id: int,
    name: str | None = None,
    name_sort_key: str | None = None,
    summary: str | None = None,
) -> Any:
    """Update bounded text metadata only; asset fetch/write and provider-ID mutation are excluded."""
    data = {k: v for k, v in {
        "name": name,
        "name_sort_key": name_sort_key,
        "summary": summary,
    }.items() if v is not None}
    if not data:
        raise ValueError("At least one metadata field must be provided")
    return client().request("PUT", f"/api/roms/{rom_id}", multipart=data)


@mcp.tool()
def update_rom_user_properties(
    rom_id: int,
    status: Literal["incomplete", "finished", "completed_100", "retired", "never_playing"] | None = None,
    rating: int | None = None,
    difficulty: int | None = None,
    completion: int | None = None,
    backlogged: bool | None = None,
    hidden: bool | None = None,
) -> Any:
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
    return client().request("PUT", f"/api/roms/{rom_id}/props", json=payload)


@mcp.tool()
def list_rom_notes(rom_id: int) -> Any:
    """List notes attached to a ROM."""
    return client().request("GET", f"/api/roms/{rom_id}/notes")


@mcp.tool()
def create_rom_note(
    rom_id: int,
    title: str,
    content: str = "",
    is_public: bool = False,
    tags: list[str] | None = None,
) -> Any:
    """Create a RomM note with explicit supported fields."""
    if not title.strip():
        raise ValueError("title must not be empty")
    payload = {"title": title, "content": content, "is_public": is_public, "tags": tags or []}
    return client().request("POST", f"/api/roms/{rom_id}/notes", json=payload)


@mcp.tool()
def update_rom_note(
    rom_id: int,
    note_id: int,
    title: str | None = None,
    content: str | None = None,
    is_public: bool | None = None,
    tags: list[str] | None = None,
) -> Any:
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
    return client().request("PUT", f"/api/roms/{rom_id}/notes/{note_id}", json=payload)


@mcp.tool()
def delete_rom_note(rom_id: int, note_id: int, confirm: bool = False) -> Any:
    """Delete one RomM note after explicit confirmation. This does not delete ROM files."""
    if not confirm:
        raise ValueError("confirm=true is required to delete a note")
    return client().request("DELETE", f"/api/roms/{rom_id}/notes/{note_id}")


@mcp.tool()
def list_collections() -> Any:
    """List normal RomM collections."""
    return client().request("GET", "/api/collections")


@mcp.tool()
def get_collection(collection_id: int) -> Any:
    """Get one normal RomM collection."""
    return client().request("GET", f"/api/collections/{collection_id}")


@mcp.tool()
def create_collection(name: str, description: str = "", is_public: bool | None = None, is_favorite: bool | None = None) -> Any:
    """Create a normal RomM collection without uploading artwork."""
    if not name.strip():
        raise ValueError("name must not be empty")
    params = {k: v for k, v in {"is_public": is_public, "is_favorite": is_favorite}.items() if v is not None}
    return client().request("POST", "/api/collections", params=params, multipart={"name": name, "description": description})


@mcp.tool()
def update_collection(
    collection_id: int,
    rom_ids: list[int] | None = None,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
) -> Any:
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
    return client().request("PUT", f"/api/collections/{collection_id}", params=params, multipart=data)


@mcp.tool()
def delete_collection(collection_id: int, confirm: bool = False) -> Any:
    """Delete a collection and its RomM-managed collection resources; ROM files are never deleted."""
    if not confirm:
        raise ValueError("confirm=true is required to delete a collection")
    return client().request("DELETE", f"/api/collections/{collection_id}")


@mcp.tool()
def add_roms_to_collection(collection_id: int, rom_ids: list[int]) -> Any:
    """Add ROM IDs to an existing collection."""
    if not rom_ids:
        raise ValueError("rom_ids must not be empty")
    return client().request("POST", f"/api/collections/{collection_id}/roms", json={"rom_ids": rom_ids})


@mcp.tool()
def remove_roms_from_collection(collection_id: int, rom_ids: list[int]) -> Any:
    """Remove ROM IDs from a collection without deleting ROMs."""
    if not rom_ids:
        raise ValueError("rom_ids must not be empty")
    return client().request("DELETE", f"/api/collections/{collection_id}/roms", json={"rom_ids": rom_ids})


@mcp.tool()
def list_smart_collections() -> Any:
    """List RomM smart collections."""
    return client().request("GET", "/api/collections/smart")


@mcp.tool()
def get_smart_collection(collection_id: int) -> Any:
    """Get one RomM smart collection."""
    return client().request("GET", f"/api/collections/smart/{collection_id}")


@mcp.tool()
def create_smart_collection(name: str, filter_criteria: SmartCollectionFilterCriteria, description: str = "", is_public: bool | None = None) -> Any:
    """Create a smart collection from explicit RomM filter criteria."""
    if not name.strip():
        raise ValueError("name must not be empty")
    params = {"is_public": is_public} if is_public is not None else None
    data = {"name": name, "description": description, "filter_criteria": json.dumps(_smart_filter_payload(filter_criteria))}
    return client().request("POST", "/api/collections/smart", params=params, data=data)


@mcp.tool()
def update_smart_collection(
    collection_id: int,
    name: str | None = None,
    description: str | None = None,
    filter_criteria: SmartCollectionFilterCriteria | None = None,
    is_public: bool | None = None,
) -> Any:
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
    return client().request("PUT", f"/api/collections/smart/{collection_id}", params=params, data=data)


@mcp.tool()
def delete_smart_collection(collection_id: int, confirm: bool = False) -> Any:
    """Delete a smart collection definition after explicit confirmation; this does not delete ROM files."""
    if not confirm:
        raise ValueError("confirm=true is required to delete a smart collection")
    return client().request("DELETE", f"/api/collections/smart/{collection_id}")


@mcp.tool()
def list_users() -> Any:
    """List RomM users. v0.1 intentionally exposes no user/permission mutation tools."""
    return client().request("GET", "/api/users")


@mcp.tool()
def get_user(user_id: int) -> Any:
    """Get one RomM user. v0.1 intentionally exposes no user/permission mutation tools."""
    return client().request("GET", f"/api/users/{user_id}")


@mcp.tool()
def list_play_sessions(limit: int = 100, offset: int = 0) -> Any:
    """List play sessions for the token owner with bounded pagination."""
    limit = max(1, min(limit, 200))
    return _compact_list(client().request("GET", "/api/play-sessions", params={"limit": limit, "offset": max(0, offset)}), limit)
