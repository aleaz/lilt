# FAQ

Short answers to common product questions. **Failures and recovery** live in [Troubleshooting](runbooks/troubleshooting.md), [Error reference](runbooks/error-reference.md), and [Recovery](runbooks/recovery.md) — this page does not duplicate those procedures.

Hub: [Documentation](README.md). Support routing: [SUPPORT.md](../SUPPORT.md).

## What is LILT?

LILT (*LaTeX Intelligent Localization Tool*) is a CLI that localizes LaTeX by parsing into **segments**, masking structure into **placeholders**, storing state in a **Translation Memory** (JSONL), calling an LLM for prose, validating structure, then **building** a localized `.tex`.

It is **not** affiliated with [Lilt Inc.](https://lilt.com/) / lilt.com. It is **not** a CAT GUI and **not** a PDF compiler.

More: [Concepts](concepts.md).

## Why should I use it?

When you care about **compile-safe** structure, **human-protected** statuses (`reviewed` / `approved` / `locked`), and a durable TM under `.lilt/tm/` — rather than pasting whole `.tex` files into a chat.

## How does the workflow work?

At a glance: `project init` → configure LLM → `pipeline sync` → `pipeline translate` → `pipeline build` (PDF is external).

- Quick path: [Getting started](getting-started.md)
- Explained once: [First translation](guides/first-translation.md)
- Day-to-day: [Workflows](guides/workflows.md)

## Which LLM providers are supported?

The shipped factory adapter is **OpenAI-compatible** (`provider: openai`): local servers (e.g. LM Studio / Ollama-style `/v1`) or cloud endpoints that speak the same HTTP API. Per-stage `base_url` / `model` / keys are supported.

There is **no** separate plugin marketplace for other vendor SDKs in this repo. Deferred ideas: [appendix-deferred](architecture/appendix-deferred.md).

## How do I configure a provider?

Edit `.lilt/lilt.yaml` (`llm.base_url`, `llm.model`, languages). Put cloud keys in `.lilt/.env`. Topologies: [Configuration guide](guides/configuration.md). Keys: [Configuration reference](reference/config.md).

## Can I resume a failed or interrupted translation?

Yes. Re-run `lilt pipeline translate` (or `--all`). Finished segments stay in the TM. Details: [Workflows — resume](guides/workflows.md#scenario-resume-an-interrupted-translation) and [Recovery](runbooks/recovery.md#interrupted-translation).

## How does Translation Memory work?

Segments live in append-oriented JSONL under `.lilt/tm/`, one file per namespace. Inspect with `tm list` / `tm status`. Human statuses are not auto-overwritten by MT. Operator scenarios: [Workflows — TM](guides/workflows.md#scenario-manage-translation-memory).

## How do I debug an error?

```bash
lilt --debug …          # stdout + .lilt/lilt.log
lilt tm list NS --status error
lilt tm list NS --status conflict
```

Then: [Troubleshooting](runbooks/troubleshooting.md) → [Error reference](runbooks/error-reference.md).

## Does LILT produce PDF?

No. Build writes `.tex`. Compile with your TeX distribution. See troubleshooting for multi-pass `???` refs.

## How do I install it? (`pip install lilt`?)

**Do not** `pip install lilt` — that name is another project. Install from Git; distribution package is **`latex-lilt`**; CLI is **`lilt`**. See [Getting started](getting-started.md#1-install).

## When is something a bug vs my setup?

| Likely usage / env | Likely product bug |
|--------------------|--------------------|
| Wrong install package, missing LLM, empty config, busy namespace, fail-closed build on unfinished statuses | Crash with no clear domain message, wrong Behavior vs L1/docs after correct setup, data loss of human locks without `--force` |

Open issues per [SUPPORT.md](../SUPPORT.md). Check troubleshooting first.

## Where is the full command list?

[CLI reference](reference/cli.md) — not this FAQ.
