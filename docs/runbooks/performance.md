# Performance

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **Token usage** | Draft + critique + refine = 3+ LLM calls per segment | `llm.cost_profile: balanced` (cheap critique) or `draft_only`; check `lilt tm status` |
| **Provider latency** | Local models: GPU-bound; cloud: network + rate limits | Hybrid topology: draft locally, refine in cloud; tune `llm.retry` |
| **Adaptive max tokens** | Global ceiling caused long decode outliers | StagePolicy adaptive output vs source size |
| **Checkpoint overhead** | JSONL append (+ fsync in `strict`) | `tm.durability: batched` for stage-end fsync; compaction at stage end |
| **TM file size** | Append-only JSONL grows until compaction | Stage-end compaction; `lilt tm admin repair` to compact manually |
| **Context window** | Larger windows = more tokens per call | Balanced defaults critique=`1`; override via `context_window` dict |
| **Linguistic bypass** | Pure-math segments skip LLM entirely | Automatic; no configuration needed |

---
