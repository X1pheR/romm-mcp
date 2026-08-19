# Tool reference

RomM MCP v0.1.0 exposes exactly 26 explicit tools. It does not expose a generic HTTP/API passthrough.

| Tool | Access | Destructive | Purpose / side effects |
|---|---|---:|---|
| `health` | Read | No | Verifies authenticated API access and returns the current user plus effective permissions. |
| `list_platforms` | Read | No | Lists platforms visible to the token. |
| `get_platform` | Read | No | Gets one platform by internal ID. |
| `list_roms` | Read | No | Searches/lists ROMs with bounded pagination and common filters. |
| `get_rom` | Read | No | Gets one ROM by internal ID. |
| `update_rom_metadata` | Write | No | Updates only `name`, `name_sort_key` and `summary`. Remote cover/manual fetching, asset writes and provider-ID mutation are excluded. |
| `update_rom_user_properties` | Write | No | Updates the token owner's ROM status, rating, difficulty, completion, backlog and hidden state. |
| `list_rom_notes` | Read | No | Lists notes for one ROM. |
| `create_rom_note` | Write | No | Creates a note with explicit title/content/public/tags fields. |
| `update_rom_note` | Write | No | Updates only supported note fields. |
| `delete_rom_note` | Write | Yes | Deletes one note and requires `confirm=true`. Never deletes ROM files. |
| `list_collections` | Read | No | Lists regular collections. |
| `get_collection` | Read | No | Gets one regular collection. |
| `create_collection` | Write | No | Creates a collection without artwork upload. |
| `update_collection` | Write | No | Updates metadata and/or membership. A rename with omitted membership preserves existing ROM membership. |
| `delete_collection` | Write | Yes | Requires `confirm=true`. Deletes the collection definition and RomM-managed resources for that collection (for example collection artwork); ROM files are never deleted. |
| `add_roms_to_collection` | Write | No | Adds ROM IDs to a regular collection. |
| `remove_roms_from_collection` | Write | No | Removes membership only; it does not delete ROMs or ROM files. |
| `list_smart_collections` | Read | No | Lists smart collections. |
| `get_smart_collection` | Read | No | Gets one smart collection. |
| `create_smart_collection` | Write | No | Creates a smart collection using the explicit v0.1 filter schema below. |
| `update_smart_collection` | Write | No | Updates smart-collection metadata and/or explicit filter criteria. |
| `delete_smart_collection` | Write | Yes | Deletes one smart-collection definition and requires `confirm=true`. ROM files are never deleted. |
| `list_users` | Read | No | Lists users visible to `users.read`; no user mutation is exposed. |
| `get_user` | Read | No | Gets one user; no permission or authorization mutation is exposed. |
| `list_play_sessions` | Read | No | Lists play sessions for the token owner with bounded pagination. |

## Smart-collection filter schema

`create_smart_collection` and `update_smart_collection` do not accept an arbitrary object. v0.1 exposes the RomM 5.1 filter fields below:

- IDs/search: `platform_ids`, `collection_id`, `virtual_collection_id`, `search_term`.
- Booleans: `matched`, `favorite`, `duplicate`, `last_played`, `playable`, `has_ra`, `has_saves`, `has_states`, `has_soundtrack`, `missing`, `verified`.
- Multi-value filters: `genres`, `franchises`, `collections`, `companies`, `age_ratings`, `statuses`, `regions`, `languages`, `player_counts`, `metadata_providers`, `tags`.
- Multi-value logic (`any` or `all`): `genres_logic`, `franchises_logic`, `collections_logic`, `companies_logic`, `age_ratings_logic`, `regions_logic`, `languages_logic`, `statuses_logic`, `player_counts_logic`, `metadata_providers_logic`, `tags_logic`.
- Ordering: `order_by`, `order_dir` (`asc` or `desc`).

## Intentionally unavailable

These are absent from the MCP registry rather than merely discouraged:

- Generic API/HTTP calls.
- ROM or ROM-file deletion.
- ROM/file upload, replacement or conversion.
- Remote cover/manual fetching or direct asset mutation.
- Library scans, background tasks and bulk metadata refresh.
- Platform/system configuration mutation.
- Client-token creation, regeneration or deletion.
- User, permission-group or authorization mutation.
- Device/sync mutation.
