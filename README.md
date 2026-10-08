# agente-whatsapp

Base reutilizável de agente de atendimento para WhatsApp: chamada de ferramentas (catálogo, pedido, encaminhamento
para humano), busca nos documentos do negócio com recusa quando não há base, e um gate de avaliação que mede acerto e
custo por conversa.

**Status:** especificação. Nada implementado.

| Fatia | O quê | Spec |
|---|---|---|
| 001 | Núcleo, sem canal: ferramentas, documentos, avaliação, custo | [specs/001-nucleo/spec.md](specs/001-nucleo/spec.md) |
| 002 | API oficial do WhatsApp (Cloud API da Meta), modos `aprovar` e `auto` | — |
| 003 | Extensão sobre o WhatsApp Web, modo `sugerir` | — |
