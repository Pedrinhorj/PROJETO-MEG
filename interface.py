# =====================================================================
# interface.py - Interface Minimalista da Meg com Código Interativo
# =====================================================================
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import re
import time
from pathlib import Path
from typing import List, Dict

# Importa as funções do core
from meg import (
    montar_mensagens,
    obter_resposta_ollama,
    caca_informacoes,
    salvar_memoria_sessao,
    extrair_memoria,
    atualizar_memoria,
    salvar_memoria_usuario,
    carregar_memoria_usuario,
)

# ──────────────────────────────────────────────
# PALETA DE CORES
# ──────────────────────────────────────────────
C = {
    "bg":           "#141414",   # fundo principal
    "bg_chat":      "#141414",   # fundo da área de chat
    "bg_input":     "#1f1f1f",   # fundo do campo de entrada
    "bg_bubble_u":  "#1e3a5f",   # balão do usuário
    "bg_bubble_m":  "#1c1c1c",   # balão da meg
    "bg_code_head": "#252526",   # cabeçalho do bloco de código
    "bg_code_body": "#1e1e1e",   # corpo do bloco de código
    "fg":           "#d4d4d4",   # texto principal
    "fg_dim":       "#6a6a6a",   # texto secundário
    "fg_user":      "#9cdcfe",   # nome do usuário
    "fg_meg":       "#4ec9b0",   # nome da meg
    "fg_sys":       "#565656",   # sistema
    "fg_code_lang": "#858585",   # label da linguagem
    "accent":       "#0e639c",   # azul de destaque
    "accent_hover": "#1177bb",   # azul hover
    "border":       "#2d2d2d",   # bordas
    "copy_btn":     "#3a3a3a",   # botão copiar normal
    "copy_ok":      "#1e4620",   # botão copiar OK
    "copy_fg":      "#cccccc",
    "copy_ok_fg":   "#4ec9b0",
    "send_btn":     "#0e639c",
    "send_hover":   "#1177bb",
    "scrollbar":    "#2d2d2d",
}

FONT_UI    = ("Segoe UI", 11)
FONT_BOLD  = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_CODE  = ("Consolas", 10)
FONT_CODE_HEADER = ("Segoe UI", 9)

# Regex para detectar blocos de código markdown  ```lang\n...\n```
CODE_BLOCK_RE = re.compile(r'```(\w*)\n?(.*?)```', re.DOTALL)


