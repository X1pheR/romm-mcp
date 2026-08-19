from .server import mcp


def main() -> None:
    mcp.run(transport="stdio")


__all__ = ["main", "mcp"]
