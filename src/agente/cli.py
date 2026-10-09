"""Linha de comando do agente (RF-32). Por enquanto, só o `diagnostico`; `chat` e
`gate` chegam nas tarefas T11 e T12.

Roda da raiz do repositório: o `.env` e o `config/` são procurados a partir dela.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from agente.configuracao import CAMINHO_PADRAO, ErroConfiguracao, carregar_modelos
from agente.diagnostico import diagnosticar, formatar


def _diagnostico(args: argparse.Namespace) -> int:
    try:
        modelos = carregar_modelos(args.config)
    except ErroConfiguracao as erro:
        print(erro, file=sys.stderr)
        return 2
    if args.modelo:
        if args.modelo not in modelos:
            disponiveis = ", ".join(modelos)
            print(
                f"modelo desconhecido: {args.modelo} (há: {disponiveis})",
                file=sys.stderr,
            )
            return 2
        modelos = {args.modelo: modelos[args.modelo]}

    resultados = [diagnosticar(nome, cfg, os.environ) for nome, cfg in modelos.items()]
    print("\n".join(formatar(r) for r in resultados))
    return 0 if all(r.ok for r in resultados) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agente", description=__doc__.splitlines()[0])
    comandos = parser.add_subparsers(dest="comando", required=True)

    diagnostico = comandos.add_parser(
        "diagnostico", help="uma chamada com ferramenta a cada modelo configurado"
    )
    diagnostico.add_argument(
        "--modelo", help="só este modelo (nome em config/modelos.yaml)"
    )
    diagnostico.add_argument("--config", type=Path, default=CAMINHO_PADRAO)
    diagnostico.set_defaults(executar=_diagnostico)

    args = parser.parse_args(argv)
    # Variável já definida no ambiente vence o .env.
    load_dotenv(find_dotenv(usecwd=True), override=False)
    return args.executar(args)


if __name__ == "__main__":
    sys.exit(main())
