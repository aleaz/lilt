# AI domain language guide

How AI coding agents should use LILT’s ubiquitous language. Complements [AGENTS.md](../../AGENTS.md), [ai-engineering-guide.md](ai-engineering-guide.md), and [language-guidelines.md](language-guidelines.md).

**Vocabulary SSOT:** [Canonical Domain Language](../architecture/00-glossary.md) ([redirect](../glossary.md)).

## Before inventing a name

1. Search the glossary for an existing term.
2. Prefer existing symbols: `WorkspaceContext`, `StoredSegment`, `SegmentStatus`, `AccuracyGate`, `PipelineService`, `TranslationCheckpoint`, `LLMProvider`, …
3. If none fit, propose a glossary entry — do not silently mint synonyms (`AgentOrchestrator`, `EvalService`, `DocumentStore`, …).

## Correct vs incorrect assumptions

| Incorrect | Correct |
|-----------|---------|
| Multi-agent / agent framework product | Reflection **stages**: Draft → Critique → Refine |
| Critique is human review | Critique = LLM; **Review** = human (`pipeline review`) |
| AccuracyGate = critique JSON | AccuracyGate / validators = **structural**; critique = editorial LLM |
| PDF is a `lilt` command | Build → `.tex`; compile externally |
| Corpus / `project evaluate` in this repo | Out of product boundary |
| New top-level CLI verb | Only `project` / `pipeline` / `tm` / `telemetry` |
| `docs/adrs/` | Decisions in L1; no ADR tree |
| `pip install lilt` | Dist **`latex-lilt`**; CLI **`lilt`** |
| `workflow` always means the whole product | Three senses — see glossary table |
| TM = chat context | TM = JSONL segment memory; **context** has other senses |

## Where concepts belong

| Concept | Typical home |
|---------|----------------|
| CLI adaptation | `cli/` |
| Sync / translate / build orchestration | `services/` (+ `PipelineService`) |
| Reflection strategies, build, policies | `core/` |
| JSONL TM, checkpoint | `tm/` |
| Parse / placeholders | `parser/` |
| HTTP LLM / prompts | `llm/` |
| Structural validation | `validation/` |
| Config / segment models | `models/` |

Detail: [architectural-guidelines.md](architectural-guidelines.md).

## Overloaded words — always qualify

- **Stage** → translation stage vs compaction vs telemetry  
- **Context** → neighbor RAG vs `model_context_limit` vs Workspace Context vs `domain_context`  
- **Workflow** → pipeline vs `translation_mode: workflow` vs operator guide  
- **Model** → Pydantic vs LLM id  
- **Review** → never for LLM critique  

## Do not introduce

- Agent/swarm/orchestrator product framing  
- Synonym statuses (`pending`, `machine_done`) in new APIs — use `SegmentStatus` (+ documented CLI aliases only)  
- “Evaluation” as a shipped engine feature name  
- Parallel glossary or ADR vocabulary  

## Related

- [language-guidelines.md](language-guidelines.md)
- [ai-contribution-guidelines.md](ai-contribution-guidelines.md)
- [engineering-invariants.md](engineering-invariants.md)
