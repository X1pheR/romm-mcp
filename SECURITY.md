# Security Policy

## Supported versions

Security fixes are provided for the latest released version of RomM MCP.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use [GitHub Private Vulnerability Reporting](https://github.com/X1pheR/romm-mcp/security/advisories/new) for this repository. If that channel is unavailable, contact the maintainer privately through the GitHub profile associated with this repository.

Include enough information to reproduce and assess the issue without including real RomM Client API Tokens, passwords, session cookies, ROM contents, or other private data.

## Credential model

RomM MCP is designed for a dedicated RomM Client API Token with the minimum required scopes. The token is read from `ROMM_API_TOKEN_FILE` and is never accepted as an MCP tool argument.

If a token is exposed, revoke it in RomM immediately and create a replacement. Do not reuse a token that may have been disclosed.

## Capability boundary

The v0.1 server intentionally does not expose generic HTTP passthrough, ROM/file deletion, uploads, remote cover/manual fetching, background task execution, Client API Token administration, or user/permission mutation.

Deletion of notes, regular collections and smart collections requires an explicit `confirm=true` argument. RomM's regular-collection delete endpoint also removes resources owned by that collection (for example collection artwork); this MCP never deletes ROM files.

The upstream RomM Client API Token scopes remain the hard authorization boundary. Deployments should grant only the scopes required for their selected tools.

## Outbound data boundary

RomM MCP does not intentionally return raw RomM API objects. Successful JSON responses and upstream error details first pass through a recursive sanitizer that removes credential-like values and redacts credential-bearing URL query parameters case-insensitively. Tool handlers then project upstream objects into explicit bounded response models.

The projection boundary intentionally excludes provider-specific metadata payloads and URLs, ROM filesystem paths and hashes, user email/OAuth/permission/UI/device details, collection asset internals, and play-session device/sync internals unless a future explicit tool contract requires a reviewed field. Tests use synthetic credentials only.
