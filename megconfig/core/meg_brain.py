import logging

import ollama

from megconfig.learning.book_learning import learn_from_file
from megconfig.learning.module_manager import create_module
from megconfig.retrieval.memory_search import search_memory
from meg.config import MODEL_NAME

logger = logging.getLogger(__name__)

class MegBrain:
    """
    Core Controller: orquestra a inteligência, memória e busca da MEG AI,
    conectando perfeitamente o aprendizado aos motores de inferência em Llama 3 local.
    """
    def __init__(self) -> None:
        logger.info("MEG Brain Boot Sequence Started.")
        
    def create_memory_module(self, name: str, description: str) -> None:
        create_module(name, description)
        
    def learn(self, file_path: str, module_name: str, description: str = "") -> None:
        """Gatilho principal para leitura de textos ou pdfs."""
        logger.info("Brain: Iniciando ingestão do arquivo '%s' no módulo '%s'", file_path, module_name)
        learn_from_file(file_path, module_name, description)
        
    def think_and_answer(self, question: str) -> str:
        """
        Consulta a memória local, busca relevância semântica e contextual antes de
        elaborar e sintetizar respostas precisas via modelo de linguagem.
        """
        logger.info("Brain processando query de inferência: '%s'", question)
        
        # Estratégia simples de bag of words
        words = question.lower().split()
        relevant_knowledge = []
        
        # Busca sobre contextos fortes (descartando determinantes curtos da lingua)
        for word in words:
            if len(word) > 3:
                res = search_memory(word)
                for r in res:
                    if r not in relevant_knowledge:
                        relevant_knowledge.append(r)
                        
        context_text = ""
        if relevant_knowledge:
            logger.info("Recuperador retornou %d blocos de contexto relevantes.", len(relevant_knowledge))
            context_text = "As seguintes memórias em formato estruturado podem ajudar a formar a sua resposta de forma fiel e embasada:\n\n"
            
            # Limite rígido (Top 3) de injeção de prompt no Llama para não superar a Context Window
            for i, item in enumerate(relevant_knowledge[:3]):
                k = item['knowledge']
                context_text += f"=== MÓDULO: {item['module']} ===\n"
                context_text += f"- Tópico: {k.get('topic', '')}\n"
                context_text += f"- Resumo: {k.get('summary', '')}\n"
                context_text += f"- Detalhes Específicos: {k.get('details', '')}\n\n"
            
            context_text += "Instrução ao Cérebro: Priorize informações da memória fornecida.\n"
        else:
            logger.info("Nenhum contexto encontrado na memória. Usando general knowledge do modelo.")
            
        prompt = f"{context_text}\nDe modo amigável e informativo, responda:\n{question}"
        
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}]
            )
            if isinstance(response, dict):
                return response.get("message", {}).get("content", "")
            return getattr(getattr(response, "message", {}), "content", "")
        except Exception as e:
            logger.error("Engine de geração não respondeu: %s", e)
            return "Estou com problemas para pensar no momento devido a uma falha local do modelo."

if __name__ == "__main__":
    # Inicialização Padrão
    brain = MegBrain()
    print("MEG Architecture OK. Use 'brain.learn(...)' ou 'brain.think_and_answer(...)'.")
