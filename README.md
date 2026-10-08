# agente-whatsapp

A reusable customer-service agent for WhatsApp: **tool calling** (catalog lookup, order status, handoff to a human),
answers grounded in the business's own documents (with refusal when there is no evidence), and an **evaluation gate**
that measures tool accuracy and cost per conversation before anything ships.

**Status:** specification. Nothing implemented yet. Specs are written in Brazilian Portuguese, the language of the
target market.

## How it is cut

One core, three deliveries. The core is the same in all of them; only the last step changes: suggest, wait for
approval, or send.

| Slice | What | Channel | Autonomy | Docs |
|---|---|---|---|---|
| 001 | The core, channel-free: tools, document search, evaluation, cost | Command line | Any, by config | [spec](specs/001-nucleo/spec.md) · [plan](specs/001-nucleo/plan.md) · [tasks](specs/001-nucleo/tasks.md) |
| 002 | Official WhatsApp Cloud API (Meta) | WhatsApp | `approve`, `auto` | — |
| 003 | Browser extension on WhatsApp Web | WhatsApp Web | `suggest`: a human always sends | — |

Design rules that hold in every slice:

- **Facts come from tools.** Prices, stock and order status are never written from the model's memory
- **Authorization lives in code, not in the prompt.** The model never receives another customer's data, so no
  injected instruction can extract it
- **Business-only.** Off-topic requests are refused, as Meta's WhatsApp Business policy has required since January 2026
- **Zero cost in development.** Free API tiers with fictional data only; paid models only in client projects

## Secrets

This repository is public, so its whole history is. No secret is ever committed:

1. `.env` stays out of git; `.env.example` lists variable names only
2. A pre-commit hook runs [gitleaks](https://github.com/gitleaks/gitleaks) and refuses `.env` files and keys.
   Enable it once per clone:
   ```bash
   git config core.hooksPath .githooks
   ```
3. CI scans the full history with gitleaks on every push
4. GitHub secret scanning with push protection

CI needs no API key: tests run against a scripted fake model.
