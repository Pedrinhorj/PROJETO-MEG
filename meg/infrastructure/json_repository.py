"""
Infraestrutura — Repositório JSON (json_repository.py)

Funções puras de leitura e escrita de arquivos JSON.
Toda a lógica que antes estava em meg.py (load_json / save_json).

Por que isolar aqui?
- Um único lugar para tratar erros de IO de JSON.
- Fácil de mockar em testes unitários.
- Nenhuma camada superior precisa conhecer encoding ou indent.
"""
import json
import logging
from pathlib import Path
from typing import Any, Union

logger = logging.getLogger(__name__)


def load_json(path: Path) -> Union[list, dict]:
    """
    Lê um arquivo JSON e retorna seu conteúdo.

    Retorna [] se o arquivo não existir ou estiver corrompido,
    garantindo que o chamador sempre recebe um tipo iterável.
    """
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as arquivo:
            data = json.load(arquivo)
            return data if isinstance(data, (list, dict)) else []
    except json.JSONDecodeError as erro:
        logger.warning("Arquivo JSON corrompido em '%s': %s", path, erro)
        return []
    except OSError as erro:
        logger.error("Erro ao abrir '%s': %s", path, erro)
        return []


def save_json(path: Path, data: Any) -> bool:
    """
    Salva dados em um arquivo JSON, criando diretórios pai se necessário.

    Retorna True se bem-sucedido, False em caso de erro.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as arquivo:
            json.dump(data, arquivo, ensure_ascii=False, indent=2)
        return True
    except OSError as erro:
        logger.error("Erro ao salvar JSON em '%s': %s", path, erro)
        return False
