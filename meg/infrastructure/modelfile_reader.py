"""
Infraestrutura — Leitor do Modelfile (modelfile_reader.py)

Isola a leitura do Modelfile para extrair o system prompt da MEG.
Antes estava diretamente no meg.py junto com toda a lógica do agente.

Por que isolar?
- O Modelfile é uma dependência de infraestrutura (arquivo em disco).
- Facilita mocks em testes sem precisar de arquivo real.
- Deixa o agent_service focado apenas na lógica de prompt.
"""
import logging
from pathlib import Path

from meg.config import BASE_DIR

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_PADRAO = "Você é a Meg, assistente inteligente."


def carregar_regras_modelfile() -> str:
    """
    Lê o Modelfile e extrai o conteúdo da diretiva SYSTEM.

    Suporta dois formatos:
    - SYSTEM \"\"\"...\"\"\"  (multiline)
    - SYSTEM \"...\"       (single line)

    Retorna o prompt padrão se o arquivo não existir ou o parse falhar.
    """
    caminho: Path = BASE_DIR / "Modelfile"

    if not caminho.exists():
        logger.warning("Modelfile não encontrado em '%s'. Usando prompt padrão.", caminho)
        return _SYSTEM_PROMPT_PADRAO

    try:
        conteudo = caminho.read_text(encoding="utf-8")

        if 'SYSTEM """' in conteudo:
            return conteudo.split('SYSTEM """')[1].split('"""')[0].strip()

        if 'SYSTEM "' in conteudo:
            return conteudo.split('SYSTEM "')[1].split('"')[0].strip()

        logger.warning("Diretiva SYSTEM não encontrada no Modelfile. Usando prompt padrão.")
        return _SYSTEM_PROMPT_PADRAO

    except OSError as erro:
        logger.error("Erro ao ler Modelfile: %s", erro)
        return _SYSTEM_PROMPT_PADRAO
