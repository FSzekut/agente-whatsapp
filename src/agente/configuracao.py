"""Lê `config/modelos.yaml`: provedor, modelo, chave, limites e preço pago.

RF-12 (trocar de modelo é configuração) e RF-25 (custo pelo preço pago).
"""

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

CAMINHO_PADRAO = Path("config/modelos.yaml")


class ErroConfiguracao(ValueError):
    """Configuração de modelos ausente ou inválida."""


class Limites(BaseModel):
    """Limites da camada gratuita. Vazio quando o provedor não publica."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    req_min: int | None = Field(default=None, gt=0)
    req_dia: int | None = Field(default=None, gt=0)
    tokens_min: int | None = Field(default=None, gt=0)
    tokens_dia: int | None = Field(default=None, gt=0)


class Preco(BaseModel):
    """US$ por milhão de tokens, na camada paga."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entrada: Decimal = Field(ge=0)
    saida: Decimal = Field(ge=0)


class ConfigModelo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    base_url: str
    modelo: str
    chave_env: str
    extra: dict[str, Any] = {}
    limites: Limites = Limites()
    preco_pago_usd_milhao: Preco
    fonte: str


def carregar_modelos(caminho: Path = CAMINHO_PADRAO) -> dict[str, ConfigModelo]:
    try:
        dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    except FileNotFoundError as erro:
        raise ErroConfiguracao(f"{caminho}: arquivo não encontrado") from erro
    except yaml.YAMLError as erro:
        raise ErroConfiguracao(f"{caminho}: {erro}") from erro
    if not isinstance(dados, dict) or not dados:
        raise ErroConfiguracao(f"{caminho}: nenhum modelo configurado")
    modelos = {}
    for nome, valores in dados.items():
        try:
            modelos[nome] = ConfigModelo(**valores)
        except (TypeError, ValidationError) as erro:
            raise ErroConfiguracao(f"{caminho}, modelo {nome}: {erro}") from erro
    return modelos
