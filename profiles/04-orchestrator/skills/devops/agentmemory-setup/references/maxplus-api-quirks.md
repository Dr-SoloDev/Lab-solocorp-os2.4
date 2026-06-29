# MaxPlus API Quirks for agentmemory

## Overview
MaxPlus wraps the Anthropic API via a custom endpoint. Dashboard: https://maxplus-ai.cc/dashboard

## Key Format
- MaxPlus keys use format: `ccsk-...` (NOT `sk-ant-...`)
- Credit balance visible on dashboard (example session: $1026.43)

## agentmemory Field Name
agentmemory (iii-sdk) expects the env var `ANTHROPIC_API_KEY`.
Put the MaxPlus `ccsk-...` key in that field — it works because MaxPlus speaks
the Anthropic native wire format.

```env
ANTHROPIC_API_KEY=ccsk-xxxxxxxxxxxxxxxx
```

## Transport
- Transport type: `anthropic_messages` (Anthropic native wire)
- NOT an OpenAI shim — do not treat as OpenAI-compatible endpoint
- Hermes config sets: `transport: anthropic_messages`, provider: `custom:maxplus`

## Hermes config.yaml reference
```yaml
model:
  default: claude-sonnet-4-6
  provider: custom:maxplus
```

## Pricing (Sonnet, as of session May 2026)
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens
