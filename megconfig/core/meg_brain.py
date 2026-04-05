import os
import sys
import logging

# Permite importações a partir da raiz do módulo 'meg'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meg.learning.book_learning import learn_from_file
from meg.learning.module_manager import create_module
from meg.retrieval.memory_search import search_memory
import ollama

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MegBrain:
    """
    Core Controller: orquestra a inteligência, memória e busca da MEG AI,
    conectando perfeitamente o aprendizado aos motores de inferência em Llama 3 local.
    """
    def __init__(self):
        logging.info("MEG Brain Boot Sequence Started.")
        
    def create_memory_module(self, name: str, description: str):
        create_module(name, description)
        
    def learn(self, file_path: str, module_name: str, description: str = ""):
        """Gatilho principal para leitura de textos ou pdfs."""
        logging.info(f"Brain: Iniciando ingestão do arquivo: {file_path} no módulo {module_name}")
        learn_from_file(file_path, module_name, description)
        
    def think_and_answer(self, question: str) -> str:
        """
        Consulta a memória local, busca relevância semântica e contextual antes de
        elaborar e sintetizar respostas precisas via modelo de linguagem.
        """
        logging.info(f"Brain processando query de inferência: '{question}'")
        
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
            logging.info(f"O modelo de recuperação retornou {len(relevant_knowledge)} blocos de contexto relevantes do JSON.")
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
            logging.info("Recuperador falhou ou query não abrangeu conhecimento. Atuando via general knowledge weight do Llama 3.")
            
        prompt = f"{context_text}\nDe modo amigável e informativo, responda:\n{question}"
        
        try:
            response = ollama.chat(
                model="llama3",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.get('message', {}).get('content', '')
        except Exception as e:
            logging.error(f"Engine de Geração não respondeu. Exceção do Ollama: {e}")
            return "Estou com problemas para pensar no momento devido a uma falha local do modelo."

if __name__ == "__main__":
    # Inicialização Padrão
    brain = MegBrain()
    print("MEG Architecture OK. Use 'brain.learn(...)' ou 'brain.think_and_answer(...)'.")
