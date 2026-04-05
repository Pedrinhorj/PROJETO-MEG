# Sistema de Aprendizado e Memória Modular - Projeto MEG

Este módulo permite que a inteligência da MEG leia arquivos de texto (PDF/TXT), entenda o conteúdo fracionado, extraia conhecimento valioso na forma de arquivos padronizados JSON usando a capacidade do `Llama 3` via Ollama, e recupere esse mesmo conteúdo em inferências futuras de maneira segura (sem que o modelo tenha controle autônomo e de baixo nível ao Storage).

---

## 📂 Visão Geral e Estrutura dos Arquivos

Foi elaborada a seguinte arquitetura gerada para você:

```text
meg/
│
├── core/
│   └── meg_brain.py             # Instância do "Cérebro" unificador. Conecta extração e consulta via API.
│
├── learning/
│   ├── book_learning.py         # Módulo injetor que quebra arquivos em "chunks" suportados.
│   ├── knowledge_extractor.py   # Usa engenharia de prompt restritivo para criar um output em JSON nativo no Llama 3.
│   └── module_manager.py        # Garante a escrita e estrutura de diretórios e validade no Storage interno.
│
├── memory/                      # Automagicamente criado. Armazém que segura JSON's blindados de deleções aleatórias pelo modelo.
│   ├── memory_index.json
│   └── modules/
│
└── retrieval/
    └── memory_search.py         # Motor focado em NLP local e Keyword match no dataset de JSON's.
```

### Explicação Rápida:
* **`module_manager.py`**: Interage com o sistema de arquivos para criar novas "pastas de tópicos" (`memory_index` e `modules/xyz/knowledge.json`). Assegura que todas as operações sejam feitas apenas pelo sub-sistema Python nativo (blindado de vulnerabilidades do LLM).
* **`knowledge_extractor.py`**: Onde o Llama 3 é evocado para analisar texto puro e ser forçado a criar um JSON estruturado. Corta saídas longas proativamente usando truncamento para mitigar limites de token.
* **`book_learning.py`**: É o iterador. Lê arquivos locais (`.txt` ou `.pdf` com PyPDF2), faz o chunking (2500 chars), entrega para o `knowledge_extractor` e devolve ao `module_manager`.
* **`memory_search.py`**: Realiza queries varrendo todos os arquivos `knowledge.json` indexados de forma offline sem usar tokens.
* **`meg_brain.py`**: Interface unificada onde basta chamar a variável de `brain` para iniciar processos.

---

## 🚀 Como Rodar e Testar

### 1. Requisitos e Dependências
Certifique-se de você ter tudo local instalado:

```cmd
# Instalar pacote do Ollama local se não estiver na pasta
pip install ollama

# Excitante mas opcional: Para permitir que a Meg leia PDFs
pip install PyPDF2
```

Lembre-se também de garantir que o modelo `llama3` rode no Ollama:
```cmd
ollama run llama3
```


### 2. Rodando seu primeiro script 

Veja um código limpo de como treinar a MEG e forçar inferências locais a partir de uma pasta qualquer na raiz:

Crie e rode um arquivo `teste.py` na pasta `PROJETO_MEG/`:

```python
from meg.core.meg_brain import MegBrain

# 1. Acorda o Core
brain = MegBrain()

# 2. Faz as extrações de novo conhecimento. Supondo que você criou um '.txt' legal contendo os fatos do "Espaço"
brain.learn(
    file_path="texto_exemplo.txt", 
    module_name="ciencia_espacial", 
    description="Fatos científicos sobre astronomia e estrelas"
)

# 3. Pergunte à MEG
resposta = brain.think_and_answer("O que dizem nossas memórias sobre buracos negros e afins?")
print("MEG respondeu:\n", resposta)
```
