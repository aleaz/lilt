#!/usr/bin/env bash
# Fail if official Quick Start is missing required onboarding structure.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QS="$ROOT/examples/quickstart"
README="$QS/README.md"

FAIL=0
need() {
  if [[ ! -e "$1" ]]; then
    echo "MISSING: $1"
    FAIL=1
  fi
}

need "$QS/main.tex"
need "$README"

if [[ -f "$README" ]]; then
  for needle in \
    "fail-closed" \
    "allow-partial" \
    "llm.model" \
    "pipeline sync" \
    "pipeline translate" \
    "pipeline build" \
    "What was created"
  do
    if ! grep -qF "$needle" "$README"; then
      echo "Quick Start README missing required text: $needle"
      FAIL=1
    fi
  done
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "check-quickstart-structure: FAILED"
  exit 1
fi
echo "check-quickstart-structure: OK"
