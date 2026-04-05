import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, 'memory')
MODULES_DIR = os.path.join(MEMORY_DIR, 'modules')

def search_memory(query: str) -> list:
    """
    Searches for a query/keywords inside all memory modules.
    Returns a list of matching knowledge blocks dynamically.
    """
    query_lower = query.lower()
    results = []
    
    if not os.path.exists(MODULES_DIR):
        logging.info("Nenhuma base de memória alocada localmente.")
        return results
        
    for module_name in os.listdir(MODULES_DIR):
        knowledge_file = os.path.join(MODULES_DIR, module_name, 'knowledge.json')
        if not os.path.exists(knowledge_file):
            continue
            
        try:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                knowledge_list = json.load(f)
        except json.JSONDecodeError:
            logging.debug(f"Aviso: O módulo {module_name} aparentemente está corrompido ou vazio.")
            continue
        except Exception as e:
            logging.debug(f"Erro ao acesar módulo {module_name}: {e}")
            continue
                
        for entry in knowledge_list:
            # Matches based on structured keys
            keywords = [str(k).lower() for k in entry.get('keywords', [])]
            topic = str(entry.get('topic', '')).lower()
            summary = str(entry.get('summary', '')).lower()
            details = str(entry.get('details', '')).lower()
            
            # Simple soft keyword / phrase matching over internal memory representation
            if (query_lower in keywords or 
                query_lower in topic or 
                query_lower in summary or
                query_lower in details or
                any(query_lower in k for k in keywords)):
                
                results.append({
                    "module": module_name,
                    "knowledge": entry
                })
                
    return results
