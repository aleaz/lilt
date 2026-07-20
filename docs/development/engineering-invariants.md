# Engineering invariants

Hard rules that **must not be broken** without an explicit L1 Decision change and same-PR docs. Softer guidance lives in [engineering-philosophy.md](engineering-philosophy.md) and [engineering-principles.md](engineering-principles.md).

Index: [Developer Guide](README.md). Agent hard stops also in [AGENTS.md](../../AGENTS.md).

## Architectural invariants

| ID | Invariant | Evidence |
|----|-----------|----------|
| A1 | No business orchestration in CLI handlers — adapt I/O only | Architecture rule; L1-07 |
| A2 | Dependency direction: `cli → services → core|parser|tm|llm|validation` | [project-layout](project-layout.md) |
| A3 | One composition root: `WorkspaceContext` for shared workspace deps | `services/workspace_context.py` |
| A4 | Core stays provider-agnostic; do not embed new vendor SDKs in domain code | `llm/` factory pattern |
| A5 | Prompts live as Jinja (package / `prompt_dir`), not YAML blobs | L1-05; architecture rule |

## Domain / TM invariants

| ID | Invariant | Evidence |
|----|-----------|----------|
| D1 | Human statuses (`reviewed` / `approved` / `locked`) are never auto-overwritten by MT or sync | L1-02; architecture rule |
| D2 | JSONL TM under `.lilt/tm/` is append-oriented segment SSOT | L1-02 |
| D3 | Structural validation gates TM commits (MT and human edit paths) | validators; L1-08 |
| D4 | AccuracyGate owns structural accuracy vs draft; critique does not override it via free-text JSON | L1-04; `validation/accuracy_gate.py` |
| D5 | Placeholder / structure contract must hold for machine translations | Architecture rule; validators |

## CLI / product surface invariants

| ID | Invariant | Evidence |
|----|-----------|----------|
| C1 | Public CLI groups only: `project`, `pipeline`, `tm`, `telemetry` | Typer; AGENTS |
| C2 | Do not invent top-level verbs (`evaluate`, `corpus`, …) in this repo | AGENTS; product boundary |
| C3 | Do not restore `docs/adrs/` or treat appendix-deferred as shipped | AGENTS; architecture README |
| C4 | Do not add corpus / eval harness trees as product code | Architecture README product boundary |
| C5 | Default `pipeline build` fails closed; incomplete output needs `--allow-partial` | L1-06; cli.md |

## Documentation invariants

| ID | Invariant | Evidence |
|----|-----------|----------|
| Doc1 | Typer / config / contract changes update `docs/reference/` (+ agent mirrors) in the **same PR** | Architecture rule; [conventions](conventions.md) |
| Doc2 | Glossary is SSOT for terms — Critique ≠ Review; refined ≠ approved | [00-glossary](../architecture/00-glossary.md) |
| Doc3 | Decisions go in L1 Decisions / Known gaps / appendix — not a parallel ADR tree | Architecture README |
| Doc4 | Deferred features stay in [appendix-deferred](../architecture/appendix-deferred.md) until shipped | AGENTS |

## Testing / CI invariants

| ID | Invariant | Evidence |
|----|-----------|----------|
| T1 | Engine regressions are caught by `tests/` + `make ci` | [testing](testing.md) |
| T2 | Large empirical campaigns stay outside this repository | CONTRIBUTING; product boundary |

## What is *not* an invariant (do not over-claim)

- Bit-identical LLM outputs across runs
- Forever-stable public CLI before intentional release
- Plugin or corpus features listed only in appendix

## Breaking an invariant

1. Propose the change in L1 **Decisions** (or Known gaps).
2. Implement with tests.
3. Sync Derived docs (cli/config/architecture/agent mirrors) same PR.
4. If user-visible: update PRD Shipped / appendix as appropriate.

---

*Related: [architectural-guidelines.md](architectural-guidelines.md).*
