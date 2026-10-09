"""A pasta do negócio (RF-05) e a fonte de dados de arquivo (RF-06)."""

import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from agente.dados.fonte import ErroDados, FonteArquivo, FonteDados
from agente.dados.negocio import carregar_negocio, ler_documento

PET_SHOP = Path(__file__).resolve().parent.parent / "negocios" / "pet-shop"


@pytest.fixture(scope="module")
def negocio():
    return carregar_negocio(PET_SHOP)


@pytest.fixture
def copia(tmp_path):
    """Uma cópia do pet shop para estragar à vontade."""
    destino = tmp_path / "pet-shop"
    shutil.copytree(PET_SHOP, destino)
    return destino


def test_carrega_o_pet_shop(negocio):
    assert negocio.config.nome == "Empório Quatro Patas"
    assert negocio.config.autonomia.modo == "auto"
    assert "consultar_pedido" not in negocio.config.autonomia.auto.ferramentas
    assert len(negocio.documentos) == 4
    assert len(negocio.trechos) == 16
    assert len(negocio.fonte.produtos()) == 15


def test_trecho_cita_o_documento_de_origem(negocio):
    trecho = next(t for t in negocio.trechos if "banho e tosa" in t.pergunta)
    assert trecho.documento == "perguntas-frequentes"
    assert trecho.texto.startswith("Vocês fazem banho e tosa?\nNão.")


def test_fonte_de_arquivo_segue_a_interface(negocio):
    assert isinstance(negocio.fonte, FonteDados)


def test_produto_vem_com_preco_exato_e_disponibilidade(negocio):
    produtos = {p.id: p for p in negocio.fonte.produtos()}
    assert produtos["P01"].preco == Decimal("69.90")
    assert produtos["P01"].disponivel
    assert not produtos["P03"].disponivel  # sem estoque de propósito


def test_pedido_vem_com_o_dono(negocio):
    pedido = negocio.fonte.pedido(123)
    assert pedido is not None
    assert pedido.cliente.startswith("5500")
    assert pedido.status == "entregue"


def test_pedido_inexistente_devolve_none(negocio):
    assert negocio.fonte.pedido(999) is None


def test_versao_e_estavel_e_muda_com_o_conteudo(negocio, copia):
    assert carregar_negocio(PET_SHOP).versao == negocio.versao
    assert carregar_negocio(copia).versao == negocio.versao
    documento = copia / "documentos" / "horario-e-contato.md"
    documento.write_text(documento.read_text(encoding="utf-8") + "\n", "utf-8")
    assert carregar_negocio(copia).versao != negocio.versao


def test_chave_desconhecida_no_yaml_e_erro(copia):
    yaml = copia / "negocio.yaml"
    yaml.write_text(yaml.read_text(encoding="utf-8") + "\nhorario_extra: 1\n", "utf-8")
    with pytest.raises(ErroDados, match=r"negocio\.yaml"):
        carregar_negocio(copia)


def test_modo_de_autonomia_invalido_e_erro(copia):
    yaml = copia / "negocio.yaml"
    yaml.write_text(
        yaml.read_text(encoding="utf-8").replace("modo: auto", "modo: total"), "utf-8"
    )
    with pytest.raises(ErroDados, match="modo"):
        carregar_negocio(copia)


def test_fuso_desconhecido_e_erro(copia):
    yaml = copia / "negocio.yaml"
    texto = yaml.read_text(encoding="utf-8")
    yaml.write_text(texto.replace("America/Sao_Paulo", "America/Curitba"), "utf-8")
    with pytest.raises(ErroDados, match="fuso"):
        carregar_negocio(copia)


def test_arquivo_ausente_cita_o_arquivo(copia):
    (copia / "catalogo.csv").unlink()
    with pytest.raises(ErroDados, match=r"catalogo\.csv: arquivo não encontrado"):
        carregar_negocio(copia)


def test_pedido_com_status_desconhecido_e_erro(copia):
    pedidos = copia / "pedidos.json"
    texto = pedidos.read_text(encoding="utf-8")
    pedidos.write_text(texto.replace('"entregue"', '"perdido"', 1), "utf-8")
    with pytest.raises(ErroDados, match=r"pedidos\.json"):
        FonteArquivo(copia)


def test_documento_sem_secao_e_erro(tmp_path):
    documento = tmp_path / "solto.md"
    documento.write_text("# Solto\n\nTexto corrido, sem pergunta.\n", "utf-8")
    with pytest.raises(ErroDados, match="## Pergunta"):
        ler_documento(documento)


def test_pasta_inexistente_e_erro(tmp_path):
    with pytest.raises(ErroDados, match="pasta do negócio"):
        carregar_negocio(tmp_path / "nao-existe")
