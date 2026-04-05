import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base Directory calculations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, 'memory')
MODULES_DIR = os.path.join(MEMORY_DIR, 'modules')
INDEX_FILE = os.path.join(MEMORY_DIR, 'memory_index.json')

def ensure_structure():
    """Ensure the memory directories and index file exist."""
    try:
        os.makedirs(MODULES_DIR, exist_ok=True)
        if not os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                json.dump({"modules": []}, f, indent=4)
    except Exception as e:
        logging.error(f"Erro ao criar estrutura de diretórios: {e}")

def create_module(name: str, description: str) -> bool:
    """Creates a new memory module."""
    ensure_structure()
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for mod in data.get('modules', []):
            if mod['name'] == name:
                logging.info(f"Módulo '{name}' já existe.")
                return False
                
        data['modules'].append({"name": name, "description": description})
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        mod_dir = os.path.join(MODULES_DIR, name)
        os.makedirs(mod_dir, exist_ok=True)
        knowledge_file = os.path.join(mod_dir, 'knowledge.json')
        
        if not os.path.exists(knowledge_file):
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)
                
        logging.info(f"Módulo '{name}' criado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro ao criar módulo '{name}': {e}")
        return False

def save_knowledge(module_name: str, knowledge_data: dict) -> bool:
    """Saves validated knowledge into a specific module."""
    ensure_structure()
    knowledge_file = os.path.join(MODULES_DIR, module_name, 'knowledge.json')
    
    if not os.path.exists(knowledge_file):
        logging.error(f"Módulo '{module_name}' não existe. Crie-o primeiro.")
        return False
        
    try:
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
    except json.JSONDecodeError:
        current_data = []
        
    current_data.append(knowledge_data)
    
    try:
        with open(knowledge_file, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar conhecimento: {e}")
        return False
