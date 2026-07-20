#!/usr/bin/env bash
# Warn-only: report LiltConfig field names missing from docs/reference/config.md.
# Always exits 0 (does not fail CI). Not part of `make ci`.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOC="docs/reference/config.md"
if [[ ! -f "$DOC" ]]; then
  echo "WARN: missing $DOC"
  exit 0
fi

uv run python - "$DOC" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel

from lilt.models.config import LiltConfig

doc_path = Path(sys.argv[1])
doc_text = doc_path.read_text(encoding="utf-8")


def collect_fields(model: type[BaseModel], prefix: str = "") -> list[str]:
    names: list[str] = []
    for name, field in model.model_fields.items():
        path = f"{prefix}.{name}" if prefix else name
        names.append(path)
        ann = field.annotation
        origin = getattr(ann, "__origin__", None)
        args = getattr(ann, "__args__", ())
        candidates: list[type] = []
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            candidates.append(ann)
        elif origin is not None:
            for arg in args:
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    candidates.append(arg)
        for nested in candidates:
            names.extend(collect_fields(nested, path))
    return names


missing = [p for p in collect_fields(LiltConfig) if p.split(".")[-1] not in doc_text]
if missing:
    print(f"WARN: {len(missing)} config field name(s) not found in {doc_path}:")
    for path in missing:
        print(f"  - {path}")
else:
    print(f"config-doc-sync-check: all field leaf names appear in {doc_path}.")
PY

exit 0
