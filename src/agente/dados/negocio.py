"""Carrega a pasta do negócio (RF-05): trocar de negócio é trocar a pasta.

A pasta tem:
    negocio.yaml      nome, tom, horário e política de autonomia (escrito à mão)
    catalogo.csv      lido pela fonte de dados (RF-06)
    pedidos.json      idem
    documentos/*.md   um `# Título` e um trecho por `## Pergunta`, com a resposta
                      logo abaixo; é a unidade que a busca nos documentos indexa
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from agente.dados.fonte import ErroDados, FonteArquivo, FonteDados

Acao = Literal["responder", "encaminhar", "recusar"]


class ListaAuto(BaseModel):
    """No modo `auto`, o que pode sair sem revisão humana (RF-23)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    acoes: list[Acao] = []
    ferramentas: list[str] = []


class Autonomia(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    modo: Literal["sugerir", "aprovar", "auto"]
    auto: ListaAuto = ListaAuto()


class ConfigNegocio(BaseModel):
    """O `negocio.yaml`. Chave desconhecida é erro, para digitação não passar calada."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    nome: str
    descricao: str
    tom: str
    fuso: str
    horario: dict[str, str] = Field(min_length=1)
    autonomia: Autonomia

    @field_validator("fuso")
    @classmethod
    def _fuso_existe(cls, valor: str) -> str:
        try:
            ZoneInfo(valor)
        except (ZoneInfoNotFoundError, ValueError) as erro:
            raise ValueError(f"fuso desconhecido: {valor}") from erro
        return valor


@dataclass(frozen=True)
class Trecho:
    documento: str  # nome do arquivo, sem extensão: é a fonte citada (RF-16)
    pergunta: str
    resposta: str

    @property
    def texto(self) -> str:
        return f"{self.pergunta}\n{self.resposta}"


@dataclass(frozen=True)
class Documento:
    nome: str
    titulo: str
    trechos: list[Trecho]


@dataclass(frozen=True)
class Negocio:
    pasta: Path
    config: ConfigNegocio
    documentos: list[Documento]
    fonte: FonteDados
    versao: str  # muda quando qualquer arquivo da pasta muda (RF-02, `versoes`)

    @property
    def trechos(self) -> list[Trecho]:
        return [t for d in self.documentos for t in d.trechos]


def carregar_negocio(pasta: Path) -> Negocio:
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ErroDados(f"{pasta}: pasta do negócio não encontrada")
    return Negocio(
        pasta=pasta,
        config=_ler_config(pasta / "negocio.yaml"),
        documentos=[ler_documento(c) for c in sorted(pasta.glob("documentos/*.md"))],
        fonte=FonteArquivo(pasta),
        versao=_versao(pasta),
    )


def ler_documento(caminho: Path) -> Documento:
    texto = caminho.read_text(encoding="utf-8")
    titulo = re.search(r"^# (.+)$", texto, flags=re.MULTILINE)
    blocos = re.split(r"^## ", texto, flags=re.MULTILINE)[1:]
    trechos = [
        Trecho(caminho.stem, pergunta.strip(), " ".join(resposta.split()))
        for pergunta, _, resposta in (b.partition("\n") for b in blocos)
    ]
    if not titulo or not trechos:
        raise ErroDados(
            f"{caminho}: o documento precisa de um `# Título` e de pelo menos uma "
            "seção `## Pergunta` com a resposta abaixo"
        )
    if any(not t.resposta for t in trechos):
        raise ErroDados(f"{caminho}: há pergunta sem resposta")
    return Documento(caminho.stem, titulo.group(1).strip(), trechos)


def _ler_config(caminho: Path) -> ConfigNegocio:
    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        return ConfigNegocio(**(dados or {}))
    except FileNotFoundError as erro:
        raise ErroDados(f"{caminho}: arquivo não encontrado") from erro
    except (yaml.YAMLError, ValidationError) as erro:
        raise ErroDados(f"{caminho}: {erro}") from erro


def _versao(pasta: Path) -> str:
    """Os 12 primeiros caracteres do sha256 de todos os arquivos, em ordem."""
    resumo = hashlib.sha256()
    for caminho in sorted(p for p in pasta.rglob("*") if p.is_file()):
        resumo.update(caminho.relative_to(pasta).as_posix().encode())
        resumo.update(caminho.read_bytes())
    return resumo.hexdigest()[:12]
