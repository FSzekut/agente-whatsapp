"""Gera os dados fictícios do pet shop: catálogo, clientes e pedidos (RF-31, RS-02).

A mesma semente gera sempre os mesmos arquivos, byte a byte. Os arquivos gerados são
versionados, e um teste confere que continuam iguais à saída do script: para mudar um
dado, muda-se o script, nunca o CSV à mão.

O negocio.yaml e os documentos não saem daqui: são escritos à mão (RF-31).

Uso:
    python scripts/gerar_dados.py                      # escreve em negocios/pet-shop/
    python scripts/gerar_dados.py --saida /tmp/x --semente 7
"""

import argparse
import csv
import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

SEMENTE = 2026
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "negocios" / "pet-shop"

# Lista escrita à mão: preço inventado e plausível não sai de sorteio. A semente decide
# estoque, clientes e pedidos. Seis rações, para "ração" ter mais de 5 resultados
# (RF-14), e três embalagens de 3 kg, para "ração de 3 kg" ser ambígua.
# (id, nome, categoria, espécie, preço)
PRODUTOS = [
    ("P01", "Ração Vitalis Cães Adultos Frango 3 kg", "ração", "cão", "69.90"),
    ("P02", "Ração Vitalis Cães Adultos Frango 10 kg", "ração", "cão", "189.90"),
    ("P03", "Ração Vitalis Cães Adultos Frango 15 kg", "ração", "cão", "259.90"),
    ("P04", "Ração Vitalis Cães Filhotes 3 kg", "ração", "cão", "79.90"),
    ("P05", "Ração Felinus Gatos Adultos Salmão 1 kg", "ração", "gato", "34.90"),
    ("P06", "Ração Felinus Gatos Adultos Salmão 3 kg", "ração", "gato", "89.90"),
    ("P07", "Areia Higiênica Grão Fino 4 kg", "higiene", "gato", "24.90"),
    ("P08", "Areia Higiênica Grão Fino 12 kg", "higiene", "gato", "59.90"),
    ("P09", "Petisco Bifinho de Frango 65 g", "petisco", "cão", "12.90"),
    ("P10", "Sachê Cremoso de Salmão para Gatos 4 un", "petisco", "gato", "15.90"),
    ("P11", "Tapete Higiênico 30 un", "higiene", "cão", "49.90"),
    ("P12", "Tapete Higiênico 50 un", "higiene", "cão", "74.90"),
    ("P13", "Coleira Ajustável Nylon P", "acessório", "cão", "29.90"),
    ("P14", "Coleira Ajustável Nylon M", "acessório", "cão", "34.90"),
    ("P15", "Arranhador Torre 60 cm", "acessório", "gato", "149.90"),
]
# Sem estoque de propósito: o caso de borda "produto sem estoque" da spec.
SEM_ESTOQUE = {"P03"}

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Heitor"]
SOBRENOMES = ["Almeida", "Barros", "Cardoso", "Duarte", "Esteves", "Fontana", "Gouveia"]

# Do pedido mais antigo para o mais novo: o status acompanha a idade do pedido.
STATUS_POR_IDADE = [
    "entregue",
    "entregue",
    "entregue",
    "entregue",
    "entregue",
    "enviado",
    "enviado",
    "em_separacao",
    "em_separacao",
    "aguardando_pagamento",
]
PRIMEIRO_PEDIDO = 120
PRIMEIRA_DATA = date(2026, 9, 14)
FRETE = Decimal("12.90")
FRETE_GRATIS_A_PARTIR_DE = Decimal("150.00")  # o mesmo valor do documento de entrega


def gerar_catalogo(rng: random.Random) -> list[dict]:
    return [
        {
            "id": id_,
            "nome": nome,
            "categoria": categoria,
            "especie": especie,
            "preco": preco,
            "estoque": 0 if id_ in SEM_ESTOQUE else rng.randint(2, 40),
        }
        for id_, nome, categoria, especie, preco in PRODUTOS
    ]


def gerar_clientes(rng: random.Random, quantidade: int = 5) -> list[dict]:
    nomes = rng.sample(NOMES, quantidade)
    clientes = []
    for nome in nomes:
        # DDD 00 não existe no Brasil: nenhum número daqui pode ser de alguém.
        telefone = "55009" + "".join(str(rng.randint(0, 9)) for _ in range(8))
        clientes.append(
            {"telefone": telefone, "nome": f"{nome} {rng.choice(SOBRENOMES)}"}
        )
    return clientes


def gerar_pedidos(
    rng: random.Random, catalogo: list[dict], clientes: list[dict]
) -> list[dict]:
    # O último cliente fica sem pedido de propósito: "cliente que nunca comprou".
    com_pedido = clientes[:-1]
    precos = {p["id"]: Decimal(p["preco"]) for p in catalogo}
    nomes = {p["id"]: p["nome"] for p in catalogo}

    # Um cancelado entre os mais antigos, em posição sorteada.
    status = list(STATUS_POR_IDADE)
    status[rng.randint(1, 4)] = "cancelado"

    # Cada cliente com pedido tem pelo menos um; os demais pedidos são sorteados.
    donos = [c["telefone"] for c in com_pedido]
    donos += [
        rng.choice(com_pedido)["telefone"] for _ in range(len(status) - len(donos))
    ]
    rng.shuffle(donos)

    pedidos = []
    dia = PRIMEIRA_DATA
    for i, (situacao, dono) in enumerate(zip(status, donos, strict=True)):
        dia += timedelta(days=rng.randint(1, 3)) if i else timedelta()
        escolhidos = rng.sample(sorted(precos), rng.randint(1, 3))
        itens = [
            {
                "produto": id_,
                "nome": nomes[id_],
                "quantidade": rng.randint(1, 2),
                "preco_unitario": str(precos[id_]),
            }
            for id_ in sorted(escolhidos)
        ]
        subtotal = sum(Decimal(it["preco_unitario"]) * it["quantidade"] for it in itens)
        frete = Decimal("0.00") if subtotal >= FRETE_GRATIS_A_PARTIR_DE else FRETE
        em_aberto = situacao in ("aguardando_pagamento", "em_separacao", "enviado")
        previsao = dia + timedelta(days=rng.randint(1, 3)) if em_aberto else None
        pedidos.append(
            {
                "numero": PRIMEIRO_PEDIDO + i,
                "cliente": dono,
                "data": dia.isoformat(),
                "status": situacao,
                "previsao_entrega": previsao.isoformat() if previsao else None,
                "itens": itens,
                "frete": str(frete),
                "total": str(subtotal + frete),
            }
        )
    return pedidos


def escrever_csv(caminho: Path, linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=list(linhas[0]), lineterminator="\n"
        )
        escritor.writeheader()
        escritor.writerows(linhas)


def gerar(saida: Path, semente: int = SEMENTE) -> None:
    rng = random.Random(semente)
    catalogo = gerar_catalogo(rng)
    clientes = gerar_clientes(rng)
    pedidos = gerar_pedidos(rng, catalogo, clientes)

    saida.mkdir(parents=True, exist_ok=True)
    escrever_csv(saida / "catalogo.csv", catalogo)
    escrever_csv(saida / "clientes.csv", clientes)
    texto = json.dumps(pedidos, ensure_ascii=False, indent=2)
    (saida / "pedidos.json").write_text(texto + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", type=Path, default=PASTA_PADRAO)
    parser.add_argument("--semente", type=int, default=SEMENTE)
    args = parser.parse_args()
    gerar(args.saida, args.semente)
    print(f"Dados gerados em {args.saida} com a semente {args.semente}.")


if __name__ == "__main__":
    main()
