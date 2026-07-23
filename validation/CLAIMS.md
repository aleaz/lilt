# Validation claims registry (operational)

Slim registry for assets under `validation/`. This file is authoritative for
claim ID, slug, mode, primary asset path, and Evidence. Maintainer-only narrative
catalogs are out of tree and not required to operate or extend this registry.

IDs are permanent `CL-NNN`. Never renumber. Do not invent `VC-*` IDs.

| Claim | Slug | Mode | Primary asset | Evidence |
|-------|------|------|---------------|----------|
| CL-001 | smoke.article-sync-build | CV | `smoke/article-l1-smoke` | implemented |
| CL-002 | smoke.article-translate-build | RV | `smoke/article-l1-smoke` | implemented |
| CL-010 | structure.sectioning-preserved | both | `smoke/article-l1-smoke` | implemented |
| CL-011 | structure.env-pairing-preserved | CV | `smoke/article-l1-smoke` | implemented |
| CL-012 | structure.documentclass-survives | CV | `smoke/article-l1-smoke` | implemented |
| CL-020 | parser.lossless-roundtrip | CV | `smoke/article-l1-smoke` | implemented |
| CL-021 | parser.gaps-surfaced | CV | `packages/pkg-parser-edge` | implemented |
| CL-022 | parser.custom-macro-config | CV | `packages/pkg-parser-edge` | implemented |
| CL-030 | masking.placeholder-multiset | both | `smoke/article-l1-smoke` | implemented |
| CL-031 | masking.opaque-env-not-sent | both | `packages/pkg-tikz-pgfplots` | implemented |
| CL-032 | masking.restore-deterministic | both | `smoke/article-l1-smoke` | implemented |
| CL-033 | masking.protected-terms | RV | `document-types/article-scholarly-l2` | implemented |
| CL-034 | masking.arg-level-macros | both | `document-types/article-scholarly-l2` | implemented |
| CL-040 | xref.ref-masked | both | `smoke/article-l1-smoke` | implemented |
| CL-041 | xref.cleveref-masked | both | `document-types/article-scholarly-l2` | implemented |
| CL-042 | xref.label-not-translated | both | `smoke/article-l1-smoke` | implemented |
| CL-050 | bibliography.cite-masked | both | `document-types/article-scholarly-l2` | implemented |
| CL-051 | bibliography.biblatex-cite | both | `document-types/article-scholarly-l2` | implemented |
| CL-052 | bibliography.bib-file-untouched | CV | `document-types/article-scholarly-l2` | implemented |
| CL-053 | bibliography.cite-optional-args | RV | `document-types/article-scholarly-l2` | implemented |
| CL-060 | math.inline-masked | both | `smoke/article-l1-smoke` | implemented |
| CL-061 | math.display-masked | both | `document-types/article-scholarly-l2` | implemented |
| CL-062 | math.not-translated-as-prose | RV | `document-types/article-scholarly-l2` | implemented |
| CL-070 | tables.caption-translatable | RV | `document-types/article-scholarly-l2` | implemented |
| CL-071 | tables.alignment-tabs-preserved | both | `document-types/article-scholarly-l2` | implemented |
| CL-072 | tables.longtable-survives | both | `document-types/article-scholarly-l2` | implemented |
| CL-080 | figures.caption-translatable | RV | `document-types/article-scholarly-l2` | implemented |
| CL-081 | figures.path-stable | both | `document-types/article-scholarly-l2` | implemented |
| CL-082 | figures.subcaption | RV | `document-types/article-scholarly-l2` | implemented |
| CL-090 | tikz.picture-opaque | both | `packages/pkg-tikz-pgfplots` | implemented |
| CL-091 | tikz.pgfplots-opaque | both | `packages/pkg-tikz-pgfplots` | implemented |
| CL-092 | tikz.build-with-opaque | CV | `packages/pkg-tikz-pgfplots` | implemented |
| CL-100 | listings.body-opaque | both | `packages/pkg-listings` | implemented |
| CL-101 | minted.body-opaque | both | `packages/pkg-minted` | implemented |
| CL-102 | listings.caption-ok | RV | `packages/pkg-listings` | implemented |
| CL-110 | beamer.frame-structure | both | `document-types/beamer-frames` | implemented |
| CL-111 | beamer.overlay-safe | both | `document-types/beamer-frames` | implemented |
| CL-112 | beamer.translate-titles | RV | `document-types/beamer-frames` | implemented |
| CL-120 | multifile.input-tree-sync | CV | `document-types/multifile-input` | implemented |
| CL-121 | multifile.subfiles-root | CV | `document-types/multifile-subfiles` | implemented |
| CL-122 | multifile.partial-sync-message | CV | `workflow/sync-partial-fail` | implemented |
| CL-123 | multifile.namespace-encoding | CV | `document-types/multifile-input` | implemented |
| CL-130 | workspace.init-required | CV | `workflow/workspace-cli` | implemented |
| CL-131 | workspace.work-dir-flag | CV | `workflow/workspace-cli` | implemented |
| CL-140 | tm.namespace-per-file | CV | `smoke/article-l1-smoke` | implemented |
| CL-141 | tm.human-status-protected | both | `workflow/tm-human-gates` | implemented |
| CL-142 | tm.source-change-conflict | both | `workflow/tm-human-gates` | implemented |
| CL-143 | tm.status-counts-honest | CV | `workflow/tm-human-gates` | implemented |
| CL-150 | recovery.translate-interrupt-resume | RV | `recovery/session-lease` | implemented |
| CL-151 | recovery.stale-lease-reclaim | CV | `recovery/session-lease` | implemented |
| CL-152 | recovery.busy-identity | CV | `recovery/session-lease` | implemented |
| CL-160 | build.fail-closed-default | both | `smoke/article-l1-smoke` | implemented |
| CL-161 | build.allow-partial | both | `document-types/article-scholarly-l2` | implemented |
| CL-162 | build.uses-persisted-placeholders | both | `smoke/article-l1-smoke` | implemented |
| CL-170 | cli.sync-translate-build-sequence | RV | `smoke/article-l1-smoke` | implemented |
| CL-171 | cli.status-empty-ns-guidance | CV | `workflow/workspace-cli` | implemented |
| CL-180 | review.queue-respects-config | CV | `human-review/human-review-queue` | implemented |
| CL-181 | review.import-validates | both | `human-review/human-review-queue` | implemented |
| CL-190 | localization.babel-preamble-stable | CV | `smoke/article-l1-smoke` | implemented |
| CL-191 | localization.polyglossia-xe-lua | CV | `document-types/polyglossia-xe` | implemented |
| CL-192 | localization.csquotes | RV | `document-types/article-scholarly-l2` | implemented |
| CL-200 | publisher.class-preamble-survives | CV | `document-types/publisher-class` | implemented |
| CL-201 | engine.xelatex-declared | CV | `document-types/polyglossia-xe` | implemented |
| CL-210 | stem.siunitx-not-mangled | RV | `document-types/article-scholarly-l2` | implemented |

**Evidence column:** `implemented` = primary asset directory exists and documents the claim.  
Operator pass/fail for a release still requires executing the asset README (coverage state may remain `pending` until a recorded run).

When adding an asset: set its claims to `implemented` and keep the primary path aligned with the asset catalog.
