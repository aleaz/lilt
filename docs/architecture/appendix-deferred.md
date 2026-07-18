# Deferred Features and Roadmap

This appendix collects architectural intentions **not yet implemented** in the
current codebase. Items here are design targets, not current behavior.

For implemented behavior, see the L1 guides in this directory. When a feature
ships, it is removed from this appendix and documented in the relevant L1 guide
and PRD "Shipped" section.

## Plugin system (deferred)

**Status:** NOT IMPLEMENTED

Hook-based plugins in `.lilt/plugins/`:

- `pre_parse`, `on_node_visit`, `pre_translate`, `post_translate`, `on_validate`

**MVP substitute:** `parser.custom_macros` and YAML-driven classification
(see [03-parser-masking](03-parser-masking.md)).

**Rejected for MVP:** Arbitrary code execution surface and security review burden.

## Git automation

**Status:** NOT IMPLEMENTED

Planned features:

- Auto-branch on sync
- Commit-on-sync hooks
- `source/` upstream tracking directory

**Current behavior:** User-managed Git; JSONL + stable IDs are Git-friendly by design
(see [01-platform](01-platform.md)).

## Validators Phase 2

**Status:** NOT IMPLEMENTED

- `TerminologyValidator` — glossary term preservation
- `StructureValidator` — section/chapter wrapper integrity

MVP uses `PlaceholderValidator`, `SyntaxValidator`, `BuildValidator`, and
`SegmentTranslationValidator` (orchestrates placeholder + syntax for MT and human edits).

## Multi-language TM layout

**Status:** NOT IMPLEMENTED

Planned: `.lilt/<lang>/` per target language. Single TM layout today.

## AST-node identity diffing

**Status:** NOT IMPLEMENTED

Beyond `SequenceMatcher` text alignment (see [02-persistence](02-persistence.md)):
structural moves without text overlap.

## Audit log on segments

**Status:** NOT IMPLEMENTED

Full provenance (editor identity, per-edit timestamps) deferred from TM schema.

## Transactional TM read-modify-write

**Status:** NOT IMPLEMENTED

Full atomic load-mutate-save across all repository callers. Mitigated in 1.0 by
the single-writer session lock per namespace (see [02-persistence](02-persistence.md)).

## Related PRD phases

See [Product Context](00-product-context.md) Phase 2/3 for product-level roadmap alignment.
