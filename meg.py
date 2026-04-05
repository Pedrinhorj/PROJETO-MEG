# =====================================================================
# SEÇÃO 1: IMPORTAÇÕES DE BIBLIOTECAS E TIPAGENS
# =====================================================================
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import os
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext

import ollama
from duckduckgo_search import DDGS

# =====================================================================
# SEÇÃO 2: DEFINIÇÃO DE CAMINHOS E CONSTANTES GERAIS
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
ARMAZENAMENTO_DIR = BASE_DIR / "ArmazenamentoMemoria"
MEMORIA_JSON = ARMAZENAMENTO_DIR / "memoria.json"
MEMORIA_PERMANENTE = ARMAZENAMENTO_DIR / "memoria_permanente.txt"
MEMORIA_SESSAO = ARMAZENAMENTO_DIR / "conversa_sessao.txt"
MEMORIA_USUARIO_JSON = ARMAZENAMENTO_DIR / "memoria_usuario.json"
MODEL_NAME = "meg"

# =====================================================================
# SEÇÃO 3: DEFINIÇÃO DE FERRAMENTAS (TOOL CALLING NATIVO)
# =====================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "pesquisar_web",
            "description": "Realiza uma pesquisa na internet. Use quando precisar de informações atualizadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Pergunta ou termo para pesquisar"},
                    "max_results": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ler_arquivo",
            "description": "Lê o conteúdo completo de um arquivo de texto no computador do usuário. Use quando o Pedro pedir para ler um arquivo, ver código, notas, logs, etc. Aceita caminho relativo ou absoluto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caminho": {
                        "type": "string",
                        "description": "Caminho do arquivo (ex: 'documentos/notas.txt', 'C:/projetos/script.py' ou '~/meu_arquivo.md')"
                    }
                },
                "required": ["caminho"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_memoria_aprendida",
            "description": "Busca e consulta informações aprendidas de módulos, livros, PDFs ou DOCX em sua memória profunda. Use quando o usuário perguntar sobre coisas que você validamente leu dos resumos e módulos aprendidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca, palavra-chave, tópico ou dúvida sobre o documento aprendido."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_navegador",
            "description": "Abre o navegador padrão na página do Google",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

# =====================================================================
# SEÇÃO 4: EXECUÇÃO DE FERRAMENTAS
# =====================================================================

FERRAMENTAS = json.dumps([t["function"] for t in TOOLS], ensure_ascii=False, indent=2)

def executar_ferramenta(tool_call: Any) -> str:
    if isinstance(tool_call, str):
        name = tool_call.strip()
        args = {}
    elif isinstance(tool_call, dict):
        func = tool_call.get('function', tool_call)
        name = func.get('name', '')
        args = func.get('arguments', {})
    else:
        func = getattr(tool_call, 'function', tool_call)
        name = getattr(func, 'name', '')
        args = getattr(func, 'arguments', {})

    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}

    try:
        if name == "pesquisar_web":
            query = args.get("query", "").strip()
            max_results = args.get("max_results", 5)
            try: max_results = int(max_results)
            except: max_results = 5
            
            if not query:
                return "Erro ao executar pesquisar_web: Você não forneceu uma 'query' válida para pesquisar. Corrija a digitação dos parâmetros."
            
            with DDGS() as ddgs:
                resultados = ddgs.text(query, region="br-BR", max_results=max_results)
                if not resultados:
                    return "Nenhum resultado encontrado na pesquisa."
                return "\n\n".join([f"• {r['title']}\n{r['body'][:300]}...\nLink: {r['href']}" for r in resultados])

        elif name == "ler_arquivo":
            caminho_str = args.get("caminho", "").strip()
            if not caminho_str:
                return "Erro: Nenhum caminho de arquivo foi fornecido."

            # Converte caminho relativo em absoluto (baseado no diretório do projeto)
            caminho = Path(caminho_str).expanduser().resolve()

            # Segurança básica: só permite ler dentro de certas pastas (evita ler arquivos sensíveis)
            allowed_dirs = [BASE_DIR, Path.home() / "Documents", Path.home() / "Desktop", Path.home() / "Downloads"]
            path_allowed = False
            for d in allowed_dirs:
                try:
                    if caminho.is_relative_to(d.resolve()):
                        path_allowed = True
                        break
                except ValueError:  # fallback caso is_relative_to falhe dependendo do path
                    pass
            if not path_allowed:
                return f"Erro: Acesso negado. Só posso ler arquivos dentro das pastas permitidas."

            if not caminho.exists():
                return f"Erro: Arquivo não encontrado: {caminho}"
            if not caminho.is_file():
                return f"Erro: O caminho não é um arquivo: {caminho}"

            try:
                conteudo = caminho.read_text(encoding="utf-8")
                # Limita o tamanho para não explodir o contexto do modelo
                if len(conteudo) > 15000:
                    conteudo = conteudo[:15000] + "\n\n... (arquivo muito grande, conteúdo truncado)"
                return f"Conteúdo do arquivo '{caminho.name}':\n\n{conteudo}"
            except Exception as e:
                return f"Erro ao ler o arquivo: {str(e)}"

        elif name == "consultar_memoria_aprendida":
            query = args.get("query", "").strip()
            if not query:
                return "Erro ao executar: Você deve fornecer uma 'query' com a sua busca."
            try:
                from megconfig.retrieval.memory_search import search_memory
                resultados = search_memory(query)
                if not resultados:
                    return f"Nenhuma informação encontrada na memória do aprendizado profundo sobre '{query}'."
                
                texto_res = f"Resultados encontrados na memória para '{query}':\n"
                for res in resultados[:5]:
                    modulo = res['module']
                    k = res['knowledge']
                    texto_res += f"- [Módulo: {modulo}] {k.get('topic')}: {k.get('summary')} (Palavras-chaves: {', '.join(k.get('keywords', []))}). Detalhes: {k.get('details')}\n"
                return texto_res
            except Exception as e:
                return f"Erro ao consultar memória aprendida: {str(e)}"

        elif name == "abrir_navegador":
            subprocess.Popen("start https://www.google.com", shell=True)
            return "Navegador aberto no Google."

        else:
            return f"Ferramenta '{name}' não implementada ainda."

    except Exception as e:
        return f"Erro ao executar {name}: {str(e)}"