class MegInterface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Meg")
        self.root.geometry("1000x760")
        self.root.configure(bg=C["bg"])
        self.root.minsize(700, 500)

        self._thinking_job = None
        self._thinking_dots = 0

        self.historico: List[Dict[str, str]] = []
        self.memoria_usuario = carregar_memoria_usuario()
        self.arquivo_anexado_atual = None

        self._criar_interface()
        self._adicionar_mensagem_sistema("Meg online.")
        self.root.protocol("WM_DELETE_WINDOW", self._fechar)
        self.root.mainloop()

    # ──────────────────────────────────────────
    # CONSTRUÇÃO DA INTERFACE
    # ──────────────────────────────────────────
    def _criar_interface(self):
        # ── Cabeçalho ──
        header = tk.Frame(self.root, bg=C["bg"], height=48)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)

        tk.Label(
            header, text="MEG", bg=C["bg"], fg=C["fg_meg"],
            font=("Segoe UI", 13, "bold")
        ).pack(side=tk.LEFT, padx=20, pady=12)

        self._lbl_status = tk.Label(
            header, text="", bg=C["bg"], fg=C["fg_dim"],
            font=FONT_SMALL
        )
        self._lbl_status.pack(side=tk.LEFT, padx=4)

        # ── Separador ──
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill=tk.X)

        # ── Área de chat com scrollbar customizada ──
        chat_container = tk.Frame(self.root, bg=C["bg_chat"])
        chat_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        scrollbar = tk.Scrollbar(chat_container, bg=C["bg"], troughcolor=C["bg"],
                                  relief=tk.FLAT, bd=0, width=8)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 2))

        self.chat_area = tk.Text(
            chat_container,
            wrap=tk.WORD,
            state="disabled",
            font=FONT_UI,
            bg=C["bg_chat"],
            fg=C["fg"],
            bd=0,
            relief=tk.FLAT,
            padx=28,
            pady=16,
            spacing1=2,
            spacing3=2,
            cursor="arrow",
            yscrollcommand=scrollbar.set,
            highlightthickness=0,
        )
        self.chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chat_area.yview)

        # Tags de texto
        self.chat_area.tag_configure("nome_meg",    foreground=C["fg_meg"],  font=FONT_BOLD)
        self.chat_area.tag_configure("nome_user",   foreground=C["fg_user"], font=FONT_BOLD)
        self.chat_area.tag_configure("nome_sys",    foreground=C["fg_sys"],  font=FONT_SMALL)
        self.chat_area.tag_configure("texto_normal",foreground=C["fg"],      font=FONT_UI)
        self.chat_area.tag_configure("texto_sys",   foreground=C["fg_sys"],  font=FONT_SMALL)
        self.chat_area.tag_configure("bold",        foreground=C["fg"],      font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_configure("italic",      foreground="#ce9178",    font=("Segoe UI", 11, "italic"))
        self.chat_area.tag_configure("inline_code", foreground="#ce9178",
                                     font=("Consolas", 10), background="#2d2d2d")
        self.chat_area.tag_configure("espacador",   font=("Segoe UI", 4))

        # ── Separador ──
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill=tk.X)

        # ── Painel inferior ──
        bottom = tk.Frame(self.root, bg=C["bg"], pady=12)
        bottom.pack(fill=tk.X, padx=20)

        # Botões de ação (esquerda)
        btn_frame = tk.Frame(bottom, bg=C["bg"])
        btn_frame.pack(side=tk.LEFT, padx=(0, 10))

        self._btn_attach = self._make_icon_btn(btn_frame, "📎", self._anexar_arquivo, "Anexar arquivo")
        self._btn_attach.pack(side=tk.LEFT, padx=(0, 6))

        self._btn_learn = self._make_icon_btn(btn_frame, "📚", self._iniciar_aprendizado, "Aprender documento")
        self._btn_learn.pack(side=tk.LEFT)

        # Campo de entrada
        input_wrap = tk.Frame(bottom, bg=C["bg_input"], bd=0)
        input_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)

        self.user_input = tk.Text(
            input_wrap,
            font=FONT_UI,
            bg=C["bg_input"],
            fg=C["fg"],
            insertbackground=C["fg_meg"],
            relief=tk.FLAT,
            bd=0,
            height=2,
            wrap=tk.WORD,
            padx=12,
            pady=8,
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
        )
        self.user_input.pack(fill=tk.BOTH, expand=True)
        self.user_input.bind("<Return>", self._on_enter)
        self.user_input.bind("<Shift-Return>", lambda e: None)  # shift+enter = nova linha

        # Placeholder
        self._placeholder_text = "Mensagem para Meg..."
        self._placeholder_on = True
        self._set_placeholder()
        self.user_input.bind("<FocusIn>",  self._clear_placeholder)
        self.user_input.bind("<FocusOut>", self._restore_placeholder)

        # Botão Enviar
        self._btn_send = tk.Button(
            bottom, text="↑",
            command=self._enviar_mensagem,
            bg=C["send_btn"], fg="white",
            font=("Segoe UI", 14, "bold"),
            width=3, relief=tk.FLAT, bd=0,
            activebackground=C["send_hover"],
            activeforeground="white",
            cursor="hand2",
        )
        self._btn_send.pack(side=tk.LEFT, padx=(8, 0))
        self._btn_send.bind("<Enter>", lambda e: self._btn_send.config(bg=C["send_hover"]))
        self._btn_send.bind("<Leave>", lambda e: self._btn_send.config(bg=C["send_btn"]))

    # ──────────────────────────────────────────
    # PLACEHOLDER
    # ──────────────────────────────────────────
    def _set_placeholder(self):
        self.user_input.delete("1.0", tk.END)
        self.user_input.insert("1.0", self._placeholder_text)
        self.user_input.config(fg=C["fg_dim"])
        self._placeholder_on = True

    def _clear_placeholder(self, event=None):
        if self._placeholder_on:
            self.user_input.delete("1.0", tk.END)
            self.user_input.config(fg=C["fg"])
            self._placeholder_on = False

    def _restore_placeholder(self, event=None):
        if not self.user_input.get("1.0", tk.END).strip():
            self._set_placeholder()

    # ──────────────────────────────────────────
    # BOTÃO ÍCONE
    # ──────────────────────────────────────────
    def _make_icon_btn(self, parent, icon, cmd, tooltip=""):
        btn = tk.Button(
            parent, text=icon, command=cmd,
            bg=C["bg"], fg=C["fg_dim"],
            font=("Segoe UI", 13),
            relief=tk.FLAT, bd=0,
            activebackground=C["border"],
            activeforeground=C["fg"],
            cursor="hand2", padx=4, pady=2,
        )
        btn.bind("<Enter>", lambda e: btn.config(fg=C["fg"]))
        btn.bind("<Leave>", lambda e: btn.config(fg=C["fg_dim"]))
        return btn

    # ──────────────────────────────────────────
    # INDICADOR "PENSANDO..."
    # ──────────────────────────────────────────
    def _start_thinking(self):
        self._thinking_dots = 0
        self._animate_thinking()

    def _animate_thinking(self):
        dots = "." * (self._thinking_dots % 4)
        self._lbl_status.config(text=f"Meg está pensando{dots}")
        self._thinking_dots += 1
        self._thinking_job = self.root.after(420, self._animate_thinking)

    def _stop_thinking(self):
        if self._thinking_job:
            self.root.after_cancel(self._thinking_job)
            self._thinking_job = None
        self._lbl_status.config(text="")

    # ──────────────────────────────────────────
    # RENDERIZAÇÃO DE MENSAGENS
    # ──────────────────────────────────────────
    def _chat_write(self, text, *tags):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, text, tags)
        self.chat_area.config(state="disabled")

    def _chat_window(self, widget):
        """Embute um widget dentro do Text."""
        self.chat_area.config(state="normal")
        self.chat_area.window_create(tk.END, window=widget)
        self.chat_area.config(state="disabled")

    def _adicionar_mensagem_sistema(self, texto: str):
        self._chat_write("\n")
        self._chat_write(f"  {texto}\n", "texto_sys")
        self._chat_write("\n", "espacador")
        self.chat_area.see(tk.END)

    def adicionar_mensagem(self, remetente: str, texto: str, cor: str = None):
        """Compatibilidade com chamadas externas."""
        if remetente in ("Sistema", "System"):
            self._adicionar_mensagem_sistema(texto)
            return
        is_meg = remetente.lower() == "meg"
        self._renderizar_resposta(texto, is_meg=is_meg)

    def _renderizar_resposta(self, texto: str, is_meg: bool = True):
        """Parseia markdown e renderiza no chat com blocos de código embutidos."""
        self.chat_area.config(state="normal")

        # Nome do remetente
        tag_nome = "nome_meg" if is_meg else "nome_user"
        nome = "Meg" if is_meg else "Você"
        self.chat_area.insert(tk.END, "\n")
        self.chat_area.insert(tk.END, f"{nome}\n", tag_nome)

        # Divide texto em partes: código e texto normal
        partes = CODE_BLOCK_RE.split(texto)
        # split com 2 grupos gera: [texto, lang, code, texto, lang, code, ...]
        i = 0
        while i < len(partes):
            if i % 3 == 0:
                # Texto normal — renderiza inline formatting
                self._renderizar_texto_normal(partes[i])
            elif i % 3 == 1:
                lang = partes[i].strip() or "code"
                code = partes[i + 1] if i + 1 < len(partes) else ""
                self._renderizar_bloco_codigo(lang, code)
                i += 1  # pula o grupo 'code'
            i += 1

        self.chat_area.insert(tk.END, "\n", "espacador")
        self.chat_area.config(state="disabled")
        self.chat_area.see(tk.END)

    def _renderizar_texto_normal(self, texto: str):
        """Renderiza texto com suporte a **negrito**, *itálico* e `inline code`."""
        if not texto:
            return

        # Regex para detectar marcações inline
        pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)', re.DOTALL)
        last = 0
        for m in pattern.finditer(texto):
            # Texto antes da marcação
            before = texto[last:m.start()]
            if before:
                self.chat_area.insert(tk.END, before, "texto_normal")

            raw = m.group(0)
            if raw.startswith("**"):
                self.chat_area.insert(tk.END, m.group(2), "bold")
            elif raw.startswith("*"):
                self.chat_area.insert(tk.END, m.group(3), "italic")
            elif raw.startswith("`"):
                self.chat_area.insert(tk.END, m.group(4), "inline_code")

            last = m.end()

        # Resto do texto
        resto = texto[last:]
        if resto:
            self.chat_area.insert(tk.END, resto, "texto_normal")

    def _renderizar_bloco_codigo(self, lang: str, code: str):
        """Cria um container estilo VSCode embutido no Text widget."""
        # Container externo com padding
        outer = tk.Frame(self.chat_area, bg=C["bg_chat"], pady=6)
        outer.pack_propagate(False)

        # Frame principal do bloco
        frame = tk.Frame(outer, bg=C["bg_code_body"],
                         highlightbackground=C["border"], highlightthickness=1)
        frame.pack(fill=tk.X, padx=28)

        # ── Cabeçalho ──
        header = tk.Frame(frame, bg=C["bg_code_head"], pady=5, padx=10)
        header.pack(fill=tk.X)

        tk.Label(
            header, text=lang.lower(), bg=C["bg_code_head"],
            fg=C["fg_code_lang"], font=FONT_CODE_HEADER
        ).pack(side=tk.LEFT)

        # Botão copiar
        btn_copy = tk.Button(
            header, text="📋  Copiar",
            bg=C["copy_btn"], fg=C["copy_fg"],
            font=("Segoe UI", 8), relief=tk.FLAT, bd=0,
            padx=8, pady=2,
            activebackground=C["accent"],
            activeforeground="white",
            cursor="hand2",
        )
        btn_copy.pack(side=tk.RIGHT)

        # ── Separador ──
        tk.Frame(frame, bg=C["border"], height=1).pack(fill=tk.X)

        # ── Área do código ──
        code_clean = code.strip()
        linhas = code_clean.count("\n") + 1
        altura = min(max(linhas, 2), 25)  # entre 2 e 25 linhas visíveis

        code_text = tk.Text(
            frame,
            font=FONT_CODE,
            bg=C["bg_code_body"],
            fg="#d4d4d4",
            bd=0, relief=tk.FLAT,
            padx=16, pady=12,
            height=altura,
            wrap=tk.NONE,
            state="normal",
            highlightthickness=0,
            cursor="arrow",
            selectbackground="#264f78",
            selectforeground="#d4d4d4",
            insertwidth=0,
        )
        code_text.insert("1.0", code_clean)
        code_text.config(state="disabled")
        code_text.pack(fill=tk.X)

        # Scroll horizontal se necessário
        hbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=code_text.xview,
                             bg=C["bg_code_body"], troughcolor=C["bg_code_body"],
                             relief=tk.FLAT, bd=0)
        code_text.config(xscrollcommand=hbar.set)
        # Só mostra scrollbar se tiver linha longa
        if any(len(l) > 80 for l in code_clean.splitlines()):
            hbar.pack(fill=tk.X)

        # ── Lógica do botão copiar ──
        def _copiar(event=None, bt=btn_copy, ct=code_text, cd=code_clean):
            self.root.clipboard_clear()
            self.root.clipboard_append(cd)
            bt.config(text="✓  Copiado!", bg=C["copy_ok"], fg=C["copy_ok_fg"])
            self.root.after(2000, lambda: bt.config(
                text="📋  Copiar", bg=C["copy_btn"], fg=C["copy_fg"]
            ))

        btn_copy.config(command=_copiar)
        btn_copy.bind("<Enter>", lambda e: btn_copy.config(bg=C["accent"]))
        btn_copy.bind("<Leave>", lambda e: btn_copy.config(bg=C["copy_btn"]))

        # Embute o frame no Text widget
        self.chat_area.insert(tk.END, "\n")
        self.chat_area.window_create(tk.END, window=frame, padx=0, pady=0)
        self.chat_area.insert(tk.END, "\n")

    # ──────────────────────────────────────────
    # ENVIO E PROCESSAMENTO
    # ──────────────────────────────────────────
    def _on_enter(self, event):
        """Enter envia; Shift+Enter insere nova linha."""
        if not event.state & 0x1:  # sem Shift
            self._enviar_mensagem()
            return "break"

    def _enviar_mensagem(self, event=None):
        texto = self.user_input.get("1.0", tk.END).strip()
        if self._placeholder_on or not texto:
            if self.arquivo_anexado_atual:
                texto = ""
            else:
                return

        # Exibe mensagem do usuário
        self._renderizar_resposta(texto, is_meg=False)

        # Limpa input
        self.user_input.delete("1.0", tk.END)
        self._set_placeholder()

        # Monta pergunta com anexo se houver
        if self.arquivo_anexado_atual:
            pergunta_envio = f"{texto}\n\n[Arquivo Anexado pelo Usuário com caminho: {self.arquivo_anexado_atual}]"
            self.arquivo_anexado_atual = None
        else:
            pergunta_envio = texto

        # Desativa input enquanto processa
        self.user_input.config(state="disabled")
        self._btn_send.config(state="disabled", bg=C["fg_dim"])
        self._start_thinking()

        threading.Thread(
            target=self._processar_pergunta,
            args=(pergunta_envio,),
            daemon=True
        ).start()

    def _processar_pergunta(self, pergunta: str):
        caca_informacoes(pergunta)
        mensagens = montar_mensagens(pergunta, self.historico)
        resposta = obter_resposta_ollama(mensagens)
        self.root.after(0, self._finalizar_resposta, pergunta, resposta)

    def _finalizar_resposta(self, pergunta: str, resposta: str):
        self._stop_thinking()

        if not resposta:
            resposta = "Desculpe, não consegui processar sua pergunta."

        self._renderizar_resposta(resposta, is_meg=True)

        # Reativa input
        self.user_input.config(state="normal")
        self._btn_send.config(state="normal", bg=C["send_btn"])
        self.user_input.focus_set()

        # Histórico
        self.historico.append({"role": "user",      "content": pergunta})
        self.historico.append({"role": "assistant",  "content": resposta})
        salvar_memoria_sessao("\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in self.historico
        ))

        cmd_mem = extrair_memoria(resposta)
        if cmd_mem:
            self.memoria_usuario = atualizar_memoria(self.memoria_usuario, cmd_mem)
            salvar_memoria_usuario(self.memoria_usuario)

    # ──────────────────────────────────────────
    # ANEXAR ARQUIVO
    # ──────────────────────────────────────────
    def _anexar_arquivo(self):
        pop = tk.Toplevel(self.root)
        pop.title("Anexar")
        pop.geometry("300x130")
        pop.configure(bg=C["bg"])
        pop.transient(self.root)
        pop.grab_set()
        pop.resizable(False, False)

        tk.Label(pop, text="Origem do arquivo:", bg=C["bg"], fg=C["fg"],
                 font=FONT_UI).pack(pady=(16, 8))

        btn_row = tk.Frame(pop, bg=C["bg"])
        btn_row.pack()

        def _local():
            pop.destroy()
            caminho = filedialog.askopenfilename(title="Selecionar arquivo")
            if caminho:
                self.arquivo_anexado_atual = caminho
                self._adicionar_mensagem_sistema(f"📎 Arquivo: {Path(caminho).name}")

        def _indexado():
            pop.destroy()
            self._escolher_indexado()

        for txt, cmd, cor in [
            ("📁  Arquivo Local", _local,    C["accent"]),
            ("🧠  Módulo Meg",    _indexado, "#6b3fa0"),
        ]:
            b = tk.Button(btn_row, text=txt, command=cmd, bg=cor, fg="white",
                          font=("Segoe UI", 10), relief=tk.FLAT, bd=0,
                          padx=12, pady=6, cursor="hand2")
            b.pack(side=tk.LEFT, padx=6)

    def _escolher_indexado(self):
        import json
        from megconfig.learning.module_manager import INDEX_FILE
        modulos = []
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                modulos = [m["name"] for m in data.get("modules", [])]
        except Exception:
            pass

        if not modulos:
            messagebox.showinfo("Sem Módulos", "A Meg ainda não possui módulos indexados.")
            return

        pop2 = tk.Toplevel(self.root)
        pop2.title("Módulo")
        pop2.geometry("360x280")
        pop2.configure(bg=C["bg"])
        pop2.transient(self.root)
        pop2.grab_set()

        tk.Label(pop2, text="Selecione o módulo:", bg=C["bg"], fg=C["fg"],
                 font=FONT_UI).pack(pady=(12, 4))

        lista = tk.Listbox(pop2, bg=C["bg_input"], fg=C["fg"], font=FONT_UI,
                           selectbackground=C["accent"], relief=tk.FLAT, bd=0,
                           highlightthickness=1, highlightbackground=C["border"])
        lista.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)
        for m in modulos:
            lista.insert(tk.END, m)

        def _confirmar():
            sel = lista.curselection()
            if not sel:
                return
            nome = lista.get(sel[0])
            pop2.destroy()
            import os
            base = os.path.dirname(INDEX_FILE)
            know = os.path.join(base, "modules", nome, "knowledge.json")
            self.arquivo_anexado_atual = know
            self._adicionar_mensagem_sistema(f"🧠 Módulo anexado: {nome}")

        tk.Button(pop2, text="Confirmar", command=_confirmar,
                  bg=C["accent"], fg="white", font=FONT_UI,
                  relief=tk.FLAT, bd=0, padx=14, pady=6,
                  cursor="hand2").pack(pady=10)

    # ──────────────────────────────────────────
    # APRENDER DOCUMENTO
    # ──────────────────────────────────────────
    def _iniciar_aprendizado(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar documento",
            filetypes=[("Documentos", "*.pdf *.docx *.txt"), ("Todos", "*.*")]
        )
        if not caminho:
            return

        nome = simpledialog.askstring("Tópico", "Nome do módulo de aprendizado:",
                                      initialvalue=Path(caminho).stem)
        if not nome:
            nome = Path(caminho).stem

        self._adicionar_mensagem_sistema(f"📚 Iniciando aprendizado: {Path(caminho).name}...")

        def _thread():
            try:
                from megconfig.learning.book_learning import learn_from_file
                ok = learn_from_file(caminho, nome, "Aprendido via UI.")
                msg = f"✅ Módulo '{nome}' gravado na memória." if ok else "⚠️ Arquivo inválido ou biblioteca ausente."
            except Exception as ex:
                msg = f"⚠️ Erro no aprendizado: {ex}"
            self.root.after(0, self._adicionar_mensagem_sistema, msg)

        threading.Thread(target=_thread, daemon=True).start()

    # ──────────────────────────────────────────
    # FECHAR
    # ──────────────────────────────────────────
    def _fechar(self):
        self.root.destroy()


if __name__ == "__main__":
    MegInterface()