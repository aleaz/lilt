# Code review guidelines

What maintainers and reviewers verify. Authors: complete [pull-request-checklist.md](pull-request-checklist.md) first. Culture: [engineering-philosophy.md](engineering-philosophy.md).

There is **no** documented review SLA or required CODEOWNERS automation — review is human + CI (`make ci`).

## Always verify

| Area | Pass when |
|------|-----------|
| **CI** | GitHub Actions `make ci` is green |
| **Purpose** | Motivation is clear; scope matches the diff |
| **Architecture** | Thin CLI; logic in services/core/…; dependency direction holds |
| **Product boundary** | No corpus/eval, no new top-level verbs, no ADR tree |
| **Human locks** | Protected statuses never auto-overwritten |
| **Structural integrity** | AccuracyGate/validators own placeholders/structure |
| **Docs sync** | L1 / cli / config / glossary updated when contracts change |
| **Tests** | Behavior is locked by tests at the right layer |
| **Terminology** | Glossary-aligned; Critique ≠ Review |

Hard stops: [engineering-invariants.md](engineering-invariants.md), [AGENTS.md](../../AGENTS.md).

## Prefer requesting changes when

- Business orchestration lives in Typer handlers
- New top-level CLI command groups appear without an explicit maintainer Decision
- Deferred appendix items are documented as shipped Behavior
- Docs claim Behavior the code does not implement
- Human-protected statuses can be overwritten by MT/sync
- Critique JSON is treated as the structural accuracy authority
- Large empirical artifacts or secrets are in the PR
- Breaking surface changes are silent (no PR callout, no reference update)

## Prefer approving when

- Small, focused diff with clear why
- Tests prove the fix/feature
- Same-PR Derived docs when needed
- Invariants preserved
- Complexity is justified

## Review focus by change type

| Change | Extra attention |
|--------|-----------------|
| Parser / masking | Placeholder integrity; parser rule |
| TM / sync | Lifecycle; human protection; JSONL SSOT |
| Validation / AccuracyGate | Deterministic gate vs LLM critique roles |
| LLM / prompts | Factory pattern; Jinja assets; no YAML prompt blobs |
| CLI / config | Reference docs + agent mirrors |
| Docs-only | Diátaxis home; no invented CLI; glossary |

## Tone and process

- Be specific: cite file/layer and the invariant at risk.
- Prefer link-to-canonical (L1, invariants) over rewriting encyclopedias in review comments.
- AI-assisted PRs: hold the **human author** accountable — [ai-contribution-guidelines.md](ai-contribution-guidelines.md).

## Related

- [contribution-workflow.md](contribution-workflow.md)
- [architectural-guidelines.md](architectural-guidelines.md)
- [contributor-guide.md](contributor-guide.md)
