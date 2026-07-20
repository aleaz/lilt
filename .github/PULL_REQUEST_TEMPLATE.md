## Description

Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

Docs updated: … / Docs N/A: …

## Type of change

Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Verification

Please describe the tests that you ran to verify your changes.

- [ ] `make ci` passes locally (matches GitHub Actions)
- [ ] Optional: `make check-all` used first for auto-format/fix
- [ ] I have added or updated tests that prove my fix/feature

Full author checklist: [docs/development/pull-request-checklist.md](../docs/development/pull-request-checklist.md)

## Checklist

- [ ] I followed [pull-request-checklist.md](../docs/development/pull-request-checklist.md)
- [ ] My code follows project style (`ruff` / `mypy` via `make ci`)
- [ ] I have performed a self-review of my own code
- [ ] If behavior in `src/lilt/` changed, the relevant L1 guide under `docs/architecture/` was updated (per [documentation update policy](../docs/architecture/README.md#documentation-update-policy))
- [ ] If operator-facing CLI or config changed, [docs/reference/](../docs/reference/cli.md) / guides under [docs/](../docs/README.md) were updated
- [ ] If a Known gap was resolved, it was removed from the guide (not left as history)
- [ ] Architecture invariants preserved (thin CLI, human locks, product boundary) — [engineering-invariants.md](../docs/development/engineering-invariants.md)
