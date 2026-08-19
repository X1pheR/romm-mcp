#!/usr/bin/env bash
set -euo pipefail

command -v uv >/dev/null 2>&1 || {
  echo "uv is required" >&2
  exit 1
}

uv venv --clear --python 3.12
uv sync --frozen --extra test
.venv/bin/python - <<'PY'
import importlib.metadata
import tomllib

project = tomllib.load(open("pyproject.toml", "rb"))["project"]["version"]
installed = importlib.metadata.version("romm-mcp")
assert installed == project, (installed, project)
PY
.venv/bin/python -m compileall -q src tests
.venv/bin/pytest -p no:cacheprovider
rm -rf dist
uv build --wheel --out-dir dist

test -n "$(find dist -maxdepth 1 -type f -name '*.whl' -print -quit)"
