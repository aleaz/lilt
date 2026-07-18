#!/usr/bin/env bash
# Warn-only: if src/lilt paths changed vs base without mapped docs, print warnings.
# Always exits 0 (does not fail CI). Override base with DOCS_SYNC_BASE=origin/main.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BASE="${DOCS_SYNC_BASE:-origin/main}"
if ! git rev-parse --verify "$BASE" >/dev/null 2>&1; then
  BASE="HEAD~1"
fi

CHANGED="$(
  {
    git diff --name-only "${BASE}...HEAD" 2>/dev/null || true
    git diff --name-only HEAD 2>/dev/null || true
    git diff --name-only --cached 2>/dev/null || true
  } | sort -u
)"

if [[ -z "${CHANGED}" ]]; then
  echo "docs-sync-check: no changed files vs ${BASE} / working tree."
  exit 0
fi

echo "${CHANGED}" | grep -q '^src/lilt/' || {
  echo "docs-sync-check: no src/lilt changes; OK."
  exit 0
}

doc_touched() {
  echo "${CHANGED}" | grep -qxF "$1"
}

WARN=0
warn() {
  echo "WARN: $1"
  WARN=1
}

cli=0
services=0
parser=0
tm=0
translation=0
llm=0
build=0
telemetry=0
config=0

while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  case "$f" in
    src/lilt/cli/*) cli=1 ;;
    src/lilt/services/*) services=1 ;;
    src/lilt/parser/*) parser=1 ;;
    src/lilt/tm/*) tm=1 ;;
    src/lilt/models/segment*) tm=1 ;;
    src/lilt/models/segment_transition*) tm=1 ;;
    src/lilt/core/sync.py) tm=1 ;;
    src/lilt/core/review_policy.py) tm=1 ;;
    src/lilt/core/translation/*) translation=1 ;;
    src/lilt/llm/*) llm=1 ;;
    src/lilt/core/build.py|src/lilt/core/build/*) build=1 ;;
    src/lilt/telemetry/*) telemetry=1 ;;
    src/lilt/models/config*) config=1 ;;
  esac
done <<< "${CHANGED}"

if [[ "$cli" -eq 1 ]] && ! doc_touched 'docs/reference/cli.md'; then
  warn "src/lilt/cli changed but docs/reference/cli.md was not updated"
fi
if [[ "$services" -eq 1 ]] && [[ "$cli" -eq 0 ]] && ! doc_touched 'docs/architecture/07-cli-application.md'; then
  warn "src/lilt/services changed but docs/architecture/07-cli-application.md was not updated"
fi
if [[ "$parser" -eq 1 ]] && ! doc_touched 'docs/architecture/03-parser-masking.md'; then
  warn "src/lilt/parser changed but docs/architecture/03-parser-masking.md was not updated"
fi
if [[ "$tm" -eq 1 ]] && ! doc_touched 'docs/architecture/02-persistence.md'; then
  warn "TM/segment/sync/review paths changed but docs/architecture/02-persistence.md was not updated"
fi
if [[ "$translation" -eq 1 ]] && ! doc_touched 'docs/architecture/04-translation-engine.md'; then
  warn "core/translation changed but docs/architecture/04-translation-engine.md was not updated"
fi
if [[ "$llm" -eq 1 ]] && ! doc_touched 'docs/architecture/05-llm-layer.md'; then
  warn "src/lilt/llm changed but docs/architecture/05-llm-layer.md was not updated"
fi
if [[ "$build" -eq 1 ]] && ! doc_touched 'docs/architecture/06-build-output.md'; then
  warn "build paths changed but docs/architecture/06-build-output.md was not updated"
fi
if [[ "$telemetry" -eq 1 ]] && ! doc_touched 'docs/architecture/08-observability.md'; then
  warn "telemetry changed but docs/architecture/08-observability.md was not updated"
fi
if [[ "$config" -eq 1 ]]; then
  if ! doc_touched 'docs/reference/config.md' && ! doc_touched 'docs/architecture/01-platform.md'; then
    warn "config-related paths changed but neither docs/reference/config.md nor 01-platform.md was updated"
  fi
fi

if [[ "$WARN" -eq 0 ]]; then
  echo "docs-sync-check: OK (mapped docs present or no matrix hit)."
else
  echo "docs-sync-check: warnings above are advisory (exit 0). See .cursor/rules/lilt-architecture.mdc path→docs matrix."
fi
exit 0
