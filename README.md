# RomM MCP

`romm-mcp` is a community-maintained Model Context Protocol (MCP) server for bounded management of [RomM](https://github.com/rommapp/romm) through RomM's authenticated API. It is not affiliated with, endorsed by, or maintained by the RomM project.

The server is intentionally narrower than the complete RomM API: it provides explicit typed read/write tools for common library-management tasks without a generic HTTP passthrough or broad administrative escape hatch.

## Status and compatibility

- Initial release line: `0.1.x`.
- Tested against RomM `5.1.0` API contracts.
- Requires Python `3.12` or newer.
- Uses RomM Client API Tokens (`rmm_...`) as bearer credentials.

Later RomM versions may remain compatible, but they are not claimed as tested until verified.

## Capability boundary

Included in v0.1:

- Platform and ROM discovery.
- Bounded ROM text metadata updates (`name`, `name_sort_key`, `summary`).
- Personal ROM status/rating/completion properties.
- ROM notes.
- Regular collections and collection membership.
- Smart collections with an explicit RomM 5.1 filter schema.
- User visibility and play-session reads.

Intentionally excluded from v0.1:

- Generic API/HTTP passthrough.
- ROM or ROM-file deletion.
- ROM/file uploads or replacement.
- Remote cover/manual fetching and asset mutation.
- Library scans, background tasks and bulk metadata refresh.
- Platform/system configuration mutation.
- Client-token administration.
- User, permission-group or authorization mutation.
- Device/sync mutation.

Removing ROMs from a collection only changes collection membership. Deleting a regular collection requires `confirm=true`; RomM also removes that collection's own managed artwork/resource directory, but ROM files are never deleted by this MCP.

See [`docs/tools.md`](docs/tools.md) for the complete 26-tool surface and per-tool side effects.

## Installation

Releases are distributed as immutable GitHub Release wheels. `romm-mcp` is not currently published to PyPI.

For v0.1.0:

```bash
uvx --python 3.12 \
  --from https://github.com/X1pheR/romm-mcp/releases/download/v0.1.0/romm_mcp-0.1.0-py3-none-any.whl \
  romm-mcp
```

Each release includes `SHA256SUMS`. For pinned or production use, verify the wheel digest before deployment and, where supported, pin the artifact URL with its SHA-256 hash.

## Configuration

The server requires a dedicated RomM Client API Token stored in a file. Token values are never accepted as MCP tool arguments.

```text
ROMM_BASE_URL=https://romm.example.com
ROMM_API_TOKEN_FILE=/path/to/romm-api-token
ROMM_TIMEOUT_SECONDS=15
```

`ROMM_BASE_URL` must be an absolute `http://` or `https://` URL. `ROMM_TIMEOUT_SECONDS` must be greater than 0 and at most 300 seconds.

For the complete v0.1 toolset, the intended RomM scope set is:

```text
me.read
platforms.read
roms.read
roms.write
roms.user.read
roms.user.write
collections.read
collections.write
users.read
```

`users.write`, task execution, platform-write, device-write and asset-write scopes are not required by v0.1.

## MCP client example

```json
{
  "command": "uvx",
  "args": [
    "--python",
    "3.12",
    "--from",
    "https://github.com/X1pheR/romm-mcp/releases/download/v0.1.0/romm_mcp-0.1.0-py3-none-any.whl",
    "romm-mcp"
  ],
  "env": {
    "ROMM_BASE_URL": "https://romm.example.com",
    "ROMM_API_TOKEN_FILE": "/path/to/romm-api-token",
    "ROMM_TIMEOUT_SECONDS": "15"
  }
}
```

## Security model

The RomM Client API Token and its upstream scopes are the hard authorization boundary. Use a dedicated token and grant only the scopes required by the tools you intend to expose.

The MCP layer adds a second boundary:

- Credentials are file-backed and omitted from tool schemas.
- There is no generic request tool.
- Remote cover/manual URLs are not accepted, avoiding server-side asset fetch/write behavior through this MCP.
- Note, regular-collection and smart-collection deletion require explicit `confirm=true`.
- ROM/file deletion, uploads, task execution and authorization administration are absent from the tool registry.

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting and credential-handling guidance.

## Development

CI and release verification use an exact-pinned dependency set in `requirements-dev.txt` while the published package keeps compatible dependency ranges in `pyproject.toml`.

```bash
bash ./scripts/verify.sh
```

The verification script creates an isolated Python 3.12 environment, synchronizes the pinned dependency set, compiles the package, runs the test suite and builds the release wheel.

## Upstream and license

This repository is an independent community integration for [RomM](https://github.com/rommapp/romm). RomM is a separate upstream project governed by its own license and project policies.

`romm-mcp` is licensed under the [MIT License](LICENSE).
