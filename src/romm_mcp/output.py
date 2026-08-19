from __future__ import annotations

import re
from typing import Any, Generic, TypeVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field

REDACTED = "[REDACTED]"
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_SECRET_NAMES = {
    "apikey",
    "apitoken",
    "accesstoken",
    "authtoken",
    "refreshtoken",
    "sessiontoken",
    "authorization",
    "bearertoken",
    "clientsecret",
    "clienttoken",
    "credential",
    "credentials",
    "key",
    "passwd",
    "password",
    "privatekey",
    "pwd",
    "secret",
    "secretkey",
    "signature",
    "token",
    "xapikey",
}


def _normalized_name(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _is_secret_name(value: str) -> bool:
    return _normalized_name(value) in _SECRET_NAMES


def _sanitize_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return url
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc or not parsed.query:
        return url
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if not any(_is_secret_name(name) for name, _ in pairs):
        return url
    safe_pairs = [(name, REDACTED if _is_secret_name(name) else value) for name, value in pairs]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(safe_pairs, doseq=True), parsed.fragment))


def _sanitize_string(value: str) -> str:
    return _URL_RE.sub(lambda match: _sanitize_url(match.group(0)), value)


def sanitize_outbound(value: Any) -> Any:
    """Recursively redact credential material from upstream data before it can leave the MCP."""
    if isinstance(value, dict):
        safe: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and _is_secret_name(key):
                safe[key] = REDACTED
            else:
                safe[key] = sanitize_outbound(item)
        return safe
    if isinstance(value, list):
        return [sanitize_outbound(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_outbound(item) for item in value)
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def safe_error_detail(value: Any, max_length: int = 500) -> str:
    safe = sanitize_outbound(value)
    if isinstance(safe, str):
        text = safe
    elif safe is None:
        return ""
    else:
        text = str(safe)
    return text if len(text) <= max_length else text[: max_length - 1] + "…"


class OutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthView(OutputModel):
    ok: bool = True
    romm_reachable: bool = True
    authenticated: bool = True
    user_id: int | None = None
    username: str | None = None


class PlatformView(OutputModel):
    id: int
    name: str | None = None
    slug: str | None = None
    rom_count: int | None = None
    category: str | None = None
    generation: int | None = None
    family_name: str | None = None
    is_identified: bool | None = None
    missing_from_fs: bool | None = None


class RomView(OutputModel):
    id: int
    name: str | None = None
    slug: str | None = None
    platform_id: int | None = None
    platform_name: str | None = None
    summary: str | None = None
    genres: list[str] = Field(default_factory=list)
    franchises: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    game_modes: list[str] = Field(default_factory=list)
    age_ratings: list[str] = Field(default_factory=list)
    player_count: str | None = None
    first_release_date: int | None = None
    average_rating: float | None = None
    regions: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    has_manual: bool | None = None
    has_soundtrack: bool | None = None
    is_identified: bool | None = None
    missing_from_fs: bool | None = None
    has_notes: bool | None = None
    status: str | None = None
    rating: int | None = None
    difficulty: int | None = None
    completion: int | None = None
    backlogged: bool | None = None
    hidden: bool | None = None


class UserView(OutputModel):
    id: int
    username: str
    enabled: bool | None = None


class RomUserPropertiesView(OutputModel):
    rom_id: int
    status: str | None = None
    rating: int | None = None
    difficulty: int | None = None
    completion: int | None = None
    backlogged: bool | None = None
    hidden: bool | None = None


class NoteView(OutputModel):
    id: int | None = None
    rom_id: int | None = None
    title: str | None = None
    content: str | None = None
    is_public: bool | None = None
    tags: list[str] = Field(default_factory=list)
    user_id: int | None = None
    username: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CollectionView(OutputModel):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    rom_count: int | None = None
    is_public: bool | None = None
    is_favorite: bool | None = None
    owner_username: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SmartCollectionView(CollectionView):
    filter_criteria: dict[str, Any] = Field(default_factory=dict)
    filter_summary: str | None = None


class PlaySessionView(OutputModel):
    id: int
    rom_id: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: int | None = None


T = TypeVar("T", bound=OutputModel)


class ListView(OutputModel, Generic[T]):
    items: list[T]
    count: int
    total: int | None = None
    limit: int | None = None
    offset: int | None = None


class OperationView(OutputModel):
    ok: bool = True
    action: str
    resource_id: int | None = None
    collection_id: int | None = None
    rom_ids: list[int] = Field(default_factory=list)


def _mapping(value: Any) -> dict[str, Any]:
    return sanitize_outbound(value) if isinstance(value, dict) else {}


def _items(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("items", "results", "roms", "platforms", "users", "notes", "collections", "smart_collections", "play_sessions", "sessions"):
            if isinstance(value.get(key), list):
                return value[key]
    return []


def _total(value: Any, fallback: int) -> int | None:
    data = _mapping(value)
    for key in ("total", "total_count", "count"):
        candidate = data.get(key)
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            return candidate
    return fallback


def _text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _strings(value: Any, limit: int = 50, item_limit: int = 160) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    result: list[str] = []
    for item in list(value)[:limit]:
        text = _text(item, item_limit)
        if text is not None:
            result.append(text)
    return result


def project_health(value: Any) -> HealthView:
    data = _mapping(value)
    return HealthView(
        user_id=data.get("id") if isinstance(data.get("id"), int) else None,
        username=_text(data.get("username"), 200),
    )


def project_platform(value: Any) -> PlatformView:
    data = _mapping(value)
    platform_id = data.get("id")
    if not isinstance(platform_id, int):
        raise ValueError("RomM platform response omitted its internal ID")
    name = data.get("custom_name") or data.get("display_name") or data.get("name") or data.get("slug")
    return PlatformView(
        id=platform_id,
        name=_text(name, 240),
        slug=_text(data.get("slug"), 160),
        rom_count=data.get("rom_count") if isinstance(data.get("rom_count"), int) else None,
        category=_text(data.get("category"), 120),
        generation=data.get("generation") if isinstance(data.get("generation"), int) else None,
        family_name=_text(data.get("family_name"), 200),
        is_identified=data.get("is_identified") if isinstance(data.get("is_identified"), bool) else None,
        missing_from_fs=data.get("missing_from_fs") if isinstance(data.get("missing_from_fs"), bool) else None,
    )


def project_platform_list(value: Any) -> ListView[PlatformView]:
    raw_items = _items(value)
    items = [project_platform(item) for item in raw_items[:200] if isinstance(item, dict)]
    return ListView[PlatformView](items=items, count=len(items), total=_total(value, len(raw_items)))


def project_rom(value: Any, *, fallback_id: int | None = None, compact: bool = False) -> RomView:
    data = _mapping(value)
    rom_id = data.get("id") if isinstance(data.get("id"), int) else fallback_id
    if rom_id is None:
        raise ValueError("RomM ROM response omitted its internal ID")
    metadata = _mapping(data.get("metadatum"))
    user = _mapping(data.get("rom_user"))
    name = data.get("name") or data.get("fs_name_no_tags") or data.get("fs_name_no_ext")
    return RomView(
        id=rom_id,
        name=_text(name, 300),
        slug=_text(data.get("slug"), 200),
        platform_id=data.get("platform_id") if isinstance(data.get("platform_id"), int) else None,
        platform_name=_text(data.get("platform_display_name") or data.get("platform_custom_name"), 240),
        summary=None if compact else _text(data.get("summary"), 4000),
        genres=_strings(metadata.get("genres")),
        franchises=_strings(metadata.get("franchises")),
        companies=_strings(metadata.get("companies")),
        game_modes=_strings(metadata.get("game_modes")),
        age_ratings=_strings(metadata.get("age_ratings")),
        player_count=_text(metadata.get("player_count"), 80),
        first_release_date=metadata.get("first_release_date") if isinstance(metadata.get("first_release_date"), int) else None,
        average_rating=float(metadata["average_rating"]) if isinstance(metadata.get("average_rating"), (int, float)) else None,
        regions=_strings(data.get("regions")),
        languages=_strings(data.get("languages")),
        tags=_strings(data.get("tags")),
        has_manual=data.get("has_manual") if isinstance(data.get("has_manual"), bool) else None,
        has_soundtrack=data.get("has_soundtrack") if isinstance(data.get("has_soundtrack"), bool) else None,
        is_identified=data.get("is_identified") if isinstance(data.get("is_identified"), bool) else None,
        missing_from_fs=data.get("missing_from_fs") if isinstance(data.get("missing_from_fs"), bool) else None,
        has_notes=data.get("has_notes") if isinstance(data.get("has_notes"), bool) else None,
        status=_text(user.get("status"), 80),
        rating=user.get("rating") if isinstance(user.get("rating"), int) else None,
        difficulty=user.get("difficulty") if isinstance(user.get("difficulty"), int) else None,
        completion=user.get("completion") if isinstance(user.get("completion"), int) else None,
        backlogged=user.get("backlogged") if isinstance(user.get("backlogged"), bool) else None,
        hidden=user.get("hidden") if isinstance(user.get("hidden"), bool) else None,
    )


def project_rom_list(value: Any, *, limit: int, offset: int) -> ListView[RomView]:
    all_items = _items(value)
    raw_items = all_items[:limit]
    items = [project_rom(item, compact=True) for item in raw_items if isinstance(item, dict)]
    return ListView[RomView](items=items, count=len(items), total=_total(value, len(all_items)), limit=limit, offset=offset)


def project_user(value: Any) -> UserView:
    data = _mapping(value)
    user_id = data.get("id")
    if not isinstance(user_id, int):
        raise ValueError("RomM user response omitted its internal ID")
    username = _text(data.get("username"), 200) or f"User {user_id}"
    enabled = data.get("enabled") if isinstance(data.get("enabled"), bool) else None
    return UserView(id=user_id, username=username, enabled=enabled)


def project_user_list(value: Any) -> ListView[UserView]:
    raw_items = _items(value)
    items = [project_user(item) for item in raw_items[:200] if isinstance(item, dict)]
    return ListView[UserView](items=items, count=len(items), total=_total(value, len(raw_items)))


def project_rom_user_properties(value: Any, *, fallback_rom_id: int) -> RomUserPropertiesView:
    data = _mapping(value)
    rom_id = data.get("rom_id") if isinstance(data.get("rom_id"), int) else fallback_rom_id
    return RomUserPropertiesView(
        rom_id=rom_id,
        status=_text(data.get("status"), 80),
        rating=data.get("rating") if isinstance(data.get("rating"), int) else None,
        difficulty=data.get("difficulty") if isinstance(data.get("difficulty"), int) else None,
        completion=data.get("completion") if isinstance(data.get("completion"), int) else None,
        backlogged=data.get("backlogged") if isinstance(data.get("backlogged"), bool) else None,
        hidden=data.get("hidden") if isinstance(data.get("hidden"), bool) else None,
    )


def project_note(value: Any, *, fallback_rom_id: int | None = None, fallback_note_id: int | None = None) -> NoteView:
    data = _mapping(value)
    note_id = data.get("id") if isinstance(data.get("id"), int) else fallback_note_id
    rom_id = data.get("rom_id") if isinstance(data.get("rom_id"), int) else fallback_rom_id
    return NoteView(
        id=note_id,
        rom_id=rom_id,
        title=_text(data.get("title"), 300),
        content=_text(data.get("content"), 6000),
        is_public=data.get("is_public") if isinstance(data.get("is_public"), bool) else None,
        tags=_strings(data.get("tags"), 50, 120),
        user_id=data.get("user_id") if isinstance(data.get("user_id"), int) else None,
        username=_text(data.get("username"), 200),
        created_at=_text(data.get("created_at"), 80),
        updated_at=_text(data.get("updated_at"), 80),
    )


def project_note_list(value: Any, *, rom_id: int) -> ListView[NoteView]:
    raw_items = _items(value)
    items = [project_note(item, fallback_rom_id=rom_id) for item in raw_items[:100] if isinstance(item, dict)]
    return ListView[NoteView](items=items, count=len(items), total=_total(value, len(raw_items)))


def project_collection(value: Any, *, fallback_id: int | None = None) -> CollectionView:
    data = _mapping(value)
    collection_id = data.get("id") if isinstance(data.get("id"), int) else fallback_id
    return CollectionView(
        id=collection_id,
        name=_text(data.get("name"), 300),
        description=_text(data.get("description"), 2000),
        rom_count=data.get("rom_count") if isinstance(data.get("rom_count"), int) else None,
        is_public=data.get("is_public") if isinstance(data.get("is_public"), bool) else None,
        is_favorite=data.get("is_favorite") if isinstance(data.get("is_favorite"), bool) else None,
        owner_username=_text(data.get("owner_username"), 200),
        created_at=_text(data.get("created_at"), 80),
        updated_at=_text(data.get("updated_at"), 80),
    )


def project_collection_list(value: Any) -> ListView[CollectionView]:
    raw_items = _items(value)
    items = [project_collection(item) for item in raw_items[:200] if isinstance(item, dict)]
    return ListView[CollectionView](items=items, count=len(items), total=_total(value, len(raw_items)))


_SMART_FILTER_KEYS = {
    "platform_ids", "collection_id", "virtual_collection_id", "search_term", "matched", "favorite",
    "duplicate", "last_played", "playable", "has_ra", "has_saves", "has_states", "has_soundtrack",
    "missing", "verified", "genres", "franchises", "collections", "companies", "age_ratings", "statuses",
    "regions", "languages", "player_counts", "metadata_providers", "tags", "genres_logic", "franchises_logic",
    "collections_logic", "companies_logic", "age_ratings_logic", "regions_logic", "languages_logic", "statuses_logic",
    "player_counts_logic", "metadata_providers_logic", "tags_logic", "order_by", "order_dir",
}


def _project_filter_criteria(value: Any) -> dict[str, Any]:
    data = _mapping(value)
    safe: dict[str, Any] = {}
    for key in _SMART_FILTER_KEYS:
        if key not in data:
            continue
        item = data[key]
        if isinstance(item, list):
            safe[key] = item[:50]
        elif isinstance(item, (str, int, bool)) or item is None:
            safe[key] = item
    return sanitize_outbound(safe)


def project_smart_collection(value: Any, *, fallback_id: int | None = None) -> SmartCollectionView:
    base = project_collection(value, fallback_id=fallback_id)
    data = _mapping(value)
    return SmartCollectionView(
        **base.model_dump(),
        filter_criteria=_project_filter_criteria(data.get("filter_criteria")),
        filter_summary=_text(data.get("filter_summary"), 2000),
    )


def project_smart_collection_list(value: Any) -> ListView[SmartCollectionView]:
    raw_items = _items(value)
    items = [project_smart_collection(item) for item in raw_items[:200] if isinstance(item, dict)]
    return ListView[SmartCollectionView](items=items, count=len(items), total=_total(value, len(raw_items)))


def project_play_session(value: Any) -> PlaySessionView:
    data = _mapping(value)
    session_id = data.get("id")
    if not isinstance(session_id, int):
        raise ValueError("RomM play-session response omitted its internal ID")
    return PlaySessionView(
        id=session_id,
        rom_id=data.get("rom_id") if isinstance(data.get("rom_id"), int) else None,
        start_time=_text(data.get("start_time"), 80),
        end_time=_text(data.get("end_time"), 80),
        duration_ms=data.get("duration_ms") if isinstance(data.get("duration_ms"), int) else None,
    )


def project_play_session_list(value: Any, *, limit: int, offset: int) -> ListView[PlaySessionView]:
    all_items = _items(value)
    raw_items = all_items[:limit]
    items = [project_play_session(item) for item in raw_items if isinstance(item, dict)]
    return ListView[PlaySessionView](items=items, count=len(items), total=_total(value, len(all_items)), limit=limit, offset=offset)
