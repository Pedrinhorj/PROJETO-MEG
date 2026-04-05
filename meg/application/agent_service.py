"""
Aplicação — Serviço do Agente (agent_service.py)

Responsável por:
1. Montar o payload de mensagens para o Ollama (system prompt + histórico)
2. Executar o loop ReAct do agente (Reason + Act) com suporte a ferramentas

Antes toda essa lógica estava no meg.py junto com memória e UI.
Agora é uma unidade coesa e testável.
"""
import logging
from typing import Optional

import ollama

from meg.config import AGENT_MAX_LOOPS, MODEL_NAME
from meg.application.tool_executor import FERRAMENTAS_JSON, executar_ferramenta
from meg.domain.memory_models import ChatMessage
from meg.infrastructure.modelfile_reader import carregar_regras_modelfile

logger = logging.getLogger(__name__)


def montar_mensagens(
    pergunta: str,
    historico: list[ChatMessage],
    memoria_permanente: str = "",
) -> list[ChatMessage]:
    """
    Monta a lista de mensagens para enviar ao Ollama.

    Ordem:
    1. System prompt (personalidade do Modelfile + ferramentas disponíveis + memória)
    2. Histórico da sessão
    3. Mensagem atual do usuário

    Args:
        pergunta: A pergunta atual do usuário.
        historico: Lista de mensagens anteriores da sessão.
        memoria_permanente: Conteúdo do log de memória permanente.
    """
    personalidade = carregar_regras_modelfile()
    mem_contexto = memoria_permanente or "Nenhuma informação aprendida ainda."

    system_prompt = (
        f"{personalidade}\n\n"
        "------ INSTRUÇÕES DE SISTEMA EXTRAS E FERRAMENTAS ------\n"
        "VOCÊ PODE INTERAGIR COM FERRAMENTAS PARA ACESSAR DADOS EXTERNOS. Seja autônoma:\n"
        "1. Pense passo a passo.\n"
        "2. Use ferramentas se não souber de algo de imediato!\n\n"
        f"FERRAMENTAS DISPONÍVEIS:\n{FERRAMENTAS_JSON}\n\n"
        "[MEMÓRIA PERMANENTE ATIVA]:\n"
        f"{mem_contexto}"
    )

    mensagens: list[ChatMessage] = [{"role": "system", "content": system_prompt}]
    mensagens.extend(historico)
    mensagens.append({"role": "user", "content": pergunta})
    return mensagens


def obter_resposta_ollama(mensagens: list[ChatMessage]) -> str:
    """
    Executa o loop ReAct do agente com suporte a chamadas de ferramentas.

    Fluxo por iteração:
    1. Chama o Ollama com as mensagens atuais.
    2. Se a resposta tiver tool_calls nativos → executa e continua o loop.
    3. Se o texto tiver marcador AÇÃO:/ACAO: → executa ferramenta (fallback ReAct).
    4. Se nenhum dos acima → retorna o texto como resposta final.

    Interrompe após AGENT_MAX_LOOPS iterações para evitar loops infinitos.
    """
    for loop_count in range(1, AGENT_MAX_LOOPS + 1):
        logger.debug("Loop do agente — iteração %d/%d", loop_count, AGENT_MAX_LOOPS)

        try:
            response = ollama.chat(model=MODEL_NAME, messages=mensagens)
        except Exception as erro:
            logger.error("Erro de comunicação com Ollama: %s", erro)
            return f"Erro de comunicação com o modelo: {erro}"

        mensagem = _normalizar_resposta(response)
        texto: str = mensagem.get("content") or ""

        # --- Caminho 1: Tool calling nativo do Ollama ---
        if mensagem.get("tool_calls"):
            mensagens = _processar_tool_calls_nativos(mensagens, mensagem)
            continue

        # --- Caminho 2: Tool calling baseado em texto (ReAct fallback) ---
        if "AÇÃO:" in texto.upper() or "ACAO:" in texto.upper():
            mensagens = _processar_tool_call_texto(mensagens, mensagem, texto)
            continue

        # --- Caminho 3: Resposta final ---
        return texto

    logger.warning("Loop do agente interrompido após %d iterações.", AGENT_MAX_LOOPS)
    return "Erro interno: muitas chamadas de ferramentas consecutivas sem resposta final."


# ── Helpers privados ───────────────────────────────────────────────────────────

def _normalizar_resposta(response: object) -> dict:
    """
    Normaliza a resposta do Ollama para sempre ser um dict.
    A lib pode retornar objeto ou dict dependendo da versão.
    """
    raw_msg = (
        response.get("message")
        if isinstance(response, dict)
        else getattr(response, "message", {})
    )

    if isinstance(raw_msg, dict):
        return raw_msg

    return {
        "content": getattr(raw_msg, "content", "") or "",
        "tool_calls": getattr(raw_msg, "tool_calls", None),
        "role": getattr(raw_msg, "role", "assistant"),
    }


def _processar_tool_calls_nativos(
    mensagens: list[ChatMessage],
    mensagem: dict,
) -> list[ChatMessage]:
    """Executa tool_calls nativos e adiciona os resultados ao histórico."""
    resultados = []
    for tool_call in mensagem.get("tool_calls", []):
        resultado = executar_ferramenta(tool_call)

        if isinstance(tool_call, dict):
            func = tool_call.get("function", tool_call)
            nome = func.get("name", "desconhecida")
        else:
            func = getattr(tool_call, "function", tool_call)
            nome = getattr(func, "name", "desconhecida")

        logger.info("🔧 MEG usou (nativo): %s", nome)
        resultados.append({
            "role": "user",
            "content": f"[SYSTEM - Resultado de {nome}]:\n{resultado}",
        })

    mensagens.append(mensagem)
    mensagens.extend(resultados)
    return mensagens


def _processar_tool_call_texto(
    mensagens: list[ChatMessage],
    mensagem: dict,
    texto: str,
) -> list[ChatMessage]:
    """Executa tool call baseado em texto (padrão ReAct) e adiciona ao histórico."""
    marcador = "AÇÃO:" if "AÇÃO:" in texto else "ACAO:"
    cmd = texto.split(marcador, 1)[1].strip()
    resultado = executar_ferramenta(cmd)
    nome = cmd.split()[0] if cmd else "desconhecida"

    logger.info("🔧 MEG usou (texto): %s", nome)
    mensagens.append(mensagem)
    mensagens.append({
        "role": "user",
        "content": f"[SYSTEM - Resultado de {nome}]:\n{resultado}",
    })
    return mensagens
