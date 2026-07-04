# run_meg.py — Ponto de entrada da MEG (usado pelo PyInstaller e direto pelo Python)
import sys
import os
from pathlib import Path

# ── Ajuste de path para execução via PyInstaller (sys._MEIPASS) ou direto ──
if getattr(sys, 'frozen', False):
    # Rodando como .exe compilado pelo PyInstaller
    BASE = Path(sys._MEIPASS)
else:
    # Rodando direto via `python run_meg.py`
    BASE = Path(__file__).resolve().parent

# Garante que o diretório do projeto está no sys.path
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# Muda o diretório de trabalho para a pasta do executável
# (importante para caminhos relativos como ArmazenamentoMemoria/)
os.chdir(BASE)

from interface import MegInterface

if __name__ == "__main__":
    MegInterface()