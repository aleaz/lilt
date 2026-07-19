# Performance

## Quick factors

| Factor | Impact | Mitigation |
|--------|--------|------------|
| **Token usage** | Draft + critique + refine = 3+ LLM calls per segment | `llm.cost_profile: balanced` (cheap critique) or `draft_only`; check `lilt tm status` |
| **Provider latency** | Local: GPU-bound; cloud: network + rate limits | Hybrid `llm.stages`; tune `llm.retry` |
| **Adaptive max tokens** | Global ceiling caused long decode outliers | StagePolicy adaptive output vs source size |
| **Checkpoint overhead** | JSONL append (+ fsync in `strict`) | `tm.durability: batched`; compaction at stage end |
| **TM file size** | Append-only JSONL grows until compaction | Stage-end compaction; `lilt tm admin repair` |
| **Context window** | Larger windows = more tokens per call | Set `model_context_limit` to serving **n_ctx** (e.g. 32768); default `8192` is smoke only |
| **Server thinking / reasoning** | Can starve `message.content` inside `max_tokens` | See below; prefer `stage_policies.*.thinking: off` |
| **Linguistic bypass** | Pure-math segments skip LLM | Automatic |

## Contract: content vs reasoning

LILT only persists **`message.content`** (translation text or critique JSON). Server **thinking / reasoning** tokens do not write the TM. If reasoning fills `max_tokens` and content is empty, you get `OutputTokenStarvationError`.

**Do not confuse:**

| Concept | What it is |
|---------|------------|
| `model_context_limit` | Serving context window (n_ctx); packing budget |
| `max_tokens` | Completion ceiling (may include reasoning when thinking is on) |
| `reasoning_reserve` | Extra reservation for **neighbor packing** when `output_token_mode: split_budget` — **not** “think N tokens” |
| `stage_policies.*.thinking` | Product hint: `off` / `on` / `minimal` (best-effort to the API) |
| `prompt_profile: reasoned_gate` | Critique **prompt** asks for a `<reasoning>` block (`strict` profile) — **not** LM Studio Enable Thinking |

## Capacity tiers (local = cloud)

Pick the tier by **stable n_ctx you can load**, not by the RAM sticker alone. MoE on ~24GB unified memory can often sustain more context than a dense model on the same machine.

| Tier | How you get there (examples) | Typical n_ctx | Thinking policy |
|------|------------------------------|---------------|-----------------|
| Constrained | 24GB + heavy dense; n_ctx already at limit | 8k–16k | **off** (all stages) |
| Comfortable | 48GB; or **24GB + MoE** with stable 32k | ≥32k | off on critique/refine; draft `on` only if measured |
| Ample | ~128GB local (e.g. Spark); large MoE + high ctx | 64k–128k | same stage matrix as cloud |
| Cloud API | Vendor window / quota | 128k+ | same matrix; optimize **$ / latency** |

Checklist:

1. Load model at target n_ctx without thrashing (dense or MoE).
2. Set `llm.model_context_limit` to that n_ctx.
3. Keep `max_tokens` well below context (never ≈ context).
4. If server thinking is on: use `output_token_mode: split_budget` + positive `reasoning_reserve`.
5. Prefer `thinking: off` on critique/refine; smoke that `reasoning_tokens == 0` when policy is off.
6. Run `lilt tm budget <namespace>` after sync.

## Stage matrix (defaults for `cost_profile: balanced`)

| Stage | Default `thinking` | Why |
|-------|-------------------|-----|
| draft | `off` | Starvation hurts here; opt-in `on` only on Comfortable+ |
| critique | `off` | JSON gate + AccuracyGate; thinking burns tokens / breaks JSON |
| refine | `off` | Final text, not a monologue |

Override example:

```yaml
llm:
  model_context_limit: 32768
  max_tokens: 4096
  output_token_mode: split_budget   # recommended if server thinking may be on
  reasoning_reserve: 1024
  cost_profile: balanced
  stage_policies:
    draft:
      thinking: off
    critique:
      thinking: off
    refine:
      thinking: off
```

**Local (LM Studio):** My Models → model settings → Inference → Reasoning → Enable Thinking Off → Unload/Load. Align Context Length with `model_context_limit`.

**Cloud:** pass effort/thinking via the same StagePolicy hints when the vendor supports them; otherwise configure the vendor dashboard / model choice.

## Related docs

- Config knobs: [docs/reference/config.md](../reference/config.md)
- Budget math: [docs/architecture/05-llm-layer.md](../architecture/05-llm-layer.md)
- Starvation / context errors: [docs/runbooks/troubleshooting.md](troubleshooting.md)

---
