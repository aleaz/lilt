# Engineering philosophy

How to **think** when changing LILT. Not an API catalog — for commands see [CLI reference](../reference/cli.md); for Behavior see [Architecture](../architecture/README.md).

Index: [Developer Guide](README.md). Hard rules: [engineering-invariants.md](engineering-invariants.md). Named principles: [engineering-principles.md](engineering-principles.md).

## Sources of this philosophy

Inferred from the running system and existing SSOT docs — not invented:

- Layering and hard stops in [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc)
- Product boundary on [architecture README](../architecture/README.md)
- L1 **Invariants** / **Decisions** sections
- [AGENTS.md](../../AGENTS.md) and [conventions](conventions.md)

## Core engineering philosophy

1. **Implementation is the source of truth.** When docs and code disagree, update the docs (unless you are fixing a tracked code bug).
2. **Integrity over blind fluency.** Placeholders, syntax checks, and human locks beat “prettier” prose that drops structure.
3. **Compile-minded localization.** The engine produces `.tex`; users compile PDF. Do not pretend PDF is a first-class CLI product surface.
4. **Continuous memory.** The JSONL Translation Memory under `.lilt/tm/` is the segment SSOT — not chat history and not a full document store.
5. **Explicit product boundary.** This repo ships the localization engine (`src/lilt/`, tests, L1). Corpus/eval harnesses stay outside.

## Architectural philosophy

- **Thin CLI, fat services/core.** Typer handlers adapt; orchestration lives in `services/`; domain work in `core/` / `tm/` / `parser/` / `llm/` / `validation/`.
- **One composition root.** `WorkspaceContext` wires paths, TM, and telemetry — do not invent parallel global state.
- **Provider-agnostic core.** Domain code talks through LLM abstractions; the shipped factory registers the OpenAI-compatible `openai` adapter. Do not bolt new vendor SDKs into core without design + docs.
- **Prompts as assets.** Jinja templates (package or `llm.prompt_dir`), not prompt blobs in YAML.
- **Reflection as stages, not agents.** Draft → Critique → Refine (workflow or sequential) are pipeline roles with persisted artifacts — not a multi-agent framework.
- **Decisions live in L1.** No `docs/adrs/` tree. Tradeoffs go in L1 **Decisions**; not-yet-shipped work in [appendix-deferred](../architecture/appendix-deferred.md).

## Why the layers exist

| Separation | Why |
|------------|-----|
| CLI vs services | Testable orchestration; UI/adapters stay replaceable |
| Services vs core | Application use-cases vs domain algorithms |
| Parser / TM / LLM | Independent evolution of structure, memory, and models |
| Validation vs critique | Deterministic AccuracyGate owns structure; LLM critique owns editorial quality |

## Dependency philosophy

Dependencies flow **inward** only:

```text
cli → services → core | parser | tm | llm | validation → models | utils
```

Do not import services from core, or core from CLI.

## Error-handling philosophy

- **Infrastructure vs validation:** `error` vs `conflict` statuses (see glossary) — different recovery paths.
- **Fail closed when incomplete output would lie:** default `pipeline build` refuses non-buildable segments unless `--allow-partial`.
- **Validate before persist:** structural checks gate TM commits for MT and human edits.
- Domain exceptions in `lilt.exceptions` map to CLI messages — keep handlers thin ([07-cli-application](../architecture/07-cli-application.md)).

## Testing philosophy

- Engine correctness lives in `tests/` (unit, integration, CLI). `make ci` is the gate.
- Large empirical campaigns stay **outside** the repo ([CONTRIBUTING](../../CONTRIBUTING.md)).
- Prefer tests that lock invariants (placeholders, statuses, fail-closed build) over golden “pretty translation” claims.

## Documentation philosophy

- **Diátaxis:** tutorial / how-to / reference / explanation have separate homes ([docs hub](../README.md)).
- **Derived CLI surface:** Typer → `docs/reference/cli.md` → agent mirrors — same PR.
- **Glossary owns terms.** Critique ≠ Review; refined ≠ approved.
- **Honest maturity:** beta / Unreleased until an intentional tag — no release theater.

## CLI philosophy

- Minimal public verb set: `project`, `pipeline`, `tm`, `telemetry` only.
- `compile_pdf` remains service-only; users compile externally.
- Flags and help text must match Typer — reference is not a second invention site.

## Configuration philosophy

- Explicit `lilt.yaml` + env / `${VAR}` — typed by `LiltConfig`.
- Cost/thinking via `cost_profile` and `stage_policies`; capacity checked with `tm budget`.
- Prefer documented keys over hidden defaults that surprise operators.

## Validation philosophy

- Structural integrity is **machine-owned** (validators + AccuracyGate).
- Editorial quality is **LLM-assisted** (critique) then optionally **human** (review).
- Do not let free-text critique JSON decide placeholder correctness.

## Naming philosophy

- Import/CLI: `lilt`. Distribution: `latex-lilt`. Never teach `pip install lilt` for this project.
- Status and stage names follow the [glossary](../architecture/00-glossary.md).

## Refactoring philosophy

- Prefer extending services/core over growing CLI.
- Same-PR docs for contract/surface changes.
- On ship: shrink appendix-deferred; expand L1 Behavior; update PRD Shipped if user-visible.

## Performance philosophy

- Local-first defaults; measure with telemetry and runbooks — do not invent SLOs in philosophy docs.
- Token/context packing is explicit (`model_context_limit`, StagePolicy) — see L1-05 and performance runbook.

## Backward compatibility & release philosophy

- Public beta: CLI/config **may** change until an intentional release.
- CHANGELOG stays Unreleased until the maintainer cuts a tag deliberately.
- Do not mark deferred appendix items as shipped.

## Related

- [engineering-principles.md](engineering-principles.md)
- [engineering-invariants.md](engineering-invariants.md)
- [architectural-guidelines.md](architectural-guidelines.md)
- [ai-engineering-guide.md](ai-engineering-guide.md)
