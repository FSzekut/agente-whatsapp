# Tarefas da spec 001

> **v0, 08/10/2026.** Saem do [plano](plan.md) v1 e da [spec](spec.md) v1.2.
> **Uma tarefa por vez.** Cada uma termina com um commit que roda, o teste passando e o CI verde, e **para** para você
> conferir antes da próxima. Push só com o seu OK.

**Quem:** **F** = Fernando escreve; eu explico, reviso e, se você pedir, escrevo antes o teste de aceite (vermelho)
para você deixar verde. **C** = Claude implementa; você revisa.

**Duas trilhas.** As tarefas C da P0 não dependem das suas: enquanto eu monto o esqueleto, você pode criar as chaves
(T00) e começar o contrato (T06) assim que a T01 existir.

## P0: esqueleto

- [ ] **T00 · F · Chaves da camada gratuita.** Criar a chave no Google AI Studio e na Groq; copiar `.env.example`
  para `.env` e preencher; anotar os limites que o AI Studio mostra para o `gemini-3.5-flash-lite`.
  **Pronto:** a T05 passa com as suas chaves.
  **09/10:** chaves criadas e `diagnostico` verde nos dois modelos. **Falta anotar os limites do AI Studio.**
- [x] **T01 · C · Ambiente.** `uv venv` com Python 3.12; `requirements.txt` (`openai`, `pydantic`, `rapidfuzz`,
  `pyyaml`, `python-dotenv`) e `requirements-dev.txt` (`pytest`, `ruff`), com faixas de versão como no `rag_do_zero`;
  `pyproject.toml` com a configuração do `ruff` e do `pytest`; pacote `src/agente/`.
  **Pronto:** `ruff check` limpo e `pytest` rodando um teste de fumaça.
- [x] **T02 · C · CI.** `ci.yml`: `ruff` e `pytest`, sem nenhum segredo, e um passo que falha se algo de `logs/`,
  `outputs/` ou um `.env` estiver rastreado; versões das actions alinhadas com o `rag_do_zero`.
  **Pronto:** CI verde no GitHub (CA-01, CA-08).
- [ ] **T03 · C · O pet shop.** `scripts/gerar_dados.py` com semente fixa (RF-31): ~15 produtos com variação de
  tamanho, ~5 clientes com telefone fictício, ~10 pedidos; `negocio.yaml` com nome, tom, horário e política de
  autonomia; rascunho dos quatro documentos, incluindo *"só vendemos produtos; não fazemos banho e tosa"*.
  **Pronto:** a mesma semente gera arquivos idênticos; todo pedido tem cliente; nenhum trecho passa de ~55 palavras
  (D3). **Você revisa os documentos.**
- [x] **T04 · C · Pasta do negócio e fonte de dados.** `dados/negocio.py` carrega a pasta (RF-05); `dados/fonte.py`
  define a interface de fonte de dados e a leitura de arquivo (RF-06). A fonte devolve o pedido **com** o dono; quem
  decide se o cliente pode vê-lo é a sua ferramenta (T14).
  **Pronto:** testes carregam o pet shop; pedido inexistente devolve "não existe".
- [x] **T05 · C · Modelos e diagnóstico.** `config/modelos.yaml` com os dois modelos da D1, limites e preço pago
  (conferir o preço da Groq); `diagnostico` faz **uma** chamada com uma ferramenta de teste a cada modelo e diz se
  veio uma chamada de ferramenta, com latência e tokens. É de propósito só uma chamada, não o laço (o laço é seu).
  **Pronto:** com as suas chaves, os dois modelos devolvem chamada de ferramenta; sem chave, mensagem clara.
  **Feito em 09/10:** os dois chamaram `somar` com os argumentos certos. Groq 0,53 s, 358 tokens de entrada e 92 de
  saída (48 de raciocínio); Gemini 0,95 s, 106 e 23. O Gemini devolveu os argumentos em outra ordem (`b` antes de `a`).

## P1: a primeira chamada de ferramenta

- [ ] **T06 · F · Contrato** (RF-01, RF-02). `nucleo/contrato.py`: `Entrada`, `Saida` e os tipos que a saída carrega
  (chamada de ferramenta, uso), em pydantic.
  **Pronto:** testes de validação passam; `acao` e `envio` só aceitam os valores da spec.
- [ ] **T07 · F · Interface do modelo** (RF-12, RF-13). `modelo/base.py`: o que o laço precisa de qualquer modelo
  (mensagens e ferramentas entram; chamadas de ferramenta ou texto final, e o uso, saem). `modelo/openai_compat.py`:
  a implementação que lê `config/modelos.yaml`, com espera e repetição no 429.
  **Pronto:** uma chamada real à Groq com uma ferramenta volta convertida nos seus tipos.
  **Para entender antes:** no formato da OpenAI, o modelo devolve `tool_calls`, cada uma com um `id`; o resultado
  volta numa mensagem `role: tool` com o mesmo `tool_call_id`.
