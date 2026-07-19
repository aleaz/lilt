# Concepts

User-facing product concepts for LILT. Runtime detail lives under
[architecture/](architecture/README.md).

## Purpose

LILT treats LaTeX translation as a software engineering problem. Instead of sending raw `.tex` to an LLM, it:

1. Parses the document AST and splits it into stable **segments** with deterministic IDs.
2. Masks equations, macros, references, and verbatim blocks into placeholder tags.
3. Translates only linguistic prose through a multi-stage LLM pipeline.
4. Validates structural integrity before persisting translations.
5. Reconstructs the document by unmasking placeholders from persisted maps.

## Philosophy

| Principle | Meaning in LILT |
|-----------|-----------------|
| Integrity over linguistics | Placeholder and syntax validators run before a translation is accepted. |
| Human priority | Segments in `reviewed`, `approved`, or `locked` status are protected from automatic overwrite unless explicitly forced. |
| TM as source of truth | All segment state lives in append-only JSONL under `.lilt/tm/`. |
| Local-first LLM | Default configuration targets a local OpenAI-compatible endpoint; cloud models are optional per stage. |
| Reproducibility | Stable segment IDs, persisted placeholder maps, and checkpointed translation runs. |

## Scope

- **In scope:** Academic papers, books, technical manuals, and multi-file LaTeX projects with `\input{}`, custom macros, math, citations, and cross-references.
- **Out of scope:** OCR, diagram translation, WYSIWYG editing, remote Git automation (deferred).

## Maturity

LILT is a **public beta** on the **0.1.x** package line (`0.1.0b1`). Core pipeline (sync, translate, build, review, TM management, telemetry) is implemented and tested. Treat 0.x as SemVer-unstable: CLI and config may still change. Phase 2 features (plugins, glossary validators, multi-language layout) are documented as deferred in [appendix-deferred](architecture/appendix-deferred.md).

## Audience

| Persona | Use case |
|---------|----------|
| **Technical author** | Keep translations in sync when the source `.tex` changes. |
| **Technical translator** | Review machine output segment by segment with placeholder safety. |
| **Translation maintainer** | Resolve `conflict` segments after upstream edits; export/import for external review. |
| **Contributor** | Extend parsers, validators, or LLM providers via the service layer. |

## Feature map

| Area | One-liner | Deep dive |
|------|-----------|-----------|
| Parser / masking | AST parse with gap-preserving roundtrip; opaque / transparent / deep-traversal | [03-parser-masking](architecture/03-parser-masking.md) |
| Placeholders | Canonical tags persisted in TM; multiset-exact validation | [03-parser-masking](architecture/03-parser-masking.md) |
| Translation Memory | Append-only JSONL; 10 statuses; human protection | [02-persistence](architecture/02-persistence.md) |
| Reflection pipeline | Draft → Critique → Refine (workflow or sequential) | [04-translation-engine](architecture/04-translation-engine.md) |
| LLM routing | OpenAI-compatible providers; per-stage models | [05-llm-layer](architecture/05-llm-layer.md) |
| Build | Reconstruct `.tex` from TM + persisted placeholder maps | [06-build-output](architecture/06-build-output.md) |
| CLI / services | Typer CLI → services → core | [07-cli-application](architecture/07-cli-application.md), [CLI reference](reference/cli.md) |
| Telemetry | SQLite inference records and cost estimates | [08-observability](architecture/08-observability.md) |

## Architecture (user view)

Pipeline and domain model: [Architecture README](architecture/README.md).
Operator CLI flow (init → sync → translate → review → build) is documented there.

Masking idea: the LLM sees prose with tags such as `<math id="1"/>` / `<macro id="2"/>`, never raw structural LaTeX. Details: [03-parser-masking](architecture/03-parser-masking.md).

## Human vs machine stages

- **Critique** = LLM MQM stage; **Review** = human editorial queue — [00-glossary](architecture/00-glossary.md).
- Human review workflows: [Human review](guides/human-review.md).
- Segment lifecycle state machine: [02-persistence](architecture/02-persistence.md).

## See also

- [Getting started](getting-started.md)
- [Workflows](guides/workflows.md)
- [Documentation hub](README.md)
