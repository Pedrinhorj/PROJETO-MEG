"""
Apresentação — Interface de Terminal (cli.py)

Loop principal da MEG via linha de comando.
Esta camada não contém nenhuma lógica de domínio — apenas orquestra
os serviços da camada de aplicação e cuida de IO com o usuário.
"""
import logging
import threading
from typing import Optional

from meg.application.agent_service import montar_mensagens, obter_resposta_ollama
from meg.application.memory_service import (
    atualizar_memoria,
    caca_informacoes,
    carregar_memoria_permanente,
    carregar_memoria_usuario,
    extrair_memoria,
    salvar_memoria_sessao,
    salvar_memoria_usuario,
)
from meg.domain.memory_models import ChatMessage, UserMemory

logger = logging.getLogger(__name__)


def _inicializar_voz() -> Optional[object]:
    """
    Tenta importar o módulo de voz opcionalmente.
    Retorna o módulo se disponível, None caso contrário.
    """
    try:
        import voz
        return voz
    except ImportError as erro:
        logger.warning("Módulo de voz não disponível: %s. Continuando sem voz.", erro)
        return None


def main() -> None:
    """
    Entry point da interface de terminal da MEG.

    Inicializa memória, histórico e loop de interação.
    O agente ReAct é executado dentro de obter_resposta_ollama.
    """
    voz = _inicializar_voz()
    print("Meg está online. Digite 'sair' para encerrar.\n")

    if voz:
        threading.Thread(
            target=voz.falar,
            args=("Meg online. Olá, Pedro Arthur!",),
            daemon=True,
        ).start()

    historico: list[ChatMessage] = []
    memoria_usuario: UserMemory = carregar_memoria_usuario()

    while True:
        try:
            pergunta = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if pergunta.lower() == "sair":
            print("Encerrando...")
            break

        if not pergunta:
            continue

        # Persiste a pergunta na memória permanente
        caca_informacoes(pergunta)

        # Monta o payload com todo o contexto e executa o agente
        memoria_permanente = carregar_memoria_permanente()
        mensagens = montar_mensagens(pergunta, historico, memoria_permanente)
        resposta = obter_resposta_ollama(mensagens)

        print(f"\nMeg: {resposta}\n")

        if voz:
            threading.Thread(
                target=voz.falar,
                args=(resposta,),
                daemon=True,
            ).start()

        # Atualiza histórico da sessão
        historico.append({"role": "user", "content": pergunta})
        historico.append({"role": "assistant", "content": resposta})

        salvar_memoria_sessao(
            "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in historico)
        )

        # Aplica comandos de memória emitidos pelo modelo (se houver)
        comando_memoria = extrair_memoria(resposta)
        if comando_memoria:
            memoria_usuario = atualizar_memoria(memoria_usuario, comando_memoria)
            salvar_memoria_usuario(memoria_usuario)
