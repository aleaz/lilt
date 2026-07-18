---
id: arch-00
title: Canonical Domain Language
status: accepted
---

# Canonical Domain Language

This document is the **single source of truth** for LILT vocabulary. Architecture
guides, README, and PRD should link here instead of redefining terms.

When code and prose disagree, **code wins**; update documentation to match.

## How to read each entry

| Field | Meaning |
|-------|---------|
| **Canonical name** | Official term for the project |
| **Definition** | What the concept is |
| **Responsibility** | What it does in the system |
| **Relationships** | How it connects to other concepts |
| **Code example** | Primary module or symbol |
| **Alternative names** | Synonyms in code or docs today |
| **Recommendation** | Keep, Rename, Merge, or Deprecate (alias only) |

---

## Core domain

### Segment

| | |
|---|---|
| **Definition** | Atomic translatable unit with stable ID derived from normalized source hash |
| **Responsibility** | Holds masked `source_text`, active `translation`, lifecycle `status`, artifacts, and placeholder map |
| **Relationships** | Persisted in a Namespace within Translation Memory; produced from a Parse Block during Sync |
| **Code example** | `StoredSegment` in `models/segment.py` |
| **Alternative names** | "block" (informal) |
| **Recommendation** | **Keep** |

### Parse Block

| | |
|---|---|
| **Definition** | Segment extracted at parse time, before persistence |
| **Responsibility** | Carries masked text, raw LaTeX span, and translatability flag |
| **Relationships** | Output of `LatexParser`; input to Sync |
| **Code example** | `SegmentBlock` in `parser/ast_parser.py` |
| **Alternative names** | "segment block", "blocks" in logs |
| **Recommendation** | **Keep** `SegmentBlock`; use "parse block" in prose |

### Translation Memory (TM)

| | |
|---|---|
| **Definition** | Append-only JSONL store of segment records under `.lilt/tm/` |
| **Responsibility** | Single source of truth for localization state |
| **Relationships** | Partitioned by Namespace; written via Sync and Translate; read by Build |
| **Code example** | `TMRepository` in `tm/repository.py` |
| **Alternative names** | TM, JSONL store |
| **Recommendation** | **Keep** |

### Namespace

| | |
|---|---|
| **Definition** | TM partition keyed by encoded relative path of source `.tex` (root: basename; nested: `dir__file`) |
| **Responsibility** | Isolates segments per document file |
| **Relationships** | One namespace → one JSONL file (e.g. `chapter1` → `chapter1.jsonl`) |
| **Code example** | `tm/repository.py`, `PipelineService.sync_file()` |
| **Alternative names** | file stem, document key |
| **Recommendation** | **Keep** |

### Segment Status

| | |
|---|---|
| **Definition** | Lifecycle state of a segment (10 values) |
| **Responsibility** | Gates translation eligibility, human review, and build selection |
| **Relationships** | Set by reflection pipeline, human edit, sync identity, or manual `tm set-status` |
| **Code example** | `SegmentStatus` in `models/segment.py` |
| **Alternative names** | `untranslated`/`pending` → `generated`; `machine_done` → `refined` (CLI aliases) |
| **Recommendation** | **Keep** |

### Reflection

| | |
|---|---|
| **Definition** | Quality loop: Draft → Critique → Refine on a segment |
| **Responsibility** | Improves translation via structured LLM passes and MQM critique |
| **Relationships** | Executed per Translation Stage; orchestrated by Execution Mode strategies |
| **Code example** | `llm/reflection_pass.py`, `ReflectionMeta` |
| **Alternative names** | "workflow pipeline", "multi-agent" (deprecated in docs) |
| **Recommendation** | **Keep**; **Deprecate** "multi-agent" as project framing |

### Translation Stage

| | |
|---|---|
| **Definition** | One step in reflection: `draft`, `critique`, or `refine` |
| **Responsibility** | Names LLM operation, artifact slot, and telemetry bucket |
| **Relationships** | Subset of reflection; distinct from Execution Mode and TM compaction stage |
| **Code example** | `TranslationStage` in `models/translation_stage.py` |
| **Alternative names** | "phase", "pass" (informal) |
| **Recommendation** | **Keep**; reserve "stage" for this enum in new code and docs |

### Execution Mode

| | |
|---|---|
| **Definition** | How reflection is scheduled across segments: breadth-first or depth-first |
| **Responsibility** | Selects `WorkflowReflectionStrategy` vs `SequentialReflectionStrategy` |
| **Relationships** | Configured via `translation_mode` in `lilt.yaml` |
| **Code example** | `TranslationMode` in `models/translation_mode.py` |
| **Alternative names** | `workflow`, `sequential` |
| **Recommendation** | **Keep** |

