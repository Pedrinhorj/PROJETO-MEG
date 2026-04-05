import os
import logging
from .knowledge_extractor import extract_knowledge
from .module_manager import save_knowledge, create_module

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def split_text(text: str, chunk_size: int = 2500) -> list:
    """Splits a long text into smaller chunks for processing."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def learn_from_file(file_path: str, module_name: str, module_desc: str = ""):
    """
    Reads a file (txt/pdf), extracts knowledge in chunks, and saves to a module.
    """
    if not os.path.exists(file_path):
        logging.error(f"Arquivo não encontrado: {file_path}")
        return
        
    text = ""
    # Extract text according to format
    if file_path.lower().endswith('.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            logging.error(f"Erro ao ler arquivo tx: {e}")
            return
    elif file_path.lower().endswith('.pdf'):
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except ImportError:
            logging.error("Biblioteca PyPDF2 não está instalada. Para ler PDFs, execute: pip install PyPDF2")
            return
        except Exception as e:
            logging.error(f"Erro ao ler pdf: {e}")
            return
    else:
        logging.error("Formato de arquivo não suportado. Favor usar .txt ou .pdf.")
        return

    if not text.strip():
        logging.warning("Arquivo está vazio ou texto não pôde ser extraído.")
        return

    # Garante que o módulo e as pastas existem
    create_module(module_name, module_desc)
    
    chunks = split_text(text, chunk_size=2500)
    logging.info(f"Documento dividido em {len(chunks)} trechos de aprendizado.")
    
    for i, chunk in enumerate(chunks):
        logging.info(f"Extraindo conhecimento do trecho {i+1}/{len(chunks)}...")
        knowledge = extract_knowledge(chunk)
        if knowledge:
            success = save_knowledge(module_name, knowledge)
            if success:
                logging.info(f"Conhecimento do trecho {i+1} salvo com sucesso.")
        else:
            logging.warning(f"Falha ao processar e extrair JSON válido do trecho {i+1}.")
            
    logging.info("Rotina de aprendizado a partir do arquivo finalizada!")
