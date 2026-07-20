# Contribution workflow

How changes move from idea to merge in this repository — as practiced, not as invented process.

Entry: [contributor-guide.md](contributor-guide.md). Checklist: [pull-request-checklist.md](pull-request-checklist.md). Reviewers: [code-review-guidelines.md](code-review-guidelines.md).

## Branch strategy

- Work on a **fork** or a **topic branch**.
- Open a pull request into **`main`** or **`master`** (CI watches both — [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).
- There is **no** GitFlow / release-branch ritual. Keep PRs focused and reviewable.

## Commits

- Prefer clear messages that state the **why**.
- Agents: follow [`.cursor/rules/lilt-git-agent.mdc`](../../.cursor/rules/lilt-git-agent.mdc) — commit/push/PR only when asked; no co-author trailers unless requested.

## Issues

- Bugs: [`.github/ISSUE_TEMPLATE/bug_report.md`](../../.github/ISSUE_TEMPLATE/bug_report.md)  
- Features: [`.github/ISSUE_TEMPLATE/feature_request.md`](../../.github/ISSUE_TEMPLATE/feature_request.md)  
- Link the issue from the PR when applicable (`Fixes #…`).

## Pull request process

1. Implement + tests + docs (same PR when surface/contract changes).
2. Run **`make ci`** locally (matches GitHub Actions). Use `make check-all` first if you want auto-format/fix.
3. Open PR using [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md).
4. Complete [pull-request-checklist.md](pull-request-checklist.md); state `Docs updated: …` or `Docs N/A: …`.
5. Wait for CI green and maintainer review ([code-review-guidelines.md](code-review-guidelines.md)).

There is no documented review SLA or required CODEOWNERS bot — quality is enforced by CI + human review against architecture invariants.

## Testing requirements

- Engine changes: add or update tests under `tests/` at the right layer ([testing.md](testing.md)).
- Bug fixes: include a **regression** test when feasible.
- Coverage % is **not** a CI gate; `make ci` (ruff format --check, ruff check, mypy, pytest) is.
- Do not commit large empirical campaigns or corpora — [CONTRIBUTING.md](../../CONTRIBUTING.md) empirical boundary.

## Documentation requirements

Same-PR updates when applicable ([conventions.md](conventions.md)):

| Change | Update |
|--------|--------|
| Typer command / flag | [cli.md](../reference/cli.md) + agent mirrors if they state the surface |
| `LiltConfig` / yaml keys | [config.md](../reference/config.md) |
| Domain Behavior | Matching L1 Behavior / Decisions / Known gaps |
| New term | [glossary](../architecture/00-glossary.md) first |
| Resolved Known gap | Remove from the guide (do not leave as history) |

Optional warn-only: `make docs-sync-check`.

## Release considerations

- Contributors **do not** cut release tags.
- [CHANGELOG.md](../../CHANGELOG.md) stays **Unreleased** until the maintainer tags deliberately.
- Version lives in `pyproject.toml` (public beta). CLI/config **may** change until an intentional release — call breaking changes out in the PR.
- Detail: [overview.md](overview.md#release-and-versioning-honest).

---

## Feature contribution process

### Before coding

1. Confirm the work is in product scope (not corpus/eval, not a new top-level CLI verb, not ADR revival).
2. Check [appendix-deferred](../architecture/appendix-deferred.md) — do not document deferred work as shipped.
3. Skim [engineering-invariants.md](engineering-invariants.md) and [architectural-guidelines.md](architectural-guidelines.md) for placement.
4. For layer-crossing changes, new providers, or TM schema shifts: propose the design (issue or PR description) and plan L1 **Decisions** / Behavior updates.

### During coding

- CLI: thin handlers only; orchestration in `services/`; domain in the right package.
- Use `WorkspaceContext` for workspace wiring — do not invent parallel globals.
- Preserve human locks and AccuracyGate ownership of structural accuracy.
- Add tests that lock the Behavior you care about.
- Update Derived docs in the same change set.

### After coding

- Self-review with [pull-request-checklist.md](pull-request-checklist.md).
- Run `make ci`.
- Write a PR description with motivation, risk, and verification (commands run).

---

## Bug fix process

1. **Reproduce** — CLI steps, `--debug` / `.lilt/lilt.log`, environment (see bug issue template).
2. **Investigate** — find the owning layer (parser vs TM vs validation vs services vs CLI adapter).
3. **Root cause** — fix the real owner; avoid papering over in the CLI.
4. **Regression test** — prove the failure cannot silently return.
5. **Document** — if operator-visible Behavior or CLI/config changed, update L1 and/or reference in the same PR.

---

## Documentation-only contributions

- Pick the right Diátaxis home ([docs hub](../README.md)).
- Link to L1 / reference instead of copying encyclopedias.
- Keep Critique ≠ Review; `lilt` vs `latex-lilt`.
- Do not invent CLI flags or Behavior the code does not implement.

---

## Related

- [contributor-guide.md](contributor-guide.md)
- [ai-contribution-guidelines.md](ai-contribution-guidelines.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