### Reflection Pass

| | |
|---|---|
| **Definition** | One full D→C→R execution for a single segment |
| **Responsibility** | Pure orchestration of draft, critique, refine without TM persistence |
| **Relationships** | Used by sequential path and `translate_segment_iter` |
| **Code example** | `run_reflection_pass()` in `llm/reflection_pass.py` |
| **Alternative names** | "full pass" (informal) |
| **Recommendation** | **Keep** |

### Stage Artifact

| | |
|---|---|
| **Definition** | Persisted intermediate output for one translation stage |
| **Responsibility** | Stores `content`, LLM `model` id, and `timestamp` for draft/critique/refined slots |
| **Relationships** | Embedded in Segment record; used by context resolver priority chain |
| **Code example** | `StageArtifact` in `models/segment.py` |
| **Alternative names** | "reflection artifact" (informal) |
| **Recommendation** | **Keep** |

### Critique vs Review

| | |
|---|---|
| **Definition** | **Critique** = LLM MQM evaluation of a draft; **Review** = human editorial queue |
| **Responsibility** | Critique feeds refine; review is CLI-driven human gate |
| **Relationships** | Critique → `CritiqueResult`; Review → `ReviewPolicy`, `pipeline review` |
| **Code example** | `models/critique.py`, `core/review_policy.py` |
| **Alternative names** | "Review phases" for critique/refine (incorrect) |
| **Recommendation** | **Keep** both terms; never use "review" for LLM critique |

### Conflict vs Error

| | |
|---|---|
| **Definition** | **Conflict** = validation or source-change failure; **Error** = infrastructure/API failure |
| **Responsibility** | Drives recovery paths and re-translation eligibility |
| **Relationships** | `mark_validation_conflict` vs `mark_infrastructure_error` on segment |
| **Code example** | `SegmentStatus.CONFLICT`, `SegmentStatus.ERROR`, `ErrorMeta` |
| **Alternative names** | generic "failure" |
| **Recommendation** | **Keep** (exemplary separation) |

### Placeholder

| | |
|---|---|
| **Definition** | Mask token substituting opaque LaTeX during LLM inference |
| **Responsibility** | Preserves structure; restored at build via persisted map |
| **Relationships** | Created by `PlaceholderEngine`; validated by `PlaceholderValidator` |
| **Code example** | `StoredSegment.placeholders`, `parser/placeholder_engine.py` |
| **Alternative names** | mask token, pseudo-XML tag |
| **Recommendation** | **Keep** |

### Translation Checkpoint

| | |
|---|---|
| **Definition** | Crash-safe incremental persistence boundary during translate |
| **Responsibility** | Appends segment updates; compacts TM at stage end |
| **Relationships** | Used by both execution mode strategies |
| **Code example** | `TranslationCheckpoint` in `tm/checkpoint.py` |
| **Alternative names** | checkpoint, stage finalize |
| **Recommendation** | **Keep** |

---

## Application and orchestration

### Translation Pipeline

| | |
|---|---|
| **Definition** | End-to-end CLI path: Sync → Translate → Build |
| **Responsibility** | User-facing workflow for localization |
| **Relationships** | Orchestrated by `PipelineService`; distinct from Translation Engine |
| **Code example** | `lilt pipeline` commands, `services/pipeline_service.py` |
| **Alternative names** | "pipeline" alone (ambiguous) |
| **Recommendation** | **Keep**; qualify as "translation pipeline" vs "translator pipeline" |

### Translation Engine

| | |
|---|---|
| **Definition** | Core subsystem that runs reflection over TM segments |
| **Responsibility** | Selects strategy, resolves context, validates, persists via checkpoint |
| **Relationships** | `create_reflection_strategy` selects a `ReflectionStrategy` implementation |
| **Code example** | `core/translation/` |
| **Alternative names** | "translate module" |
| **Recommendation** | **Keep** as architectural name; compose via `create_reflection_strategy` |

### Pipeline Service

| | |
|---|---|
| **Definition** | Application-layer facade for sync, translate, build, review, edit |
| **Responsibility** | Workspace sandboxing, config loading, CLI delegation |
| **Relationships** | Selects reflection strategy via `create_reflection_strategy`; sync, build |
| **Code example** | `services/pipeline_service.py` |
| **Alternative names** | "pipeline" |
| **Recommendation** | **Keep** |

---

## Resolvers (four distinct roles)

Do not merge these types; the `*Resolver` suffix is overloaded but each role is legitimate.

