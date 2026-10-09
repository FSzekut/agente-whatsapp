"""Fonte de dados do negócio: catálogo e pedidos atrás de uma interface (RF-06).

A 001 lê de arquivo. Planilha ou API do cliente é outra classe com os mesmos dois
métodos, não outra versão do núcleo. A fonte devolve o pedido **com** o dono: quem
decide se o cliente da conversa pode vê-lo é a ferramenta `consultar_pedido` (RS-05).
"""

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

StatusPedido = Literal[
    "aguardando_pagamento", "em_separacao", "enviado", "entregue", "cancelado"
]


class ErroDados(ValueError):
    """Arquivo do negócio ausente ou inválido, com o nome do arquivo na mensagem."""


class Produto(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    nome: str
    categoria: str
    especie: str
    preco: Decimal = Field(gt=0)
    estoque: int = Field(ge=0)

    @property
    def disponivel(self) -> bool:
        return self.estoque > 0


class ItemPedido(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    produto: str
    nome: str
    quantidade: int = Field(ge=1)
    preco_unitario: Decimal = Field(gt=0)


class Pedido(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    numero: int
    cliente: str  # telefone do dono
    data: date
    status: StatusPedido
    previsao_entrega: date | None
    itens: list[ItemPedido] = Field(min_length=1)
    frete: Decimal = Field(ge=0)
    total: Decimal = Field(gt=0)


@runtime_checkable
class FonteDados(Protocol):
    """O que o núcleo precisa de qualquer fonte. Não precisa herdar: basta ter os
    dois métodos."""

    def produtos(self) -> list[Produto]: ...

    def pedido(self, numero: int) -> Pedido | None:
        """O pedido com esse número, de qualquer cliente, ou None se não existe."""
        ...


class FonteArquivo:
    """Lê `catalogo.csv` e `pedidos.json` da pasta do negócio, uma vez, ao criar."""

    def __init__(self, pasta: Path):
        self._produtos = _ler_catalogo(pasta / "catalogo.csv")
        self._pedidos = _ler_pedidos(pasta / "pedidos.json")

    def produtos(self) -> list[Produto]:
        return list(self._produtos)

    def pedido(self, numero: int) -> Pedido | None:
        return self._pedidos.get(numero)


def _ler_catalogo(caminho: Path) -> list[Produto]:
    try:
        with caminho.open(encoding="utf-8", newline="") as arquivo:
            produtos = [Produto(**linha) for linha in csv.DictReader(arquivo)]
    except FileNotFoundError as erro:
        raise ErroDados(f"{caminho}: arquivo não encontrado") from erro
    except ValidationError as erro:
        raise ErroDados(f"{caminho}: {erro}") from erro
    ids = [p.id for p in produtos]
    if len(ids) != len(set(ids)):
        raise ErroDados(f"{caminho}: id de produto repetido")
    return produtos


def _ler_pedidos(caminho: Path) -> dict[int, Pedido]:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        pedidos = [Pedido(**p) for p in dados]
    except FileNotFoundError as erro:
        raise ErroDados(f"{caminho}: arquivo não encontrado") from erro
    except (json.JSONDecodeError, ValidationError) as erro:
        raise ErroDados(f"{caminho}: {erro}") from erro
    por_numero = {p.numero: p for p in pedidos}
    if len(por_numero) != len(pedidos):
        raise ErroDados(f"{caminho}: número de pedido repetido")
    return por_numero
