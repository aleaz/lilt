# Pull request checklist

Author self-check before opening or updating a PR. GitHub template: [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md). Process: [contribution-workflow.md](contribution-workflow.md).

## Purpose

- [ ] PR description explains **why** (motivation) and **what** changed
- [ ] Linked issue when applicable (`Fixes #…`)
- [ ] Type of change called out (bug / feature / docs / breaking)

## Quality gates

- [ ] `make ci` passes locally (matches GitHub Actions)
- [ ] Optional: ran `make check-all` first for auto-format/fix
- [ ] No new ruff/mypy failures
- [ ] Self-review of the diff completed

## Tests

- [ ] Tests added or updated for the Behavior under change
- [ ] Bug fixes include a regression test when feasible
- [ ] No corpus / evaluation sandboxes / model traces committed

## Documentation

- [ ] `Docs updated: …` **or** `Docs N/A: …` stated in the PR
- [ ] Typer / flags → [cli.md](../reference/cli.md) (+ agent mirrors if they describe the surface)
- [ ] Config keys → [config.md](../reference/config.md)
- [ ] Domain Behavior → matching L1 guide; Known gap removed if resolved
- [ ] New terms → [glossary](../architecture/00-glossary.md)
- [ ] Optional: `make docs-sync-check` reviewed (warn-only)

## Architecture & product boundary

- [ ] Dependency direction preserved (no fat CLI orchestration)
- [ ] No new top-level CLI verbs outside `project` / `pipeline` / `tm` / `telemetry`
- [ ] Human locks (`reviewed` / `approved` / `locked`) still honored
- [ ] AccuracyGate / validators still own structural accuracy
- [ ] No `docs/adrs/`, corpus trees, or deferred-as-shipped docs
- [ ] Placement matches [architectural-guidelines.md](architectural-guidelines.md)

## Terminology & examples

- [ ] Critique ≠ Review; `refined` ≠ `approved`
- [ ] Import/CLI `lilt`; dist `latex-lilt`
- [ ] Operator examples / guides updated if the user-facing path changed

## Compatibility & complexity

- [ ] Breaking CLI/config changes called out explicitly (public beta)
- [ ] No unnecessary complexity or speculative abstractions
- [ ] Performance claims (if any) are measurable — no invented SLOs

## Release

- [ ] No release tags or fake version bumps unless the maintainer asked
- [ ] CHANGELOG only if the maintainer / release process expects it for this change

---

*Reviewers use [code-review-guidelines.md](code-review-guidelines.md).*
