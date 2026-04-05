"""
main.py — Entry point único do sistema MEG.

Uso:
    python main.py          → Abre a interface gráfica (padrão)
    python main.py --cli    → Abre a interface de terminal
"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MEG — Assistente Pessoal com IA Local"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Inicia a MEG no modo terminal (sem interface gráfica)",
    )
    args = parser.parse_args()

    if args.cli:
        from meg.presentation.cli import main as cli_main
        cli_main()
    else:
        from meg.presentation.gui import MegInterface
        MegInterface()


if __name__ == "__main__":
    main()
