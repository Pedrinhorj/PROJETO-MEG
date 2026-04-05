"""
Constantes e configurações centralizadas do sistema MEG.

Por que centralizar aqui?
- Evita múltiplos "pontos da verdade" espalhados nos módulos.
- Facilita troca de modelo ou caminhos sem caçar todos os arquivos.
"""
from pathlib import Path

# --- Diretórios base ---
BASE_DIR: Path = Path(__file__).resolve().parent.parent
ARMAZENAMENTO_DIR: Path = BASE_DIR / "ArmazenamentoMemoria"

# --- Arquivos de memória ---
MEMORIA_JSON: Path = ARMAZENAMENTO_DIR / "memoria.json"
MEMORIA_PERMANENTE: Path = ARMAZENAMENTO_DIR / "memoria_permanente.txt"
MEMORIA_SESSAO: Path = ARMAZENAMENTO_DIR / "conversa_sessao.txt"
MEMORIA_USUARIO_JSON: Path = ARMAZENAMENTO_DIR / "memoria_usuario.json"

# --- Modelo Ollama ---
# "meg" é o modelo personalizado criado via Modelfile (ollama create meg -f Modelfile).
# Use "llama3" apenas se quiser o modelo base sem personalidade.
MODEL_NAME: str = "meg"

# --- Segurança: pastas permitidas para leitura de arquivos ---
PASTAS_PERMITIDAS: list[Path] = [
    BASE_DIR,
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]

# --- Limites do agente ---
AGENT_MAX_LOOPS: int = 10
TOOL_MAX_RESULTS: int = 5
FILE_MAX_CHARS: int = 15_000
KNOWLEDGE_EXTRACTOR_MAX_CHARS: int = 3_000