# =====================================================================
# SEÇÃO 5: FUNÇÕES UTILITÁRIAS PARA MANIPULAÇÃO DE ARQUIVOS JSON
# =====================================================================

def load_json(path: Path) -> List[Dict[str, Any]]:
    if not path.exists(): return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except: return []

def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =====================================================================
# SEÇÃO 6: GERENCIAMENTO DE MEMÓRIA (CURTO/LONGO PRAZO E USUÁRIO)
# =====================================================================

def salvar_memoria(nova_entrada: Dict[str, Any]) -> None:
    memorias = load_json(MEMORIA_JSON)
    memorias.append(nova_entrada)
    save_json(MEMORIA_JSON, memorias)

def carregar_memoria_usuario() -> Dict[str, Any]:
    if not MEMORIA_USUARIO_JSON.exists(): return {}
    try:
        with MEMORIA_USUARIO_JSON.open("r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
    except: return {}

def salvar_memoria_usuario(memoria: Dict[str, Any]) -> None:
    ARMAZENAMENTO_DIR.mkdir(parents=True, exist_ok=True)
    with MEMORIA_USUARIO_JSON.open("w", encoding="utf-8") as f:
        json.dump(memoria, f, indent=4, ensure_ascii=False)

def atualizar_memoria(memoria: Dict[str, Any], comando: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not comando: return memoria
    acao, campo, valor = comando.get("acao"), comando.get("campo"), comando.get("valor")
    if not campo: return memoria
    if acao == "atualizar": memoria[campo] = valor
    elif acao == "adicionar":
        if campo not in memoria: memoria[campo] = []
        if isinstance(memoria[campo], list): memoria[campo].append(valor)
    return memoria

def extrair_memoria(texto: str) -> Optional[Dict[str, Any]]:
    if "MEMORIA:" not in texto: return None
    try:
        parte = texto.split("MEMORIA:", 1)[1].strip()
        return json.loads(parte.splitlines()[0])
    except: return None

def caca_informacoes(pergunta: str) -> None:
    trecho = pergunta.strip()
    if not trecho: return
    timestamp = datetime.now().isoformat(timespec="seconds")
    salvar_memoria({"data": timestamp, "conteudo": trecho, "tags": []})
    MEMORIA_PERMANENTE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORIA_PERMANENTE.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {trecho}\n")

def carregar_memoria_permanente() -> str:
    if not MEMORIA_PERMANENTE.exists(): return ""
    return MEMORIA_PERMANENTE.read_text(encoding="utf-8")

# =====================================================================
# SEÇÃO 7: LÓGICA DE INTERAÇÃO COM O MODELO OLLAMA
# =====================================================================

def carregar_regras_modelfile() -> str:
    """Lê todas as regras mestre englobadas no Modelfile para injetar fisicamente no chat da MEG."""
    caminho = BASE_DIR / "Modelfile"
    padrao = "Você é a Meg, assistente inteligente."
    if not caminho.exists():
        return padrao
    try:
        conteudo = caminho.read_text(encoding="utf-8")
        if 'SYSTEM """' in conteudo:
            return conteudo.split('SYSTEM """')[1].split('"""')[0].strip()
        elif 'SYSTEM "' in conteudo:
            return conteudo.split('SYSTEM "')[1].split('"')[0].strip()
        return padrao
    except:
        return padrao

def montar_mensagens(pergunta: str, historico: List[Dict[str, str]]) -> List[Dict[str, str]]:
    mem_p = carregar_memoria_permanente() or "Nenhuma informação aprendida ainda."
    personalidade_modelfile = carregar_regras_modelfile()
    
    system_prompt = (
        f"{personalidade_modelfile}\n\n"
        "------ SUAS INSTRUÇÕES DE SISTEMA EXTRAS E FERRAMENTAS ------\n"
        "VOCÊ PODE INTERAGIR COM FERRAMENTAS PARA ACESSAR DADOS FORA DA MENTE. Lembre-se que é autônoma:\n"
        "1. Pense passo a passo.\n"
        "2. Intercepte e use ferramentas se não souber de algo de imediato!\n\n"
        f"FERRAMENTAS DISPONÍVEIS AGORA:\n{FERRAMENTAS}\n\n"
        "[SUA MARCA DE MEMÓRIA PERMANENTE ATIVA CONTEXTUALIZADA]:\n"
        f"{mem_p}"
    )
    
    mensagens: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    mensagens.extend(historico)
    mensagens.append({"role": "user", "content": pergunta})
    return mensagens
# =====================================================================
# SEÇÃO 8: GERENCIAMENTO DA SESSÃO ATUAL
# =====================================================================

def salvar_memoria_sessao(conteudo: str) -> None:
    """Persiste a memória de sessão atual no disco."""
    MEMORIA_SESSAO.parent.mkdir(parents=True, exist_ok=True)
    MEMORIA_SESSAO.write_text(conteudo, encoding="utf-8")

# =====================================================================
# SEÇÃO 9: LOOP PRINCIPAL DA APLICAÇÃO (MAIN) E AGENTE RECURSIVO
# =====================================================================

def obter_resposta_ollama(mensagens: List[Dict[str, str]]) -> str:
    """Executa o loop do agente ReAct com as ferramentas."""
    max_loops = 10
    loops = 0

    while loops < max_loops:
        loops += 1
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=mensagens
                # Options removidas: O tamanho do contexto agora é engolido exclusivamente pelo Modelfile leve (4096)
            )
        except Exception as e:
            return f"Erro de comunicação com Ollama: {str(e)}"

        # A lib ollama pode retornar objeto ou dict — normalizamos aqui
        raw_msg = response.get('message') if isinstance(response, dict) else getattr(response, 'message', {})
        if isinstance(raw_msg, dict):
            mensagem = raw_msg
        else:
            # Objeto com atributos (ex: ollama.Message)
            mensagem = {
                'content': getattr(raw_msg, 'content', '') or '',
                'tool_calls': getattr(raw_msg, 'tool_calls', None),
                'role': getattr(raw_msg, 'role', 'assistant'),
            }

        texto = mensagem.get('content') or ""

        # 1. Tenta chamadas nativas de ferramenta (se o modelo suportar futuramente)
        if mensagem.get('tool_calls'):
            tool_results = []
            for tool_call in mensagem.get('tool_calls', []):
                resultado = executar_ferramenta(tool_call)
                if isinstance(tool_call, dict):
                    func = tool_call.get('function', tool_call)
                    t_name = func.get('name', 'unknown')
                else:
                    func = getattr(tool_call, 'function', tool_call)
                    t_name = getattr(func, 'name', 'unknown')
                    
                tool_results.append({
                    "role": "user",  # Fallback seguro para modelos sem tool role
                    "content": f"[SYSTEM - Resultado de {t_name}]:\n{resultado}"
                })
                print(f"🔧 Meg usou (nativo): {t_name} → {resultado[:100]}...")
            
            mensagens.append(mensagem)
            mensagens.extend(tool_results)
            continue
            
        # 2. Tenta chamadas de ferramenta baseadas em texto (Fallback ReAct compatível)
        texto_upper = texto.upper()
        if "AÇÃO:" in texto_upper or "ACAO:" in texto_upper:
            marcador = "AÇÃO:" if "AÇÃO:" in texto else "ACAO:"
            cmd = texto.split(marcador, 1)[1].strip()
            resultado = executar_ferramenta(cmd)
            t_name = cmd.split()[0] if cmd else "unknown"
            
            mensagens.append(mensagem) # Salva pensamento da IA
            mensagens.append({
                "role": "user",
                "content": f"[SYSTEM - Resultado de {t_name}]:\n{resultado}"
            })
            print(f"🔧 Meg usou (texto): {t_name} → {resultado[:100]}...")
            continue
            
        # 3. Se não tiver chamadas de ferramentas, retorna a resposta final
        return texto

    return "🚨 Loop de análise interrompido (Muitas requisições de ferramentas). Ocorreu um erro na lógica do agente."

def main() -> None:
    try:
        import voz  # import local para evitar ciclo de importação
    except ImportError as e:
        print(f"[AVISO] Módulo de voz não disponível: {e}. Continuando sem síntese de voz.")
        voz = None
    print("Meg está online. Digite 'sair' para encerrar.\n")
    
    # Saudação inicial por voz
    if voz:
        threading.Thread(target=voz.falar, args=("Meg online. Olá, Pedro Arthur!",), daemon=True).start()

    memoria_sessao = ""
    historico: List[Dict[str, str]] = []
    memoria_usuario = carregar_memoria_usuario()

    while True:
        pergunta = input("Você: ").strip()
        if pergunta.lower() == "sair":
            print("Encerrando...")
            break

                # ---> PROCESSAMENTO DO AGENTE AUTÔNOMO
        caca_informacoes(pergunta)
        
        mensagens = montar_mensagens(pergunta, historico)
        # Executa o loop do agente importável
        texto = obter_resposta_ollama(mensagens)

        # ---> Resposta final (voz + texto)
        print(f"\nMeg: {texto}\n")
        if voz:
            threading.Thread(target=voz.falar, args=(texto,), daemon=True).start()

        # Atualiza histórico e memória de sessão
        historico.append({"role": "user", "content": pergunta})
        historico.append({"role": "assistant", "content": texto})
        salvar_memoria_sessao("\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in historico
        ))

        # ---> Atualização da Memória Baseada em Resposta
        # Ferramentas já foram processadas dentro de obter_resposta_ollama
        cmd_mem = extrair_memoria(texto)
        if cmd_mem:
            memoria_usuario = atualizar_memoria(memoria_usuario, cmd_mem)
            salvar_memoria_usuario(memoria_usuario)



if __name__ == "__main__":
    main()