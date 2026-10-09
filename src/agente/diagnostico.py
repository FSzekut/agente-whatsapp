"""Uma chamada com ferramenta a cada modelo configurado: a chave funciona e o modelo
devolve chamada de ferramenta pelo formato da OpenAI?

É de propósito uma chamada só, não o laço (o laço é a T10). Roda antes de cada rodada
de gate, porque a camada gratuita muda sem aviso (plano, seção 7).
"""

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import openai

from agente.configuracao import ConfigModelo

# Ferramenta neutra, que não antecipa o desenho das ferramentas do núcleo (T09).
FERRAMENTA_TESTE = {
    "type": "function",
    "function": {
        "name": "somar",
        "description": "Soma dois números inteiros e devolve o resultado.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "integer", "description": "Primeira parcela"},
                "b": {"type": "integer", "description": "Segunda parcela"},
            },
            "required": ["a", "b"],
        },
    },
}
MENSAGENS = [
    {
        "role": "system",
        "content": "Use a ferramenta somar para qualquer conta. Não calcule de cabeça.",
    },
    {"role": "user", "content": "Quanto é 1234 + 5678?"},
]
ARGUMENTOS_ESPERADOS = {"a": 1234, "b": 5678}
TIMEOUT_S = 30


@dataclass(frozen=True)
class Resultado:
    nome: str
    modelo: str
    ok: bool
    mensagem: str
    latencia_s: float | None = None
    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    tokens_raciocinio: int | None = None


def criar_cliente(config: ConfigModelo, chave: str) -> openai.OpenAI:
    # Sem repetição automática: um 429 aqui é informação, não algo a esconder.
    return openai.OpenAI(
        api_key=chave, base_url=config.base_url, max_retries=0, timeout=TIMEOUT_S
    )


def diagnosticar(
    nome: str,
    config: ConfigModelo,
    ambiente: Mapping[str, str],
    fabrica: Callable[[ConfigModelo, str], openai.OpenAI] = criar_cliente,
) -> Resultado:
    def resultado(ok: bool, mensagem: str, **medidas) -> Resultado:
        return Resultado(nome, config.modelo, ok, mensagem, **medidas)

    chave = ambiente.get(config.chave_env, "").strip()
    if not chave:
        return resultado(
            False, f"sem chave: defina {config.chave_env} no .env (veja .env.example)"
        )

    cliente = fabrica(config, chave)
    inicio = time.perf_counter()
    try:
        resposta = cliente.chat.completions.create(
            model=config.modelo,
            messages=MENSAGENS,
            tools=[FERRAMENTA_TESTE],
            extra_body=config.extra or None,
        )
    except openai.APIStatusError as erro:
        return resultado(
            False, f"o provedor devolveu {erro.status_code}: {_curto(erro)}"
        )
    except openai.APIError as erro:
        return resultado(False, f"falha de conexão: {_curto(erro)}")
    latencia = time.perf_counter() - inicio

    uso = resposta.usage
    detalhes = uso.completion_tokens_details if uso else None
    medidas = {
        "latencia_s": latencia,
        "tokens_entrada": uso.prompt_tokens if uso else None,
        "tokens_saida": uso.completion_tokens if uso else None,
        "tokens_raciocinio": detalhes.reasoning_tokens if detalhes else None,
    }

    chamadas = resposta.choices[0].message.tool_calls or []
    if not chamadas:
        texto = _curto(resposta.choices[0].message.content or "")
        return resultado(
            False, f"respondeu em texto, sem chamar a ferramenta: {texto}", **medidas
        )

    funcao = chamadas[0].function
    try:
        argumentos = json.loads(funcao.arguments)
    except json.JSONDecodeError:
        return resultado(
            False,
            f"chamou {funcao.name} com argumento que não é JSON: "
            f"{_curto(funcao.arguments)}",
            **medidas,
        )
    chamada = f"{funcao.name}({json.dumps(argumentos, ensure_ascii=False)})"
    if funcao.name != "somar" or argumentos != ARGUMENTOS_ESPERADOS:
        return resultado(
            False, f"chamou {chamada}, mas o esperado era somar(1234, 5678)", **medidas
        )
    return resultado(True, f"chamou {chamada}, argumentos certos", **medidas)


def formatar(resultado: Resultado) -> str:
    linhas = [
        f"{resultado.nome} ({resultado.modelo})",
        f"  {'✓' if resultado.ok else '✗'} {resultado.mensagem}",
    ]
    if resultado.latencia_s is not None:
        raciocinio = resultado.tokens_raciocinio
        detalhe = f" ({raciocinio} de raciocínio)" if raciocinio is not None else ""
        linhas.append(
            f"  latência {resultado.latencia_s:.2f} s · tokens: "
            f"{resultado.tokens_entrada} de entrada, {resultado.tokens_saida} de saída"
            f"{detalhe}"
        )
    return "\n".join(linhas)


def _curto(valor: object, limite: int = 200) -> str:
    texto = " ".join(str(valor).split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"
