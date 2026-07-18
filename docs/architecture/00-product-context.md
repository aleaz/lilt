# LILT: Product Requirements Document (PRD)

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement and Vision](#2-problem-statement-and-vision)
3. [Product Goals](#3-product-goals)
4. [Scope](#4-scope)
5. [Product Principles](#5-product-principles)
6. [Users and Use Cases](#6-users-and-use-cases)
7. [Core Localization Model](#7-core-localization-model)
8. [Repository Architecture and Git Flow](#8-repository-architecture-and-git-flow)
9. [Parsing and Protection Strategy](#9-parsing-and-protection-strategy)
10. [System Requirements](#10-system-requirements)
11. [Roadmap and MVP Definition](#11-roadmap-and-mvp-definition)

---

## 1. Executive Summary

**LILT** is a continuous localization platform designed to translate, maintain, and synchronize complex LaTeX projects using Large Language Models (LLMs), preserving the structural integrity of the original project and enabling collaboration through the Git ecosystem.

Unlike generic tools, this platform manages the full lifecycle of a technical document (books, theses, manuals). It guarantees that the translated document compiles without errors, that internal references and mathematics remain intact, and that human corrections prevail, minimizing unnecessary re-translations when upstream updates occur.

---

## 2. Problem Statement and Vision

### The Problem

Translating LaTeX projects using generic tools or copy-pasting directly into LLMs usually fails due to:

- **Structural corruption**: Accidental alteration of key commands (`\label`, `\ref`, `\cite`), breaking compilation.
- **Code/math corruption**: `lstlisting`, `minted` blocks, or equations being "translated" and destroyed.
- **Terminological inconsistency**: Multiple ways of translating the same term throughout the book (e.g., "scheduler").
- **Synchronization impossibility**: When the original author updates a chapter, the history of the previous translation is lost, forcing costly rework.

### The Vision

To become an **open and LLM-provider-independent platform** for technical localization of structured documentation. It will allow books and manuals to evolve and synchronize across multiple languages without sacrificing quality or editorial control.

---

## 3. Product Goals

### Primary Goals

- **PG-001**: Translate complete projects preserving their structure and ensuring successful compilation (PG-002).
- **PG-003**: Maintain terminological consistency throughout the project.
- **PG-004**: Ensure all translations can be reviewed and corrected by humans.
- **PG-005/006**: Maintain incremental synchronization with *upstream* repositories, minimizing re-translations.
- **PG-007**: Operate independently of the LLM provider (local or remote models).
- **PG-009**: Facilitate collaboration and auditing via Git branches and Pull Requests.

### Non-Goals

- It does not seek to replace professional translators or generate new content/summaries.
- It is not a visual LaTeX editor and does not manage the remote repository.
- OCR and translation of diagrams within images are out of the initial scope.

---

## 4. Scope

**In Scope (MVP):**

- Standard structured projects (`book`, `report`, `article`) with native inclusion tree parsing (`\input`, `\include`, `\usepackage`).
- Automatic Discovery of Semantic Environment Aliases (e.g., mapping `\newcommand{\ben}{\begin{eqnarray}}`).
- Translation of chapters, sections, paragraphs, *captions*, *footnotes*, and accessibility attributes (`alt-text`).
- Support for mathematics, bibliographies, cross-references, and code blocks.
- Git integration via local control.
- Usage of LLM providers via **OpenAI-compatible APIs** (LM Studio, Ollama, OpenRouter, cloud endpoints). The factory registers the `openai` adapter name; other vendors work when exposed through a compatible HTTP API (see [LLM Layer](05-llm-layer.md)).

---

## 5. Product Principles

1. **Integrity over Linguistics**: A document that compiles is preferable to an excellent translation that breaks the structure.
2. **Human Priority**: Human corrections are not automatically overwritten by AI.
3. **Translation Memory (TM) as Single Source of Truth**: The TM retains the reconstruction and translation state.
4. **Reproducibility**: Every translation is reconstructible using repository data.
5. **Incremental Translation**: Mandatory reuse to save costs.
6. **Provider Agnostic**: Modular architecture for LLMs.
7. **Git Collaboration**: Git as the natural mechanism for distributed review.
8. **Extensibility**: Support for terminology rules and custom macros (via Plugins).

---

## 6. Users and Use Cases

**Personas:**

1. **Technical Translator**: Seeks to maintain consistency and reduce repetitive work.
2. **Document Author**: Wants to keep translations synchronized with their new editions.
3. **Translation Maintainer**: Reviews and resolves conflicts when updating from upstream.
4. **Open Source Community**: Contributes improvements via Pull Requests.

**Highlighted Use Cases:**

- Translate a complete book from scratch.
- Synchronize and update only the paragraphs affected by a new upstream commit.
- Approve and "lock" a translated segment to prevent automatic overwriting.
- Recover execution from a *checkpoint* after a network or compilation failure.

---

## 7. Core Localization Model

*Implementation detail: [Persistence](02-persistence.md). This section states product intent only.*

The conceptual architecture separates source content from translations and audits, supporting multiple languages concurrently without interference (each language has its own TM).

### The Canonical Unit (CTU)

The minimum operational Canonical Translation Unit (CTU) in version 1 is the **paragraph**, with immediate extensions for *captions*, *footnotes*, and prose environments (`enumerate`, `itemize`, `quote`, etc.). *Fuzzy matching* and sub-paragraph granularity are deferred.

### Segment Identity and Translation Memory

Segments receive stable identifiers and persist in chapter-scoped **JSONL** Translation Memory files. Human corrections and machine translations share one auditable history. See [Persistence](02-persistence.md) for identity resolution, schema, and I/O.

### Lifecycle and Conflicts

Ten segment statuses govern the lifecycle. Machine translation progresses through reflection states (`generated` → `drafted` → `critiqued` → `refined`). Human editorial gates (`reviewed` → `approved` → `locked`) require explicit CLI actions. Upstream source changes on protected segments surface as `conflict`; resolution is always manual. Full state machine and review-queue policy: [Persistence](02-persistence.md).

---

## 8. Repository Architecture and Git Flow

*Implementation detail: [Platform](01-platform.md). This section states product intent only.*

```text
username/book (Translation Fork)
├── source/      # Original content (upstream, optional in MVP)
├── .lilt/
│   ├── tm/      # Translation Memory (JSONL, one file per chapter)
│   └── lilt.yaml    # Project configuration
└── .cache/      # Regenerable files (not committed)
```

Note: Multi-language structure (`.lilt/<lang>/tm/`) and glossary (`glossary.yaml`) will be implemented in Phase 2.

When `sync` is executed, the tool parses the specified LaTeX file, calculates new and modified segments, and updates the TM. The user can commit the TM changes and open a Pull Request for human review before running the LLM translations.

---

## 9. Parsing and Protection Strategy

*Implementation detail: [Parser and Masking](03-parser-masking.md). This section states product intent only.*

### Parsing and Syntax Tree (AST)

LaTeX is parsed structurally (`pylatexenc` AST), not with regex-only extraction, so hierarchy and context are preserved.

### Node Classification

Nodes are classified so structural content is masked or traversed deterministically: **opaque** (never sent to the LLM), **transparent** (wrapper with translatable children), and **deep-traversal environments** (recursive descent with inline protection). Taxonomy and placeholder prefixes: [Parser and Masking](03-parser-masking.md).

### Placeholder Architecture and Lexical Masking

Opaque nodes and protected terminology are extracted before the model sees text; translations must return the exact placeholder set or are marked `conflict`. See [Parser and Masking](03-parser-masking.md) and [Translation Engine](04-translation-engine.md).

---

## 10. System Requirements

### Functional and Editorial (Critical Selection)

- **Dependency Graph Parsing**: Automatic graph resolution of `\include`, `\input`, and `.sty` packages to propagate context (e.g., aliases) natively.
- **Semantic Alias Discovery**: Extensible tracking of custom shortcuts for opening and closing LaTeX environments.
- **Glossary and Rules**: Support for mandatory terminology and style rules.
- **Auditing**: Full traceability (who edited, what model generated it, when it was approved).
- **Recovery**: Solid *checkpointing*; stopping the process does not mean re-translating everything.

### Technological and Non-Functional

- **Base Language**: Python 3.13+.
- **Package Management**: `uv`.
- **Data Validation**: **Pydantic** for strict internal API contracts and schema models.
- **CLI**: Implemented with **Typer**. See [CLI and Application Layer](07-cli-application.md) for command groups.
- **Fast Validation**: Post-translation logical checks (see [Translation Engine](04-translation-engine.md)). MVP: `SegmentTranslationValidator` (placeholder + syntax). Phase 3 (deferred): `TerminologyValidator`, `StructureValidator`.
- **Model Interoperability**: Generic `LLMProvider` protocol ([LLM Layer](05-llm-layer.md)). Initial support for OpenAI-compatible APIs.
- **LaTeX Node Classification**: Formal taxonomy ([Parser and Masking](03-parser-masking.md)).

---

## 11. Roadmap and MVP Definition

### MVP (Phase 1)

- Advanced AST structural parsing with `pylatexenc` ([Parser and Masking](03-parser-masking.md)).
- Formal classification of LaTeX nodes: opaque, transparent, and translatable.
- **Native Lexical Masking**: Word-boundary protected terms before translation.
- **Recursive Segmentation and Masking**: Translatable segments within transparent environments.
- Support for custom macros via `.lilt/lilt.yaml` (`parser.custom_macros`).
- Content-hash segment identity and JSONL Translation Memory ([Persistence](02-persistence.md)).
- Placeholder engine for `\ref`, `\cite`, math, code, and opaque environments.
- **Deep Traversal**: Recursive parsing of `figure`, `table`, `tabular`, etc.
- Post-translation validation ([Translation Engine](04-translation-engine.md)).
- OpenAI-compatible LLM layer ([LLM Layer](05-llm-layer.md)).
- Modular CLI ([07-cli-application](07-cli-application.md)).
- Document reconstruction (`build`) ([Build and Output](06-build-output.md)).

### Phase 2

- Multi-language structure (`.lilt/<lang>/tm/`) and `glossary.yaml`.
- Full AST-node diffing for structural moves without text overlap.
- Plugin System ([appendix-deferred](appendix-deferred.md)).
- *Fuzzy Matching* and CLI Dashboards.

**Shipped (formerly Phase 2):**

- Sequence-based identity resolution during sync.
- Multi-model routing via `llm.stages` and per-stage model fields.
- Gap-preserving parser roundtrip ([Parser and Masking](03-parser-masking.md)).
- Reflection cost estimation in `lilt tm status` ([Observability](08-observability.md)).
- Unified segment validation via `SegmentTranslationValidator` and human edit path ([Translation Engine](04-translation-engine.md)).

### Phase 3

- `TerminologyValidator` and `StructureValidator` ([appendix-deferred](appendix-deferred.md)).
- Web Interface, reviewer roles management, and metrics.

### Phase 4

- Multi-format support (Markdown, AsciiDoc, DocBook).

---
*End of PRD v1.0. Architectural decisions and implementation detail: [docs/architecture/README.md](README.md).*
