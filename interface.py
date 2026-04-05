# =====================================================================
# interface.py - Interface Gráfica da Meg com Modo Voz Completo
# =====================================================================
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import time
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


class MegInterface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧠 Meg - Assistente Pessoal do Pedro Arthur")
        self.root.geometry("980x740")
        self.root.configure(bg="#1e1e1e")

        # === Variáveis de controle de voz ===
        self.voz = None
        self.voz_ativa = False
        self.esta_falando = False

        # Tenta carregar o módulo de voz
        try:
            import voz
            self.voz = voz
            self.voz_ativa = True
            print("✅ Módulo de voz carregado com sucesso!")
        except ImportError as e:
            print(f"⚠️ Módulo de voz não encontrado: {e}")
            self.voz_ativa = False

        # === Interface ===
        self.criar_interface()

        # Estado do chat
        self.historico: List[Dict[str, str]] = []
        self.memoria_usuario = carregar_memoria_usuario()

        # Saudação inicial com voz
        self.adicionar_mensagem("Sistema", "Meg está online! Olá, Pedro Arthur 👋", "#00ffaa")
        if self.voz_ativa:
            threading.Thread(target=self.falar, args=("Olá Pedro Arthur, estou pronta para ajudar!",), daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.fechar)
        self.root.mainloop()

    def criar_interface(self):
        # Área de chat
        self.chat_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state='disabled',
            font=("Segoe UI", 11),
            bg="#2d2d2d",
            fg="#e0e0e0",
            padx=12,
            pady=12
        )
        self.chat_area.pack(padx=12, pady=12, fill=tk.BOTH, expand=True)

        # Frame de entrada + botões
        input_frame = tk.Frame(self.root, bg="#1e1e1e")
        input_frame.pack(fill=tk.X, padx=12, pady=8)

        # Campo de texto
        self.user_input = tk.Entry(
            input_frame,
            font=("Segoe UI", 12),
            bg="#3d3d3d",
            fg="#ffffff",
            insertbackground="#00ddff",
            relief=tk.FLAT,
            bd=5
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.user_input.bind("<Return>", self.enviar_mensagem)

        # Botão Enviar
        send_btn = tk.Button(
            input_frame,
            text="Enviar",
            command=self.enviar_mensagem,
            bg="#0099ff",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=10,
            relief=tk.FLAT,
            pady=8
        )
        send_btn.pack(side=tk.RIGHT, padx=(0, 8))

        # Botão de Microfone (Voz)
        self.mic_btn = tk.Button(
            input_frame,
            text="🎤 Falar",
            command=self.toggle_voz_entrada,
            bg="#ff4444" if not self.voz_ativa else "#00cc66",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=12,
            relief=tk.FLAT,
            pady=8,
            state="normal" if self.voz_ativa else "disabled"
        )
        self.mic_btn.pack(side=tk.RIGHT)

        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Pronto" if self.voz_ativa else "Voz desabilitada - sem módulo voz.py",
            bg="#1e1e1e",
            fg="#aaaaaa",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=4)

    def adicionar_mensagem(self, remetente: str, texto: str, cor: str = "#ffffff"):
        self.chat_area.config(state='normal')
        tag = "meg" if remetente == "Meg" else "usuario"
        self.chat_area.insert(tk.END, f"{remetente}: ", tag)
        self.chat_area.insert(tk.END, f"{texto}\n\n")
        
        self.chat_area.tag_config("meg", foreground="#00ffcc", font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_config("usuario", foreground="#ffcc66", font=("Segoe UI", 11, "bold"))
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def falar(self, texto: str):
        """Função segura para falar com voz"""
        if not self.voz_ativa or not self.voz or not texto:
            return

        self.esta_falando = True
        self.root.after(0, self.atualizar_status, "Meg está falando... 🔊")

        try:
            self.voz.falar(texto)
        except Exception as e:
            print(f"Erro ao falar: {e}")
        finally:
            self.esta_falando = False
            self.root.after(0, self.atualizar_status, "Pronto")

    def atualizar_status(self, texto: str):
        self.status_label.config(text=texto)

    def enviar_mensagem(self, event=None):
        pergunta = self.user_input.get().strip()
        if not pergunta:
            return

        self.adicionar_mensagem("Você", pergunta)
        self.user_input.delete(0, tk.END)

        threading.Thread(
            target=self.processar_pergunta,
            args=(pergunta,),
            daemon=True
        ).start()

    def processar_pergunta(self, pergunta: str):
        """Processa a pergunta e gera resposta com voz automática"""
        caca_informacoes(pergunta)
        
        mensagens = montar_mensagens(pergunta, self.historico)
        resposta = obter_resposta_ollama(mensagens)

        # Atualiza interface + voz
        self.root.after(0, self.finalizar_resposta, pergunta, resposta)

    def finalizar_resposta(self, pergunta: str, resposta: str):
        if not resposta:
            resposta = "Desculpe, não consegui processar sua pergunta."

        self.adicionar_mensagem("Meg", resposta)

        # Atualiza histórico
        self.historico.append({"role": "user", "content": pergunta})
        self.historico.append({"role": "assistant", "content": resposta})

        salvar_memoria_sessao("\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in self.historico
        ))

        # Atualiza memória do usuário
        cmd_mem = extrair_memoria(resposta)
        if cmd_mem:
            self.memoria_usuario = atualizar_memoria(self.memoria_usuario, cmd_mem)
            salvar_memoria_usuario(self.memoria_usuario)

        # === VOZ AUTOMÁTICA NA RESPOSTA ===
        if self.voz_ativa:
            threading.Thread(target=self.falar, args=(resposta,), daemon=True).start()

    # ====================== RECONHECIMENTO DE VOZ ======================
    def toggle_voz_entrada(self):
        """Ativa o microfone para ouvir o usuário"""
        if not self.voz_ativa or self.esta_falando:
            return

        self.mic_btn.config(bg="#ffaa00", text="🎤 Ouvindo...")
        self.root.after(0, self.atualizar_status, "Ouvindo... Fale agora!")

        threading.Thread(target=self.ouvir_usuario, daemon=True).start()

    def ouvir_usuario(self):
        """Captura voz do microfone e envia como pergunta"""
        if not self.voz or not hasattr(self.voz, 'ouvir'):
            self.root.after(0, self.finalizar_voz_entrada, "Erro: Função ouvir() não encontrada no módulo voz.")
            return

        try:
            texto = self.voz.ouvir()   # Assume que seu módulo voz tem .ouvir()

            if texto and texto.strip():
                self.root.after(0, self.processar_voz_recebida, texto)
            else:
                self.root.after(0, self.finalizar_voz_entrada, "Não entendi o que você disse. Tente novamente.")
        except Exception as e:
            self.root.after(0, self.finalizar_voz_entrada, f"Erro no reconhecimento de voz: {str(e)}")

    def processar_voz_recebida(self, texto: str):
        """Processa o texto reconhecido por voz"""
        self.adicionar_mensagem("Você (voz)", texto)
        self.finalizar_voz_entrada()
        self.processar_pergunta(texto)   # Reutiliza a mesma lógica

    def finalizar_voz_entrada(self, mensagem_status: str = "Pronto"):
        self.mic_btn.config(bg="#00cc66", text="🎤 Falar")
        self.atualizar_status(mensagem_status)

    def fechar(self):
        print("Encerrando Meg...")
        if self.esta_falando and self.voz and hasattr(self.voz, 'parar'):
            try:
                self.voz.parar()
            except:
                pass
        self.root.destroy()


if __name__ == "__main__":
    MegInterface()