# Configuration guide

Operator-oriented configuration. Full schema: [Configuration reference](../reference/config.md).

## Workspace layout

See [Getting started](../getting-started.md#workspace-layout-reference).

For modes, budget, and automation after first success: [Advanced usage](advanced-usage.md).

## LLM topologies

**Single provider:**

```yaml
llm:
  provider: openai
  base_url: http://localhost:11434/v1
  model: qwen2.5:72b
```

**Multi-model (same provider):**

```yaml
llm:
  provider: openai
  base_url: http://localhost:1234/v1
  model: qwen2.5:72b
  stages:
    draft:
      model: qwen2.5:72b
    critique:
      model: llama3:8b
```

**Hybrid local/cloud:**

```yaml
llm:
  provider: openai
  base_url: http://localhost:11434/v1
  model: qwen2.5:72b
  stages:
    draft:
      model: qwen2.5:72b
    critique:
      provider: openai
      base_url: https://api.openai.com/v1
      api_key: sk-proj-...
      model: gpt-4o
    refine:
      provider: openai
      base_url: https://api.openai.com/v1
      api_key: sk-proj-...
      model: gpt-4o-mini
```

---

## Protected terms and macros

Use `parser.protected_terms`, `parser.custom_macros`, and `lilt project configure` for discovery. Details: [01-platform](../architecture/01-platform.md) and [03-parser-masking](../architecture/03-parser-masking.md).
