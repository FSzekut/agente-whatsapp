"""Teste de fumaça: o pacote e as dependências do requirements.txt importam."""

import importlib

import pytest


def test_pacote_importa_de_src():
    agente = importlib.import_module("agente")
    assert agente.__file__.endswith("src/agente/__init__.py")


# Nome de import, não de pacote: pyyaml vira yaml, python-dotenv vira dotenv.
DEPENDENCIAS = ["openai", "pydantic", "rapidfuzz", "yaml", "dotenv"]


@pytest.mark.parametrize("modulo", DEPENDENCIAS)
def test_dependencia_importa(modulo):
    importlib.import_module(modulo)