- [ ] **T08 · C · Modelo falso** (RS-07). `modelo/falso.py`: segue a sua interface e devolve respostas
  roteirizadas, para os testes rodarem sem rede. Depende da T07.
  **Pronto:** testes do próprio modelo falso passam no CI.
- [ ] **T09 · F · Registro e `buscar_produto`** (RF-11, RF-14). `ferramentas/registro.py`: um modelo pydantic por
  ferramenta gera o esquema enviado ao modelo e valida o argumento que volta. `ferramentas/produto.py`: sem acento,
  sem maiúscula, tolerante a erro de digitação, até 5 resultados.
  **Pronto:** *"rasão"* acha ração; *"ração"* com 6 itens devolve 5; sem resultado devolve lista vazia; argumento
  inválido é recusado pela validação.
- [ ] **T10 · F · O laço** (RF-07, RF-09, RF-10). `nucleo/agente.py`, por enquanto sem histórico: chama o modelo,
  executa ferramentas, devolve resultado ou erro estruturado, para no K e soma o uso.
  **Pronto:** com o modelo falso, passam os casos de estourar o K, ferramenta inexistente, argumento inválido e
  ferramenta que falha.
- [ ] **T11 · C · Chat, auditoria e custo** (RF-24, RF-25, RF-32). `chat --cliente --detalhe`; uma linha JSONL por
  mensagem em `logs/`, com o telefone mascarado; custo pelo preço pago da configuração. Depende da T06 e da T10.
  **Pronto:** no chat, com a Groq, *"tem ração de 3 kg?"* mostra a chamada, o preço, o custo e a latência.
- [ ] **T12 · C · Executor do gate** (RF-26, RF-28, RF-30). Lê `avaliacao/casos.yaml`; mede acerto de ferramenta, de
  argumento e de ação; aceita `--categoria` e `--casos`; fica abaixo do limite por minuto (plano, seção 6); termina com erro
  abaixo dos limiares da RF-29 ou com qualquer violação; no CI, roda contra o modelo falso.
  **Pronto:** o CI roda o gate falso; local, roda contra a Groq.
- [ ] **T13 · F · Casos de produto** (RF-27). ~6 casos: existe, não existe, ambíguo, erro de digitação, sem estoque,
  pergunta de preço.
  **Pronto:** a categoria produto passa na Groq. **Ponto de decisão:** se o Qwen errar ferramenta ou argumento aqui,
  troca-se o modelo antes da P2. Medir os tokens por chamada e refazer a conta da seção 6 do plano.

## P2: pedidos e estado

- [ ] **T14 · F · `consultar_pedido` com autorização** (RF-15, RS-05). O `cliente_id` chega por um contexto que o
  núcleo monta e não aparece no esquema; o número é normalizado.
  **Pronto:** pedido próprio devolve os dados; pedido alheio devolve **exatamente** a mesma resposta de pedido
  inexistente; `#00123`, `123` e *"pedido 123"* acham o mesmo pedido.
- [ ] **T15 · F · Histórico e estado** (RF-03, RF-04). `nucleo/historico.py` em `outputs/estado.sqlite3`: últimas N
  mensagens, recomeço depois de H horas, estado "com humano" e liberação.
  **Pronto:** testes com relógio injetado cobrem o corte em N, a expiração em H e o bloqueio "com humano".
- [ ] **T16 · F · `chamar_humano` e chamadas paralelas** (RF-08, RF-17, RF-20). Fila e protocolo; o laço executa
  todas as chamadas de uma rodada e devolve os resultados na ordem.
  **Pronto:** com o modelo falso, duas chamadas numa rodada viram uma resposta; `chamar_humano` leva a
  `acao = encaminhar` e ao estado "com humano".
- [ ] **T17 · C · `/nova`, `/liberar` e a checagem de vazamento** (RF-32, CA-04). Comandos do chat; no gate, uma
  violação sempre que a resposta trouxer dado de pedido de outro cliente.
  **Pronto:** um caso plantado com vazamento deixa o gate vermelho.
- [ ] **T18 · F · Casos de pedido e de conversa** (RF-27). ~10 casos: pedido próprio, alheio, inexistente e mal formatado;
  pedido de humano; injeção; referência à mensagem anterior; lista de compras.
  **Pronto:** essas categorias passam na Groq, com zero violação (CA-04).

## P3: documentos e comportamento

- [ ] **T19 · C · Índice dos documentos** (D3). `dados/indice.py`: `fastembed` importado só na hora de usar, um
  trecho por pergunta frequente, busca com fonte e semelhança; embedder falso para o CI; `fastembed` entra no
  `requirements.txt`.
  **Pronto:** o CI passa sem baixar o modelo; local, o índice do pet shop é construído.
- [ ] **T20 · F · `buscar_documentos` e `recusar`** (RF-16, RF-33). Limiar de semelhança que devolve
  `sem_evidencia`; a ferramenta `recusar`; a regra da `acao` completa.
  **Pronto:** testes de unidade passam, e o limiar foi escolhido medindo umas 6 perguntas, dentro e fora dos
  documentos, com o valor registrado abaixo.