| Resolver | Scope | Code |
|----------|-------|------|
| **ContextResolver** | Neighbor segment text for RAG (`translation` > `refined` > `draft`) | `core/translation/context_resolver.py` |
| **StatusResolver** | CLI status strings and aliases → `SegmentStatus` | `models/status_resolver.py` |
| **IdentityResolver** | Source hash similarity carry-forward on sync | `tm/identity_resolver.py` |
| **DependencyResolver** | `\input` / `\usepackage` graph for multi-file sync | `parser/dependency_resolver.py` |

**Recommendation:** **Keep** all four; always qualify which resolver in prose.

---

## Overloaded terms (disambiguation)

### Stage

| Sense | Meaning | Example |
|-------|---------|---------|
| **Translation stage** | `draft` / `critique` / `refine` | `TranslationStage`, `--stage` flag |
| **Compaction stage** | TM finalize after a batch | `TranslationCheckpoint.finalize_stage()` |
| **Telemetry stage** | Bucket in inference records | May include `"sequential"` (execution path, not a translation stage) |

### Model

| Sense | Meaning | Example |
|-------|---------|---------|
| **Domain model** | Pydantic schema | `StoredSegment`, `SegmentPolicy`, `SyncResult` |
| **LLM model** | Provider model identifier | `stage_model_name()`, `StageArtifact.model` |
| **Execution mode** | Not a "model" | Avoid calling `sequential` a model |

### Block

| Sense | Meaning | Example |
|-------|---------|---------|
| **Parse block** | `SegmentBlock` from parser | Sync input |
| **Compressed placeholders** | `<block id="N"/>` token | `compress_blocks()` output |
| **Informal** | Any segment | Avoid in new docs |

---

## Infrastructure

### LLM Provider

| | |
|---|---|
| **Definition** | Port for draft/critique/refine inference |
| **Responsibility** | Abstracts API calls, retries, model resolution |
| **Relationships** | Created by `ProviderFactory`; may delegate via `RouterLLMProvider` |
| **Code example** | `LLMProvider` protocol, `BaseLLMProvider` |
| **Alternative names** | adapter, backend |
| **Recommendation** | **Keep** |

### Provider Factory

| | |
|---|---|
| **Definition** | Builds provider graph from `lilt.yaml` |
| **Responsibility** | Single provider or `RouterLLMProvider` when `llm.stages` present |
| **Code example** | `llm/factory.py` |
| **Recommendation** | **Keep** |

### Router

| | |
|---|---|
| **Definition** | Delegates each translation stage to a distinct provider instance |
| **Responsibility** | Enables hybrid local/cloud topologies |
| **Code example** | `RouterLLMProvider` |
| **Alternative names** | multi-provider, hybrid router |
| **Recommendation** | **Keep** |

### Policy vs Strategy

| Type | Role | Examples |
|------|------|----------|
| **Policy** | Business rules, eligibility | `SegmentPolicy`, `ReviewPolicy`, `SourceChangePolicy` |
| **Strategy** | Orchestration algorithm | `WorkflowReflectionStrategy`, `SequentialReflectionStrategy` |

**Recommendation:** **Keep** suffix conventions; do not introduce new `*Handler` types.

### Workspace Context

| | |
|---|---|
| **Definition** | Composition root for workspace-scoped dependencies |
| **Responsibility** | Injects TM repository, telemetry, config paths |
| **Relationships** | Distinct from translation **context** (neighbor segments) |
| **Code example** | `services/workspace_context.py` |
| **Alternative names** | workspace, project root |
| **Recommendation** | **Keep** |

### Reflection Cost Estimation

| | |
|---|---|
| **Definition** | Pre-flight token budget for a translation run |
| **Responsibility** | Estimates inference cost before LLM calls |
| **Relationships** | Used by `tm status`; depends on execution mode multiplier |
| **Code example** | `telemetry/reflection_cost.py` |
| **Alternative names** | (none in code) |
| **Recommendation** | **Keep** |

---

## Status filter (CLI)

| | |
|---|---|
| **Definition** | Optional filter limiting which segments are translated |
| **Responsibility** | Maps `--status` / `-s` to `SegmentStatus` via `StatusResolver` |
| **Code example** | CLI flag `--status`; internal parameter `status_filter` |
| **Alternative names** | (none) |
| **Recommendation** | **Keep** CLI flag `--status`; internal name is `status_filter` |

---

## Deprecated terminology (do not use in new docs)

| Deprecated | Use instead |
|------------|-------------|
| multi-agent / agentic (project framing) | reflection pipeline, D→C→R |
| monolithic (for sequential mode) | sequential execution mode |
| Gold / Silver context | backward-priority vs bidirectional context (see 04-translation-engine) |
| Review phases (for critique/refine) | translation stages or critique/refine |
| agential cost / `SegmentInDB` / `ArtifactMeta` / `use_workflow` | removed from code; use canonical terms in [00-glossary](00-glossary.md) |
