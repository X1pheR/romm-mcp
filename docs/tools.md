# Tool reference

RomM MCP v0.1.1 exposes exactly 26 explicit tools. It does not expose a generic HTTP/API passthrough.

| Tool | Access | Destructive | Purpose / side effects |
|---|---|---:|---|
| `health` | Read | No | Verifies authenticated API access and returns non-sensitive connectivity identity only. |
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

## Outbound response-contract matrix

All upstream responses are recursively sanitized before these per-tool allow-list projections are applied. URL query parameter names such as token, password, secret and API-key variants are matched case-insensitively. The matrix is intentionally explicit so every exposed tool has a reviewed outbound contract.

| Tool | Structured output | Retained fields / bounded result | Explicitly excluded upstream detail |
|---|---|---|---|
| `health` | `HealthView` | Connectivity/authentication booleans plus current `user_id` and `username`. | Effective permissions/scopes, email, UI/device/RA data and other `/users/me` fields. |
| `list_platforms` | `ListView[PlatformView]` | Up to 200 platform IDs, display names/slugs, ROM count and compact classification/status fields. | Provider IDs/URLs, firmware payloads, filesystem sizes and timestamps. |
| `get_platform` | `PlatformView` | One platform ID, display name/slug, ROM count and compact classification/status fields. | Provider IDs/URLs, firmware payloads, filesystem sizes and timestamps. |
| `list_roms` | `ListView[RomView]` | Requested page up to 200 ROM IDs, names, platform identity, compact metadata facets and personal status fields; summary omitted in list mode. | Provider metadata/URLs/IDs, files/paths/hashes, screenshots/assets, sibling payloads and unrelated indexes/filter payloads. |
| `get_rom` | `RomView` | One ROM ID, name/platform identity, bounded summary, common metadata facets and personal status fields. | Provider metadata/URLs/IDs, files/paths/hashes, screenshots/assets and sibling payloads. |
| `update_rom_metadata` | `RomView` | Bounded post-update ROM projection, always retaining the target ROM ID. | Raw write response, provider/file/asset internals. |
| `update_rom_user_properties` | `RomUserPropertiesView` | Target `rom_id` plus only supported personal status/rating/difficulty/completion/backlog/hidden fields. | Internal RomUser record ID, user ID, timestamps and unrelated ROM/provider/file fields. |
| `list_rom_notes` | `ListView[NoteView]` | Up to 100 note IDs, ROM IDs, bounded title/content/tags, visibility, author IDs/usernames and timestamps. | Avatar paths, user profile/authorization objects and unrelated note/user internals. |
| `create_rom_note` | `NoteView` | Created note identity and bounded supported note fields. | Raw write response and unrelated user/profile internals. |
| `update_rom_note` | `NoteView` | Updated note identity and bounded supported note fields. | Raw write response and unrelated user/profile internals. |
| `delete_rom_note` | `OperationView` | `ok`, action and deleted note ID. | Raw delete response. |
| `list_collections` | `ListView[CollectionView]` | Up to 200 collection IDs, name/description, ROM count, visibility/favorite state, owner username and timestamps. | Full `rom_ids`, cover paths/URLs, owner user ID and asset internals. |
| `get_collection` | `CollectionView` | One compact collection summary with stable collection ID. | Full `rom_ids`, cover paths/URLs, owner user ID and asset internals. |
| `create_collection` | `CollectionView` | Created collection identity and compact metadata. | Raw write response, artwork/asset internals and full membership payload. |
| `update_collection` | `CollectionView` | Updated collection identity and compact metadata. | Raw write response, artwork/asset internals and full membership payload. |
| `delete_collection` | `OperationView` | `ok`, action and deleted collection ID. | Raw delete response. |
| `add_roms_to_collection` | `OperationView` | `ok`, action, collection ID and explicitly supplied ROM IDs. | Raw mutation response and collection internals. |
| `remove_roms_from_collection` | `OperationView` | `ok`, action, collection ID and explicitly supplied ROM IDs. | Raw mutation response and collection internals. |
| `list_smart_collections` | `ListView[SmartCollectionView]` | Up to 200 compact collection fields plus only the supported v0.1 smart-filter keys and bounded filter summary. | Asset internals, owner user ID and unknown/arbitrary filter fields. |
| `get_smart_collection` | `SmartCollectionView` | One compact smart collection plus only supported filter keys. | Asset internals, owner user ID and unknown/arbitrary filter fields. |
| `create_smart_collection` | `SmartCollectionView` | Created compact smart collection plus reviewed filter criteria. | Raw write response and arbitrary upstream fields. |
| `update_smart_collection` | `SmartCollectionView` | Updated compact smart collection plus reviewed filter criteria. | Raw write response and arbitrary upstream fields. |
| `delete_smart_collection` | `OperationView` | `ok`, action and deleted smart-collection ID. | Raw delete response. |
| `list_users` | `ListView[UserView]` | Up to 200 user IDs, usernames and enabled state. | Email, role, permission group, OAuth scopes, UI settings, device ID, avatar/RA data and timestamps. |
| `get_user` | `UserView` | User ID, username and enabled state. | Email, role, permission group, OAuth scopes, UI settings, device ID, avatar/RA data and timestamps. |
| `list_play_sessions` | `ListView[PlaySessionView]` | Requested page up to 200 session IDs, ROM IDs, start/end and duration. | User/device IDs, sync-session ID, save slot and unrelated timestamps. |

All 26 tools also publish MCP annotations. Reads set `readOnlyHint=true`, all tools set `openWorldHint=true` because they communicate with RomM, and only note/regular-collection/smart-collection deletion sets `destructiveHint=true`. Read tools set `idempotentHint=true`; write tools are conservatively not advertised as idempotent.

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