- [ ] **T21 · F · Prompt e política** (RF-18 a RF-23). `nucleo/prompt.py` monta o prompt a partir da pasta do
  negócio; `nucleo/politica.py` decide o `envio`.
  **Pronto:** testes da política cobrem os três modos e a lista do `auto`; o prompt sai com nome e horário do
  negócio.
- [ ] **T22 · C · Checagens automáticas** (CA-03, CA-07, RF-22). No gate: todo valor em reais e todo status de
  pedido têm uma ferramenta por trás; formato do WhatsApp e limite de C caracteres; fatos obrigatórios e proibidos.
  Teste de que o núcleo não importa canal nem framework de agente.
  **Pronto:** cada checagem tem um caso plantado que a deixa vermelha.
- [ ] **T23 · F · Casos de documentos e de escopo** (RF-27). Documentos com e sem base, fora do escopo, banho e tosa,
  mensagem vazia: fechar os ~25.
  **Pronto:** **o gate completo passa na Groq com zero violação e nos limiares da RF-29 (CA-02).**

## P4: medição e fechamento

- [ ] **T24 · C · Gemini só pela configuração** (CA-05). O `diagnostico` e o gate rodam no Gemini sem mudar código.
  Se a compatibilidade beta falhar com ferramentas, o segundo modelo vira o `gpt-oss-120b` (plano, seção 7).
  **Pronto:** gate completo nos dois modelos.
- [ ] **T25 · C · Relatório comparativo** (RF-25, RF-29). Acerto, pass^k com `--repeticoes`, custo a preço pago
  (médio, p90, por mil conversas), latência p50 e p90, erros por categoria, em `outputs/relatorios/`.
  **Pronto:** o relatório responde às três perguntas da seção 7 da spec.
- [ ] **T26 · C · Negócio mínimo e configuração padrão** (CA-06, CA-09). `negocios/minimo/` com 5 produtos, 3
  pedidos e 1 documento, e um teste que roda o núcleo com ele; teste de que a configuração padrão só tem modelo
  gratuito. **Pronto:** os dois testes passam.
- [ ] **T27 · F + C · Fechamento.** Conferir CA-01 a CA-09 um a um; aplicar a sua regra do "pronto" com o
  estacionamento (spec, seção 11); decidir se a 002 começa.
  **Pronto:** todos marcados, e a decisão registrada abaixo.

## Registro de decisões

| Data | Decisão | Motivo |
|---|---|---|
| 08/10/2026 | D1: Groq `qwen/qwen3.8-27b` no dia a dia, Gemini `gemini-3.5-flash-lite` na comparação | Os `gpt-oss` da Groq não fazem chamadas paralelas; o Flash-Lite é o mais barato a preço pago |
| 08/10/2026 | D2: recusa como quinta ferramenta, RF-33, numerada no fim | Torna a recusa mensurável; não mexe na numeração das outras |
| 08/10/2026 | D3: embeddings locais com `fastembed` | Custo zero, nada sai da máquina, sem disputar o limite por minuto |
| 08/10/2026 | O `diagnostico` (T05) faz uma chamada só, não o laço | O laço é a parte que você vai defender |
| 08/10/2026 | `fastembed` só entra no `requirements.txt` na T19 | Ninguém precisa do modelo antes da P3 |
| 09/10/2026 | *(minha)* Telefones fictícios com DDD 00 (T03) | O DDD 00 não existe: nenhum número do repositório público pode ser de alguém |
| 09/10/2026 | *(minha)* `negocio.yaml` do pet shop em modo `auto`, com `consultar_pedido` fora da lista (T03) | O gate passa a exercitar os dois envios, e dado de pedido passa por uma pessoa até a CA-04 passar. Saída: `aprovar` |
| 09/10/2026 | *(minha)* Projeto instalável (`uv pip install -e .`) só para ganhar o comando `agente`, com as dependências lidas do `requirements.txt` (T05) | Uma fonte só para as dependências. Saída: `PYTHONPATH=src python -m agente.cli` |
| 09/10/2026 | *(minha)* O `diagnostico` usa uma ferramenta neutra, `somar(a, b)` (T05) | Não antecipa o desenho de `buscar_produto` (T09) |
| 09/10/2026 | ⟪aberta⟫ Na Groq, o raciocínio do Qwen tem padrão `none`; o plano usa `low` | Fica `low` até a P1 medir. Se o acerto não cair com `none`, ele corta custo e latência. **Primeira medida (09/10, `diagnostico`):** com `low`, 48 dos 92 tokens de saída foram raciocínio, numa soma de dois números |
| 09/10/2026 | Achado: o mesmo pedido com uma ferramenta custou **358 tokens de entrada na Groq e 106 no Gemini** | O template do Qwen escreve as definições de ferramenta no prompt. Com 200 mil tokens/dia na Groq, descrição de ferramenta curta é orçamento |
| 09/10/2026 | Achado: o Gemini devolve os argumentos em outra ordem | O laço lê argumento por nome, nunca por posição |
