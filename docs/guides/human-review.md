# Human review

Human editorial queue and external review. **Critique** (LLM MQM) vs **Review** (human): [00-glossary](../architecture/00-glossary.md).

## Review and inspection

```bash
lilt tm status main
lilt tm list main --id abc12345
lilt pipeline review main
lilt pipeline edit main abc12345
```

## External review (export / import)

```bash
lilt tm export main review.csv
# Human edits review.csv externally
lilt tm import main review.csv
```

Import updates translations and sets status to `reviewed`. Locked and deprecated segments are skipped.

## Reflection stages (machine)

| Stage | Input | Output | Segment status |
|-------|-------|--------|----------------|
| **Draft** | Masked source + context | Draft text | `drafted` (reflection on) or `refined` (reflection off) |
| **Critique** | Draft + source | Structured critique JSON | `critiqued` |
| **Refine** | Draft + critique + source | Validated translation | `refined` |

When `llm.reflection_enabled: false`, draft is validated and accepted directly as `refined`.
Pipeline detail: [04-translation-engine](../architecture/04-translation-engine.md).

## Segment statuses

Ten statuses and the canonical state machine live in
[02-persistence](../architecture/02-persistence.md). Human gates:
`reviewed` → `approved` → `locked`. Machine path ends at `refined`
(`refined` ≠ human-approved).

## See also

- [Workflows](workflows.md)
- [CLI reference](../reference/cli.md)
- [02-persistence](../architecture/02-persistence.md)
