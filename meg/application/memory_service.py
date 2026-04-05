"""
Aplicação — Serviço de Memória (memory_service.py)

Centraliza toda a lógica de leitura e escrita de memória da MEG,
antes espalhada em funções soltas no meg.py.

Responsabilidades:
- Memória de conversa (curto prazo → JSON)
- Memória permanente (log de perguntas → .txt)
- Memória de sessão (histórico da sessão atual → .txt)
- Memória do usuário (dados persistentes → JSON)
- Extração e aplicação de comandos de memória emitidos pelo modelo
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from meg.config import (
    ARMAZENAMENTO_DIR,
    MEMORIA_JSON,
    MEMORIA_PERMANENTE,
    MEMORIA_SESSAO,
    MEMORIA_USUARIO_JSON,
)
from meg.domain.memory_models import MemoryEntry, MemoryCommand, UserMemory
from meg.infrastructure.json_repository import load_json, save_json

logger = logging.getLogger(__name__)


# ── Memória de Conversa (curto prazo) ─────────────────────────────────────────

def salvar_memoria(nova_entrada: MemoryEntry) -> None:
    """Adiciona uma nova entrada ao histórico de memória geral."""
    memorias: list = load_json(MEMORIA_JSON)  # type: ignore[assignment]
    memorias.append(nova_entrada)
    save_json(MEMORIA_JSON, memorias)


# ── Memória Permanente (log em texto) ─────────────────────────────────────────

def caca_informacoes(pergunta: str) -> None:
    """
    Persiste a pergunta do usuário tanto no JSON de memória quanto
    no arquivo de log permanente em texto plano.

    Nome mantido do original para compatibilidade interna.
    """
    trecho = pergunta.strip()
    if not trecho:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    salvar_memoria(MemoryEntry(data=timestamp, conteudo=trecho, tags=[]))

    MEMORIA_PERMANENTE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with MEMORIA_PERMANENTE.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"[{timestamp}] {trecho}\n")
    except OSError as erro:
        logger.error("Erro ao escrever memória permanente: %s", erro)


def carregar_memoria_permanente() -> str:
    """Retorna o conteúdo completo do log de memória permanente."""
    if not MEMORIA_PERMANENTE.exists():
        return ""
    try:
        return MEMORIA_PERMANENTE.read_text(encoding="utf-8")
    except OSError as erro:
        logger.error("Erro ao ler memória permanente: %s", erro)
        return ""


# ── Memória de Sessão ──────────────────────────────────────────────────────────

def salvar_memoria_sessao(conteudo: str) -> None:
    """Persiste o histórico completo da sessão atual em disco."""
    MEMORIA_SESSAO.parent.mkdir(parents=True, exist_ok=True)
    try:
        MEMORIA_SESSAO.write_text(conteudo, encoding="utf-8")
    except OSError as erro:
        logger.error("Erro ao salvar memória de sessão: %s", erro)


# ── Memória do Usuário (dados persistentes) ────────────────────────────────────

def carregar_memoria_usuario() -> UserMemory:
    """Carrega o dicionário de dados persistentes do usuário."""
    if not MEMORIA_USUARIO_JSON.exists():
        return {}  # type: ignore[return-value]
    data = load_json(MEMORIA_USUARIO_JSON)
    return data if isinstance(data, dict) else {}  # type: ignore[return-value]


def salvar_memoria_usuario(memoria: UserMemory) -> None:
    """Persiste o dicionário de dados do usuário em disco."""
    ARMAZENAMENTO_DIR.mkdir(parents=True, exist_ok=True)
    save_json(MEMORIA_USUARIO_JSON, memoria)


def atualizar_memoria(
    memoria: UserMemory,
    comando: Optional[MemoryCommand],
) -> UserMemory:
    """
    Aplica um comando de atualização de memória na estrutura do usuário.

    Ações suportadas:
    - "atualizar": substitui o valor do campo.
    - "adicionar": acrescenta o valor a uma lista existente no campo.
    """
    if not comando:
        return memoria

    acao = comando.get("acao")
    campo = comando.get("campo")
    valor = comando.get("valor")

    if not campo:
        return memoria

    if acao == "atualizar":
        memoria[campo] = valor  # type: ignore[literal-required]
    elif acao == "adicionar":
        if campo not in memoria:
            memoria[campo] = []  # type: ignore[literal-required]
        lista = memoria.get(campo)  # type: ignore[literal-required]
        if isinstance(lista, list):
            lista.append(valor)

    return memoria


def extrair_memoria(texto: str) -> Optional[MemoryCommand]:
    """
    Extrai um comando de memória embutido na resposta do modelo.

    O modelo pode emitir ao final da resposta:
        MEMORIA: {"acao": "atualizar", "campo": "nome", "valor": "Pedro"}

    Retorna None se nenhum comando for encontrado ou o JSON for inválido.
    """
    import json

    if "MEMORIA:" not in texto:
        return None
    try:
        parte = texto.split("MEMORIA:", 1)[1].strip()
        return json.loads(parte.splitlines()[0])
    except (json.JSONDecodeError, IndexError) as erro:
        logger.warning("Falha ao extrair comando de memória do texto: %s", erro)
        return None
