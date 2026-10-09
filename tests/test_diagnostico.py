"""`config/modelos.yaml` e o `diagnostico` (T05), sem rede: o cliente é falso."""

import json
import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx2
import openai
import pytest
from openai.types.chat import ChatCompletion

from agente import cli
from agente.configuracao import ErroConfiguracao, carregar_modelos
from agente.diagnostico import diagnosticar, formatar

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config" / "modelos.yaml"
AMBIENTE = {"GROQ_API_KEY": "chave-falsa", "GEMINI_API_KEY": "chave-falsa"}


@pytest.fixture(scope="module")
def modelos():
    return carregar_modelos(CONFIG)


def resposta(*, tool_calls=None, content=None, reasoning=7) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "falso",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls" if tool_calls else "stop",
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "total_tokens": 150,
                "completion_tokens_details": {"reasoning_tokens": reasoning},
            },
        }
    )


def chamada(nome: str, argumentos: str) -> dict:
    return {
        "id": "c1",
        "type": "function",
        "function": {"name": nome, "arguments": argumentos},
    }


def fabrica_que_devolve(valor):
    """Cliente falso: devolve `valor`, ou o levanta se for exceção, e anota o pedido."""
    pedidos = []

    def criar(**kwargs):
        pedidos.append(kwargs)
        if isinstance(valor, Exception):
            raise valor
        return valor

    cliente = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=criar))
    )
    return (lambda config, chave: cliente), pedidos


def test_config_tem_os_dois_modelos_da_d1(modelos):
    assert modelos["groq-qwen"].modelo == "qwen/qwen3.8-27b"
    assert modelos["gemini-flash-lite"].modelo == "gemini-3.5-flash-lite"
    # O YAML lê 0.30 como float; o preço tem de chegar exato, sem 0,2999...
    assert modelos["groq-qwen"].preco_pago_usd_milhao.saida == Decimal("4.00")
    assert modelos["gemini-flash-lite"].preco_pago_usd_milhao.entrada == Decimal("0.3")
    assert modelos["groq-qwen"].limites.tokens_dia == 200_000


def test_toda_chave_da_config_esta_no_env_example(modelos):
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    nomes = set(re.findall(r"^([A-Z_]+)=", exemplo, flags=re.MULTILINE))
    assert {m.chave_env for m in modelos.values()} <= nomes


def test_config_com_campo_desconhecido_e_erro(tmp_path):
    caminho = tmp_path / "modelos.yaml"
    caminho.write_text(
        CONFIG.read_text(encoding="utf-8").replace("chave_env:", "chave:", 1), "utf-8"
    )
    with pytest.raises(ErroConfiguracao, match="groq-qwen"):
        carregar_modelos(caminho)


def test_sem_chave_avisa_e_nao_cria_cliente(modelos):
    def fabrica(config, chave):
        raise AssertionError("não devia criar cliente sem chave")

    resultado = diagnosticar("groq-qwen", modelos["groq-qwen"], {}, fabrica)
    assert not resultado.ok
    assert "GROQ_API_KEY" in resultado.mensagem


def test_chamada_certa_passa_e_mede(modelos):
    fabrica, pedidos = fabrica_que_devolve(
        resposta(tool_calls=[chamada("somar", '{"a": 1234, "b": 5678}')])
    )
    resultado = diagnosticar("groq-qwen", modelos["groq-qwen"], AMBIENTE, fabrica)
    assert resultado.ok, resultado.mensagem
    assert (resultado.tokens_entrada, resultado.tokens_saida) == (120, 30)
    assert resultado.tokens_raciocinio == 7
    assert resultado.latencia_s is not None
    # A requisição leva a ferramenta e os parâmetros próprios do provedor.
    assert pedidos[0]["tools"][0]["function"]["name"] == "somar"
    assert pedidos[0]["extra_body"]["reasoning_effort"] == "low"
    assert "✓" in formatar(resultado)


def test_resposta_em_texto_reprova(modelos):
    fabrica, _ = fabrica_que_devolve(resposta(content="1234 + 5678 = 6912"))
    resultado = diagnosticar("groq-qwen", modelos["groq-qwen"], AMBIENTE, fabrica)
    assert not resultado.ok
    assert "sem chamar a ferramenta" in resultado.mensagem


@pytest.mark.parametrize(
    "nome, argumentos",
    [("somar", '{"a": 1234, "b": 1}'), ("subtrair", '{"a": 1234, "b": 5678}')],
)
def test_ferramenta_ou_argumento_errado_reprova(modelos, nome, argumentos):
    fabrica, _ = fabrica_que_devolve(resposta(tool_calls=[chamada(nome, argumentos)]))
    resultado = diagnosticar("groq-qwen", modelos["groq-qwen"], AMBIENTE, fabrica)
    assert not resultado.ok
    assert "esperado" in resultado.mensagem


def test_argumento_que_nao_e_json_reprova(modelos):
    fabrica, _ = fabrica_que_devolve(resposta(tool_calls=[chamada("somar", "a=1")]))
    resultado = diagnosticar("groq-qwen", modelos["groq-qwen"], AMBIENTE, fabrica)
    assert not resultado.ok
    assert "não é JSON" in resultado.mensagem


def test_limite_de_taxa_vira_mensagem(modelos):
    pedido = httpx2.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    erro = openai.RateLimitError(
        "Rate limit reached",
        response=httpx2.Response(429, request=pedido),
        body=None,
    )
    fabrica, _ = fabrica_que_devolve(erro)
    resultado = diagnosticar("groq-qwen", modelos["groq-qwen"], AMBIENTE, fabrica)
    assert not resultado.ok
    assert "429" in resultado.mensagem


def test_cli_sem_chave_termina_com_erro(monkeypatch, tmp_path, capsys):
    # Um .env com chave de verdade nunca pode levar este teste para a rede.
    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    codigo = cli.main(["diagnostico", "--config", str(CONFIG)])

    saida = capsys.readouterr().out
    assert codigo == 1
    assert "GROQ_API_KEY" in saida and "GEMINI_API_KEY" in saida


def test_cli_modelo_desconhecido(capsys):
    assert cli.main(["diagnostico", "--config", str(CONFIG), "--modelo", "x"]) == 2
    assert "groq-qwen" in capsys.readouterr().err


def test_ferramenta_de_teste_e_json_valido():
    from agente.diagnostico import FERRAMENTA_TESTE

    assert json.loads(json.dumps(FERRAMENTA_TESTE)) == FERRAMENTA_TESTE
