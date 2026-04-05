"""
Camada de Domínio — Modelos de Dados (memory_models.py)

Define os TypedDicts que representam as estruturas de dados
do sistema MEG. Sem lógica, sem IO — apenas os contratos de dados.

Por que TypedDict?
- Tipagem estática para dicts sem precisar de classes pesadas.
- Compatível com json.load() sem serialização extra.
- Permite type checkers (mypy, Pylance) validarem os acessos.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class MemoryEntry(TypedDict):
    """Uma entrada de memória de conversa (curto prazo)."""
    data: str        # ISO timestamp
    conteudo: str    # Texto da pergunta/interação
    tags: list[str]  # Tags para busca futura


class UserMemory(TypedDict, total=False):
    """
    Dicionário de memória persistente do usuário.
    `total=False` pois os campos são dinâmicos e opcionais.
    """
    nome: str
    preferencias: list[str]
    projetos: list[str]


class KnowledgeEntry(TypedDict):
    """
    Um bloco de conhecimento extraído de documento (megconfig).
    Produzido pelo knowledge_extractor e salvo nos módulos.
    """
    topic: str
    summary: str
    details: str
    keywords: list[str]


class ChatMessage(TypedDict):
    """Uma mensagem de histórico de chat para o Ollama."""
    role: str     # "user" | "assistant" | "system"
    content: str


class MemoryCommand(TypedDict, total=False):
    """
    Comando de atualização de memória embutido na resposta do modelo.
    O modelo pode emitir: MEMORIA: {"acao": "atualizar", "campo": "nome", "valor": "Pedro"}
    """
    acao: str    # "atualizar" | "adicionar"
    campo: str
    valor: Any
