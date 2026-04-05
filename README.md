# Sistema MEG — Assistente Pessoal com IA Local

MEG é uma assistente pessoal de IA rodando 100% localmente via [Ollama](https://ollama.com/), com suporte a **voz**, **aprendizado de documentos** (PDF/DOCX/TXT), **pesquisa na web** e **memória persistente**.

---

## 🏛️ Arquitetura (Clean Architecture)

O projeto foi refatorado seguindo os princípios de **Clean Architecture** e **SOLID**, separando as responsabilidades em camadas bem definidas:

```
PROJETO-MEG/
│
├── main.py                        # Entry point único (GUI ou CLI via argparse)
│
├── meg/                           # Pacote principal da aplicação
│   ├── config.py                  # Constantes centralizadas (MODEL_NAME, caminhos, limites)
│   │
│   ├── domain/                    # Camada de Domínio — contratos de dados (TypedDicts)
│   │   └── memory_models.py       # MemoryEntry, UserMemory, KnowledgeEntry, ChatMessage
│   │
│   ├── application/               # Camada de Aplicação — casos de uso
│   │   ├── agent_service.py       # Loop ReAct do agente + montagem de prompt
│   │   ├── memory_service.py      # Leitura/escrita de todas as memórias
│   │   └── tool_executor.py       # Definição + execução das ferramentas (tools)
│   │
│   ├── infrastructure/            # Camada de Infraestrutura — IO e integrações
│   │   ├── json_repository.py     # load_json / save_json com tratamento de erro
│   │   └── modelfile_reader.py    # Extração do system prompt do Modelfile
│   │
│   └── presentation/              # Camada de Apresentação — interfaces
│       ├── cli.py                 # Interface de terminal
│       └── gui.py                 # Interface gráfica Tkinter (MegInterface)
│
├── megconfig/                     # Submódulo de Aprendizado Profundo
│   ├── core/
│   │   └── meg_brain.py           # Orquestrador de aprendizado + inferência via Ollama
│   ├── learning/
│   │   ├── book_learning.py       # Lê arquivos e quebra em chunks para extração
│   │   ├── knowledge_extractor.py # Usa Ollama para extrair JSON estruturado do texto
│   │   └── module_manager.py      # Cria e gerencia módulos de memória em disco
│   └── retrieval/
│       └── memory_search.py       # Busca por keyword nos arquivos knowledge.json
│
├── ArmazenamentoMemoria/          # Criado automaticamente pelo sistema
│   ├── memoria.json               # Histórico de interações (curto prazo)
│   ├── memoria_permanente.txt     # Log em texto de todas as perguntas
│   ├── conversa_sessao.txt        # Histórico da sessão atual
│   └── memoria_usuario.json       # Dados persistentes do usuário
│
├── megconfig/memory/              # Criado automaticamente pelo MegBrain
│   ├── memory_index.json
│   └── modules/<topico>/
│       └── knowledge.json
│
├── voz.py                         # Módulo de síntese (edge-tts) e reconhecimento (Whisper)
└── Modelfile                      # Personalidade e parâmetros do modelo Ollama
```

---

## 🚀 Como Rodar

### 1. Requisitos

```bash
# Dependências Python (Essenciais e Opcionais unidas no arquivo)
pip install -r requirements.txt
```

Certifique-se de que o modelo `meg` está criado no Ollama:

```bash
ollama create meg -f Modelfile
```

Ou, se preferir usar o modelo base sem personalidade:

```bash
ollama pull llama3
# e altere MODEL_NAME = "llama3" em meg/config.py
```

### 2. Executar

```bash
# Interface gráfica (padrão)
python main.py

# Interface de terminal
python main.py --cli
```

### 3. Aprender um documento via código

```python
from megconfig.core.meg_brain import MegBrain

brain = MegBrain()

# Aprende um arquivo (txt, pdf ou docx)
brain.learn(
    file_path="meu_documento.txt",
    module_name="ciencia_espacial",
    description="Fatos científicos sobre astronomia e estrelas",
)

# Pergunta usando a memória aprendida
resposta = brain.think_and_answer("O que dizem nossas memórias sobre buracos negros?")
print(resposta)
```

---

## 🔧 Ferramentas do Agente

| Ferramenta | Descrição |
|---|---|
| `pesquisar_web` | Busca no DuckDuckGo em tempo real |
| `ler_arquivo` | Lê arquivos locais de pastas autorizadas |
| `consultar_memoria_aprendida` | Busca nos módulos de conhecimento indexados |
| `abrir_navegador` | Abre o navegador padrão no Google |

---

## 📐 Decisões de Arquitetura

- **Por que `meg/config.py`?** Centraliza todas as constantes (`MODEL_NAME`, caminhos, limites). Antes estavam duplicadas em `meg.py` e `meg_brain.py` com valores diferentes.
- **Por que `TypedDict` no domínio?** Tipagem estática sem overhead de classes, compatível com `json.load()` nativamente.
- **Por que injeção de callback em `voz.py`?** Elimina o import circular `voz → meg`. O módulo de voz não sabe mais nada sobre o agente.
- **Por que `logger = logging.getLogger(__name__)`?** Logging nomeado por módulo permite filtrar logs por camada sem reconfigurar o handler global.
