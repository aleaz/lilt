#!/usr/bin/env bash
# Fail if public onboarding markdown links to missing relative files.
# Scope: README.md, docs/README.md, docs/getting-started.md, examples/quickstart/README.md

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FILES=(
  README.md
  docs/README.md
  docs/getting-started.md
  examples/quickstart/README.md
)

FAIL=0

check_file() {
  local file="$1"
  local dir
  dir="$(dirname "$file")"
  # Markdown links: [text](path) — skip http(s), mailto, anchors-only
  while IFS= read -r target; do
    [[ -z "$target" ]] && continue
    [[ "$target" == http://* || "$target" == https://* || "$target" == mailto:* ]] && continue
    # Strip anchors
    local path="${target%%#*}"
    [[ -z "$path" ]] && continue
    local resolved
    if [[ "$path" == /* ]]; then
      resolved="$ROOT$path"
    else
      resolved="$ROOT/$dir/$path"
    fi
    # normalize ..
    resolved="$(python3 -c 'import os,sys; print(os.path.normpath(sys.argv[1]))' "$resolved")"
    if [[ ! -e "$resolved" ]]; then
      echo "MISSING: $file -> $target (resolved $resolved)"
      FAIL=1
    fi
  done < <(grep -oE '\[[^]]+\]\([^)]+\)' "$file" | sed -E 's/^\[[^]]+\]\(([^)]+)\)$/\1/' || true)
}

for f in "${FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "MISSING file: $f"
    FAIL=1
    continue
  fi
  check_file "$f"
done

if [[ "$FAIL" -ne 0 ]]; then
  echo "check-doc-links: FAILED"
  exit 1
fi
echo "check-doc-links: OK"
