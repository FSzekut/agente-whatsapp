"""Os dados fictícios do pet shop (RF-31): reproduzíveis, coerentes e com os casos de
borda que a spec e as tarefas usam."""

import csv
import json
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PET_SHOP = RAIZ / "negocios" / "pet-shop"
GERADOS = ["catalogo.csv", "clientes.csv", "pedidos.json"]
# D3: o embedding corta em 128 tokens. Medido em 09/10/2026 com o tokenizador do
# MiniLM multilingual: 1,5 token por palavra em média e até 2,0 com nome próprio,
# então 55 palavras ficam abaixo de 128 mesmo no pior caso visto.
MAX_PALAVRAS_POR_TRECHO = 55


def gerar(saida: Path, semente: int | None = None) -> None:
    comando = [
        sys.executable,
        str(RAIZ / "scripts" / "gerar_dados.py"),
        "--saida",
        str(saida),
    ]
    if semente is not None:
        comando += ["--semente", str(semente)]
    subprocess.run(comando, check=True, capture_output=True)


def ler_csv(nome: str) -> list[dict]:
    with (PET_SHOP / nome).open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


@pytest.fixture(scope="module")
def catalogo():
    return ler_csv("catalogo.csv")


@pytest.fixture(scope="module")
def clientes():
    return ler_csv("clientes.csv")


@pytest.fixture(scope="module")
def pedidos():
    return json.loads((PET_SHOP / "pedidos.json").read_text(encoding="utf-8"))


def test_mesma_semente_gera_os_arquivos_versionados(tmp_path):
    gerar(tmp_path / "a")
    gerar(tmp_path / "b")
    for nome in GERADOS:
        conteudo = (tmp_path / "a" / nome).read_bytes()
        assert conteudo == (tmp_path / "b" / nome).read_bytes()
        # Dado versionado que não bate com o script foi editado à mão.
        assert conteudo == (PET_SHOP / nome).read_bytes(), nome


def test_outra_semente_gera_outros_dados(tmp_path):
    gerar(tmp_path / "outra", semente=7)
    assert (tmp_path / "outra" / "pedidos.json").read_bytes() != (
        PET_SHOP / "pedidos.json"
    ).read_bytes()


def test_todo_pedido_tem_cliente_e_produtos_do_catalogo(catalogo, clientes, pedidos):
    telefones = {c["telefone"] for c in clientes}
    ids = {p["id"] for p in catalogo}
    for pedido in pedidos:
        assert pedido["cliente"] in telefones, pedido["numero"]
        assert pedido["itens"], pedido["numero"]
        assert {item["produto"] for item in pedido["itens"]} <= ids


def test_total_do_pedido_fecha(pedidos):
    for pedido in pedidos:
        itens = sum(
            Decimal(i["preco_unitario"]) * i["quantidade"] for i in pedido["itens"]
        )
        assert itens + Decimal(pedido["frete"]) == Decimal(pedido["total"])


def test_telefones_sao_impossiveis(clientes):
    # DDD 00 não existe: o repositório é público e nenhum número pode ser de alguém.
    for cliente in clientes:
        assert re.fullmatch(r"5500\d{9}", cliente["telefone"]), cliente["telefone"]


def test_casos_de_borda_da_spec_existem(catalogo, clientes, pedidos):
    racoes = [p for p in catalogo if "ração" in p["nome"].lower()]
    assert len(racoes) >= 6  # "ração" devolve só 5 (RF-14)
    assert sum("3 kg" in p["nome"] for p in racoes) >= 2  # "ração de 3 kg" é ambígua
    assert any(p["estoque"] == "0" for p in catalogo)  # produto sem estoque
    assert 123 in {p["numero"] for p in pedidos}  # "#00123", "123" e "pedido 123"
    assert {c["telefone"] for c in clientes} - {p["cliente"] for p in pedidos}
    assert len({p["cliente"] for p in pedidos}) >= 2  # há pedido alheio para testar


def trechos(caminho: Path) -> list[tuple[str, str]]:
    """Um trecho por pergunta: o título `## ` e o parágrafo que vem depois."""
    texto = caminho.read_text(encoding="utf-8")
    blocos = re.split(r"^## ", texto, flags=re.MULTILINE)[1:]
    return [
        (pergunta.strip(), " ".join(resposta.split()))
        for pergunta, _, resposta in (b.partition("\n") for b in blocos)
    ]


def test_quatro_documentos_e_todo_trecho_cabe_no_embedding():
    documentos = sorted((PET_SHOP / "documentos").glob("*.md"))
    assert len(documentos) == 4
    for documento in documentos:
        assert trechos(documento), documento.name
        for pergunta, resposta in trechos(documento):
            palavras = len(f"{pergunta} {resposta}".split())
            assert palavras <= MAX_PALAVRAS_POR_TRECHO, (documento.name, pergunta)


def test_documento_diz_que_a_loja_so_vende_produtos():
    texto = " ".join(
        " ".join(r for _, r in trechos(d))
        for d in (PET_SHOP / "documentos").glob("*.md")
    )
    assert "só vende produtos" in texto
    assert "Não fazemos banho, tosa" in texto
