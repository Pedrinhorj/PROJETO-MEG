"""
Apresentação — Interface Gráfica Tkinter (gui.py)

Classe MegInterface: janela principal da MEG com suporte a voz,
anexo de arquivos e aprendizado de documentos.

Esta camada importa apenas da camada de aplicação — nunca diretamente
de infraestrutura ou domínio (exceto os tipos).
"""
import logging
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog
import tkinter as tk
from typing import Optional

from meg.application.agent_service import montar_mensagens, obter_resposta_ollama
from meg.application.memory_service import (
    atualizar_memoria,
    caca_informacoes,
    carregar_memoria_permanente,
    carregar_memoria_usuario,
    extrair_memoria,
    salvar_memoria_sessao,
    salvar_memoria_usuario,
)
from meg.domain.memory_models import ChatMessage, UserMemory

logger = logging.getLogger(__name__)


class MegInterface:
    """Interface gráfica principal da MEG com suporte a chat, voz e aprendizado."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("🧠 Meg - Assistente Pessoal do Pedro Arthur")
        self.root.geometry("980x740")
        self.root.configure(bg="#1e1e1e")

        # Estado de voz
        self.voz = self._carregar_modulo_voz()
        self.voz_ativa: bool = self.voz is not None
        self.esta_falando: bool = False

        # Arquivo anexado aguardando envio
        self.arquivo_anexado_atual: Optional[str] = None

        # Estado do chat
        self.historico: list[ChatMessage] = []
        self.memoria_usuario: UserMemory = carregar_memoria_usuario()

        self._criar_interface()
        self._saudacao_inicial()

        self.root.protocol("WM_DELETE_WINDOW", self._fechar)
        self.root.mainloop()

    # ── Inicialização ──────────────────────────────────────────────────────────

    def _carregar_modulo_voz(self) -> Optional[object]:
        """Importa o módulo de voz opcionalmente, sem lançar exceção."""
        try:
            import voz
            logger.info("Módulo de voz carregado com sucesso.")
            return voz
        except ImportError as erro:
            logger.warning("Módulo de voz não disponível: %s", erro)
            return None

    def _saudacao_inicial(self) -> None:
        """Exibe mensagem de boas-vindas e fala a saudação se voz ativa."""
        self._adicionar_mensagem("Sistema", "Meg está online! Olá, Pedro Arthur 👋", "#00ffaa")
        if self.voz_ativa:
            threading.Thread(
                target=self._falar,
                args=("Olá Pedro Arthur, estou pronta para ajudar!",),
                daemon=True,
            ).start()

    # ── Construção da UI ───────────────────────────────────────────────────────

    def _criar_interface(self) -> None:
        """Constrói todos os widgets da janela principal."""
        self._criar_area_chat()
        self._criar_barra_entrada()
        self._criar_barra_status()

    def _criar_area_chat(self) -> None:
        self.chat_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state="disabled",
            font=("Segoe UI", 11),
            bg="#2d2d2d",
            fg="#e0e0e0",
            padx=12,
            pady=12,
        )
        self.chat_area.pack(padx=12, pady=12, fill=tk.BOTH, expand=True)

    def _criar_barra_entrada(self) -> None:
        frame = tk.Frame(self.root, bg="#1e1e1e")
        frame.pack(fill=tk.X, padx=12, pady=8)

        self.user_input = tk.Entry(
            frame,
            font=("Segoe UI", 12),
            bg="#3d3d3d",
            fg="#ffffff",
            insertbackground="#00ddff",
            relief=tk.FLAT,
            bd=5,
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.user_input.bind("<Return>", self._enviar_mensagem)

        botoes = [
            ("Enviar",      "#0099ff", self._enviar_mensagem,              8),
            ("📚 Aprender", "#9933ff", self._iniciar_aprendizado_documento, 10),
            ("📎 Anexar",   "#888888", self._anexar_arquivo_chat,           8),
        ]
        for texto, cor, cmd, largura in botoes:
            tk.Button(
                frame,
                text=texto,
                command=cmd,
                bg=cor,
                fg="white",
                font=("Segoe UI", 10, "bold"),
                width=largura,
                relief=tk.FLAT,
                pady=8,
            ).pack(side=tk.RIGHT, padx=(0, 4))

        self.mic_btn = tk.Button(
            frame,
            text="🎤 Falar",
            command=self._toggle_voz_entrada,
            bg="#00cc66" if self.voz_ativa else "#ff4444",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=12,
            relief=tk.FLAT,
            pady=8,
            state="normal" if self.voz_ativa else "disabled",
        )
        self.mic_btn.pack(side=tk.RIGHT)

    def _criar_barra_status(self) -> None:
        texto_status = "Pronto" if self.voz_ativa else "Voz desabilitada — módulo voz.py não encontrado"
        self.status_label = tk.Label(
            self.root,
            text=texto_status,
            bg="#1e1e1e",
            fg="#aaaaaa",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

    # ── Mensagens no Chat ──────────────────────────────────────────────────────

    def _adicionar_mensagem(self, remetente: str, texto: str, _cor: str = "#ffffff") -> None:
        """Insere uma mensagem na área de chat com cor de remetente."""
        self.chat_area.config(state="normal")
        tag = "meg" if remetente == "Meg" else "usuario"
        self.chat_area.insert(tk.END, f"{remetente}: ", tag)
        self.chat_area.insert(tk.END, f"{texto}\n\n")
        self.chat_area.tag_config("meg", foreground="#00ffcc", font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_config("usuario", foreground="#ffcc66", font=("Segoe UI", 11, "bold"))
        self.chat_area.see(tk.END)
        self.chat_area.config(state="disabled")

    def _atualizar_status(self, texto: str) -> None:
        self.status_label.config(text=texto)

    # ── Envio e Processamento ──────────────────────────────────────────────────

    def _enviar_mensagem(self, _event: Optional[object] = None) -> None:
        """Captura o input do usuário e dispara o processamento em thread."""
        pergunta = self.user_input.get().strip()
        if not pergunta and not self.arquivo_anexado_atual:
            return

        display = pergunta if pergunta else "(Arquivo Anexado)"
        self._adicionar_mensagem("Você", display)
        self.user_input.delete(0, tk.END)

        if self.arquivo_anexado_atual:
            pergunta_envio = f"{pergunta}\n\n[Arquivo Anexado: {self.arquivo_anexado_atual}]"
            self.arquivo_anexado_atual = None
        else:
            pergunta_envio = pergunta

        threading.Thread(
            target=self._processar_pergunta,
            args=(pergunta_envio,),
            daemon=True,
        ).start()

    def _processar_pergunta(self, pergunta: str) -> None:
        """Chama o agente (em background) e agenda a exibição da resposta."""
        caca_informacoes(pergunta)
        memoria_permanente = carregar_memoria_permanente()
        mensagens = montar_mensagens(pergunta, self.historico, memoria_permanente)
        resposta = obter_resposta_ollama(mensagens)
        self.root.after(0, self._finalizar_resposta, pergunta, resposta)

    def _finalizar_resposta(self, pergunta: str, resposta: str) -> None:
        """Exibe a resposta, atualiza histórico e dispara voz (na thread principal)."""
        if not resposta:
            resposta = "Desculpe, não consegui processar sua pergunta."

        self._adicionar_mensagem("Meg", resposta)

        self.historico.append({"role": "user", "content": pergunta})
        self.historico.append({"role": "assistant", "content": resposta})

        salvar_memoria_sessao(
            "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in self.historico)
        )

        comando_memoria = extrair_memoria(resposta)
        if comando_memoria:
            self.memoria_usuario = atualizar_memoria(self.memoria_usuario, comando_memoria)
            salvar_memoria_usuario(self.memoria_usuario)

        if self.voz_ativa:
            threading.Thread(target=self._falar, args=(resposta,), daemon=True).start()

    # ── Voz (saída) ────────────────────────────────────────────────────────────

    def _falar(self, texto: str) -> None:
        """Sintetiza voz de forma segura em thread separada."""
        if not self.voz_ativa or not self.voz or not texto:
            return
        self.esta_falando = True
        self.root.after(0, self._atualizar_status, "Meg está falando... 🔊")
        try:
            self.voz.falar(texto)
        except Exception as erro:
            logger.error("Erro ao falar: %s", erro)
        finally:
            self.esta_falando = False
            self.root.after(0, self._atualizar_status, "Pronto")

    # ── Voz (entrada / microfone) ──────────────────────────────────────────────

    def _toggle_voz_entrada(self) -> None:
        """Ativa o microfone para capturar voz do usuário."""
        if not self.voz_ativa or self.esta_falando:
            return
        self.mic_btn.config(bg="#ffaa00", text="🎤 Ouvindo...")
        self.root.after(0, self._atualizar_status, "Ouvindo... Fale agora!")
        threading.Thread(target=self._ouvir_usuario, daemon=True).start()

    def _ouvir_usuario(self) -> None:
        """Captura voz do microfone e processa como pergunta."""
        if not self.voz or not hasattr(self.voz, "ouvir"):
            self.root.after(0, self._finalizar_voz_entrada, "Erro: função ouvir() não encontrada.")
            return
        try:
            texto = self.voz.ouvir()
            if texto and texto.strip():
                self.root.after(0, self._processar_voz_recebida, texto)
            else:
                self.root.after(0, self._finalizar_voz_entrada, "Não entendi. Tente novamente.")
        except Exception as erro:
            self.root.after(0, self._finalizar_voz_entrada, f"Erro no reconhecimento: {erro}")

    def _processar_voz_recebida(self, texto: str) -> None:
        self._adicionar_mensagem("Você (voz)", texto)
        self._finalizar_voz_entrada()
        threading.Thread(target=self._processar_pergunta, args=(texto,), daemon=True).start()

    def _finalizar_voz_entrada(self, mensagem_status: str = "Pronto") -> None:
        self.mic_btn.config(bg="#00cc66", text="🎤 Falar")
        self._atualizar_status(mensagem_status)

    # ── Anexar Arquivo ─────────────────────────────────────────────────────────

    def _anexar_arquivo_chat(self) -> None:
        """Abre modal para escolher entre arquivo local ou módulo indexado."""
        pop = tk.Toplevel(self.root)
        pop.title("Opções de Anexo")
        pop.geometry("320x160")
        pop.configure(bg="#2d2d2d")
        pop.transient(self.root)
        pop.grab_set()

        tk.Label(
            pop,
            text="De onde deseja anexar um arquivo?",
            bg="#2d2d2d",
            fg="white",
            font=("Segoe UI", 11),
        ).pack(pady=10)

        def do_local() -> None:
            pop.destroy()
            caminho = filedialog.askopenfilename(
                title="Anexar arquivo para a conversa",
                filetypes=[("Todos os arquivos", "*.*")],
            )
            if caminho:
                self.arquivo_anexado_atual = caminho
                self._adicionar_mensagem("Sistema", f"📌 Arquivo local anexado: {caminho}", "#aaaaaa")

        def do_indexado() -> None:
            pop.destroy()
            self._escolher_modulo_indexado()

        for texto, cor, cmd in [
            ("📁 Arquivo Local (Seu PC)",    "#0099ff", do_local),
            ("🧠 Módulo Indexado da Meg",    "#9933ff", do_indexado),
        ]:
            tk.Button(
                pop,
                text=texto,
                command=cmd,
                bg=cor,
                fg="white",
                font=("Segoe UI", 10, "bold"),
                width=25,
                relief=tk.FLAT,
            ).pack(pady=5)

    def _escolher_modulo_indexado(self) -> None:
        """Lista os módulos aprendidos e permite anexar um ao chat."""
        import json as _json

        try:
            from megconfig.learning.module_manager import INDEX_FILE
            with open(INDEX_FILE, "r", encoding="utf-8") as arquivo:
                data = _json.load(arquivo)
            modulos = [m["name"] for m in data.get("modules", [])]
        except Exception:
            modulos = []

        if not modulos:
            messagebox.showinfo("Sem Módulos", "A Meg ainda não possui nenhum arquivo aprendido.")
            return

        pop2 = tk.Toplevel(self.root)
        pop2.title("Anexar Módulo Aprendido")
        pop2.geometry("380x300")
        pop2.configure(bg="#2d2d2d")
        pop2.transient(self.root)
        pop2.grab_set()

        tk.Label(
            pop2,
            text="Selecione um tópico aprendido:",
            bg="#2d2d2d",
            fg="white",
            font=("Segoe UI", 11),
        ).pack(pady=5)

        lista = tk.Listbox(pop2, bg="#1e1e1e", fg="white", font=("Segoe UI", 11), selectbackground="#9933ff")
        lista.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for modulo in modulos:
            lista.insert(tk.END, modulo)

        def confirmar() -> None:
            sel = lista.curselection()
            if not sel:
                return
            nome_mod = lista.get(sel[0])
            pop2.destroy()
            from megconfig.learning.module_manager import INDEX_FILE
            import os
            caminho = os.path.join(
                os.path.dirname(INDEX_FILE), "modules", nome_mod, "knowledge.json"
            )
            self.arquivo_anexado_atual = caminho
            self._adicionar_mensagem(
                "Sistema",
                f"📌 Módulo indexado anexado: [{nome_mod}]",
                "#aaaaaa",
            )

        tk.Button(
            pop2,
            text="Confirmar Anexo",
            command=confirmar,
            bg="#00cc66",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
        ).pack(pady=10)

    # ── Aprendizado de Documentos ──────────────────────────────────────────────

    def _iniciar_aprendizado_documento(self) -> None:
        """Abre seletor de arquivo e dispara aprendizado profundo em thread."""
        caminho = filedialog.askopenfilename(
            title="Selecione um arquivo para a Meg aprender (PDF, DOCX, TXT)",
            filetypes=[("Documentos suportados", "*.pdf *.docx *.txt"), ("Todos", "*.*")],
        )
        if not caminho:
            return

        nome_modulo = simpledialog.askstring(
            "Novo Aprendizado",
            "Qual será o nome/tópico deste aprendizado?",
        )
        if not nome_modulo:
            nome_modulo = Path(caminho).stem

        self._adicionar_mensagem(
            "Meg",
            f"Iniciando aprendizado de '{caminho}'...\nIsso pode demorar. Continue conversando normalmente!",
            "#cc99ff",
        )

        def thread_learn() -> None:
            try:
                from megconfig.learning.book_learning import learn_from_file
                sucesso = learn_from_file(caminho, nome_modulo, "Aprendido via UI.")
                if sucesso:
                    self.root.after(
                        0,
                        self._adicionar_mensagem,
                        "Meg",
                        f"✅ Estudo concluído! O módulo '{nome_modulo}' foi gravado na memória profunda.",
                        "#cc99ff",
                    )
                    if self.voz_ativa:
                        self.root.after(0, self._falar, f"Memorizei tudo sobre {nome_modulo}.")
                else:
                    self.root.after(
                        0,
                        self._adicionar_mensagem,
                        "Meg",
                        "⚠️ Arquivo vazio, ilegível ou extensão não suportada. Veja o console para detalhes.",
                        "#ff4444",
                    )
            except Exception as erro:
                self.root.after(
                    0,
                    self._adicionar_mensagem,
                    "Meg",
                    f"⚠️ Erro no aprendizado: {erro}",
                    "#ff4444",
                )

        threading.Thread(target=thread_learn, daemon=True).start()

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    def _fechar(self) -> None:
        """Encerra a janela de forma segura, parando a voz se necessário."""
        logger.info("Encerrando MEG Interface...")
        if self.esta_falando and self.voz and hasattr(self.voz, "parar"):
            try:
                self.voz.parar()
            except Exception:
                pass
        self.root.destroy()
