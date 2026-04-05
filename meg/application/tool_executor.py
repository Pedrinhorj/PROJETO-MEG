"""
Aplicação — Executor de Ferramentas (tool_executor.py)

Define as ferramentas disponíveis para a MEG (TOOLS) e implementa
a função que as executa (executar_ferramenta).

Antes tudo isso estava no meio do meg.py misturado com memória e agente.

Cada ferramenta tem:
- Uma definição em TOOLS (schema para o Ollama entender)
- Um método privado de execução (_executar_X)
- Tratamento de erro explícito e sem bare excepts
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from meg.config import BASE_DIR, FILE_MAX_CHARS, PASTAS_PERMITIDAS, TOOL_MAX_RESULTS

logger = logging.getLogger(__name__)

# ── Schema das ferramentas (formato Ollama tool calling) ──────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "pesquisar_web",
            "description": "Realiza uma pesquisa na internet. Use quando precisar de informações atualizadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Pergunta ou termo para pesquisar"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ler_arquivo",
            "description": (
                "Lê o conteúdo completo de um arquivo de texto no computador do usuário. "
                "Use quando o usuário pedir para ler um arquivo, ver código, notas, logs, etc. "
                "Aceita caminho relativo ou absoluto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Caminho do arquivo (ex: 'documentos/notas.txt' ou '~/meu_arquivo.md')",
                    }
                },
                "required": ["caminho"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_memoria_aprendida",
            "description": (
                "Busca informações aprendidas de módulos, livros, PDFs ou DOCX na memória profunda. "
                "Use quando o usuário perguntar sobre conteúdo que você leu e indexou."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca, palavra-chave ou dúvida sobre o documento aprendido.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_navegador",
            "description": "Abre o navegador padrão na página do Google.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# Schema serializado para injetar no system prompt
FERRAMENTAS_JSON: str = json.dumps(
    [t["function"] for t in TOOLS],
    ensure_ascii=False,
    indent=2,
)


# ── Funções de execução (privadas por convenção) ───────────────────────────────

def _executar_pesquisar_web(args: dict) -> str:
    """Busca no DuckDuckGo sem rastreamento e retorna os top resultados."""
    query = args.get("query", "").strip()
    if not query:
        return "Erro: A ferramenta 'pesquisar_web' requer o parâmetro 'query'."

    try:
        max_results = int(args.get("max_results", TOOL_MAX_RESULTS))
    except (TypeError, ValueError):
        max_results = TOOL_MAX_RESULTS

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            resultados = ddgs.text(query, region="br-BR", max_results=max_results)

        if not resultados:
            return f"Nenhum resultado encontrado para '{query}'."

        return "\n\n".join(
            f"• {r['title']}\n{r['body'][:300]}...\nLink: {r['href']}"
            for r in resultados
        )
    except Exception as erro:
        logger.error("Erro na pesquisa web: %s", erro)
        return f"Erro ao realizar pesquisa: {erro}"


def _executar_ler_arquivo(args: dict) -> str:
    """Lê um arquivo local com restrições de segurança de diretório."""
    caminho_str = args.get("caminho", "").strip()
    if not caminho_str:
        return "Erro: A ferramenta 'ler_arquivo' requer o parâmetro 'caminho'."

    caminho = Path(caminho_str).expanduser().resolve()

    # Verificação de segurança: só permite pastas autorizadas
    if not any(
        _is_subpath(caminho, pasta.resolve())
        for pasta in PASTAS_PERMITIDAS
    ):
        return "Erro: Acesso negado. Só posso ler arquivos dentro das pastas permitidas."

    if not caminho.exists():
        return f"Erro: Arquivo não encontrado: {caminho}"

    if not caminho.is_file():
        return f"Erro: O caminho não aponta para um arquivo: {caminho}"

    try:
        conteudo = caminho.read_text(encoding="utf-8")
        if len(conteudo) > FILE_MAX_CHARS:
            conteudo = conteudo[:FILE_MAX_CHARS] + "\n\n... (arquivo muito grande, conteúdo truncado)"
        return f"Conteúdo de '{caminho.name}':\n\n{conteudo}"
    except OSError as erro:
        logger.error("Erro ao ler arquivo '%s': %s", caminho, erro)
        return f"Erro ao ler o arquivo: {erro}"


def _executar_consultar_memoria_aprendida(args: dict) -> str:
    """Consulta a memória de aprendizado profundo (megconfig)."""
    query = args.get("query", "").strip()
    if not query:
        return "Erro: A ferramenta 'consultar_memoria_aprendida' requer o parâmetro 'query'."

    try:
        from megconfig.retrieval.memory_search import search_memory

        resultados = search_memory(query)
        if not resultados:
            return f"Nenhuma informação encontrada na memória profunda sobre '{query}'."

        linhas = [f"Resultados na memória para '{query}':"]
        for res in resultados[:5]:
            modulo = res["module"]
            conhecimento = res["knowledge"]
            linhas.append(
                f"- [Módulo: {modulo}] {conhecimento.get('topic')}: "
                f"{conhecimento.get('summary')} "
                f"(Palavras-chave: {', '.join(conhecimento.get('keywords', []))}). "
                f"Detalhes: {conhecimento.get('details')}"
            )
        return "\n".join(linhas)

    except Exception as erro:
        logger.error("Erro ao consultar memória aprendida: %s", erro)
        return f"Erro ao consultar memória: {erro}"


def _executar_abrir_navegador(_args: dict) -> str:
    """Abre o navegador padrão no Google."""
    try:
        subprocess.Popen("xdg-open https://www.google.com", shell=True)
        return "Navegador aberto no Google."
    except Exception as erro:
        logger.error("Erro ao abrir navegador: %s", erro)
        return f"Erro ao abrir navegador: {erro}"


# ── Roteador principal ─────────────────────────────────────────────────────────

_FERRAMENTAS_DISPONIVEIS = {
    "pesquisar_web": _executar_pesquisar_web,
    "ler_arquivo": _executar_ler_arquivo,
    "consultar_memoria_aprendida": _executar_consultar_memoria_aprendida,
    "abrir_navegador": _executar_abrir_navegador,
}


def executar_ferramenta(tool_call: Any) -> str:
    """
    Normaliza e despacha uma chamada de ferramenta do agente.

    Aceita três formatos de entrada:
    - str: nome da ferramenta direto (formato texto/ReAct)
    - dict: {"function": {"name": ..., "arguments": ...}}
    - objeto: com atributos .function.name e .function.arguments
    """
    name, args = _normalizar_tool_call(tool_call)

    executor = _FERRAMENTAS_DISPONIVEIS.get(name)
    if executor is None:
        return f"Ferramenta '{name}' não implementada."

    try:
        return executor(args)
    except Exception as erro:
        logger.error("Erro inesperado ao executar '%s': %s", name, erro)
        return f"Erro ao executar '{name}': {erro}"


def _normalizar_tool_call(tool_call: Any) -> tuple[str, dict]:
    """
    Extrai (name, args) de qualquer formato de tool_call suportado.
    Retorna ('', {}) em caso de formato desconhecido.
    """
    if isinstance(tool_call, str):
        return tool_call.strip(), {}

    if isinstance(tool_call, dict):
        func = tool_call.get("function", tool_call)
        name = func.get("name", "")
        args = func.get("arguments", {})
    else:
        func = getattr(tool_call, "function", tool_call)
        name = getattr(func, "name", "")
        args = getattr(func, "arguments", {})

    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}

    return name, args


def _is_subpath(path: Path, parent: Path) -> bool:
    """Verifica se `path` está dentro de `parent` de forma segura."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
