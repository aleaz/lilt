# Performance

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **Token usage** | Draft + critique + refine = 3+ LLM calls per segment | Use `reflection_enabled: false` for single-pass; check `lilt tm status` for estimates |
| **Provider latency** | Local models: GPU-bound; cloud: network + rate limits | Hybrid topology: draft locally, refine in cloud; tune `llm.retry` |
| **Checkpoint overhead** | One JSONL append + fsync per segment | Negligible vs. LLM latency; compaction at stage end |
| **TM file size** | Append-only JSONL grows until compaction | Stage-end compaction; `lilt tm admin repair` to compact manually |
| **Context window** | Larger `context_window` = more tokens per call | Default `3`; reduce for small models |
| **Linguistic bypass** | Pure-math segments skip LLM entirely | Automatic; no configuration needed |

---
