import json
import logging
import ollama

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Limite de segurança de caracteres por requisição
MAX_TEXT_LENGTH = 3000

def extract_knowledge(text: str) -> dict:
    """
    Sends text to Llama 3 via Ollama to extract structured knowledge.
    Returns a dictionary or None if invalid.
    """
    if len(text) > MAX_TEXT_LENGTH:
        logging.warning(f"Texto muito longo ({len(text)} chars). Truncando para evitar payload extenso.")
        text = text[:MAX_TEXT_LENGTH]

    prompt = f"""
Extraia o conhecimento do texto abaixo e retorne APENAS um objeto JSON válido.
Nenhum texto adicional, nenhuma formatação Markdown, apenas o JSON.
O JSON DEVE ESTAR no seguinte formato exato de chaves:
{{
    "topic": "o tema central",
    "summary": "resumo do conteúdo",
    "details": "informações importantes extraídas",
    "keywords": ["palavra1", "palavra2"]
}}

Texto:
{text}
"""
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )
        
        output = response.get('message', {}).get('content', '').strip()
        
        # Parse robusto de colchetes JSON pelo LLM
        start_idx = output.find('{')
        end_idx = output.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            output = output[start_idx:end_idx+1]
        
        # Validar JSON
        try:
            knowledge = json.loads(output)
        except json.JSONDecodeError as e:
            logging.error(f"Falha ao decodificar JSON do Ollama: {e}")
            logging.debug(f"Retorno do modelo (truncado): {output[:200]}")
            return None
        
        required_keys = {"topic", "summary", "details", "keywords"}
        if not required_keys.issubset(knowledge.keys()):
            logging.error("O JSON extraído não contém todas as chaves obrigatórias.")
            return None
            
        if not isinstance(knowledge["keywords"], list):
            knowledge["keywords"] = [str(k) for k in knowledge["keywords"]]
            
        return knowledge
        
    except Exception as e:
        logging.error(f"Erro durante a extração geral no ollama: {e}")
        return None
