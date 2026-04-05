# =====================================================================
# voz.py - Módulo de Voz para Meg (Sem Pygame - Usa playsound)
# =====================================================================
import asyncio
import os
import threading
import uuid
from pathlib import Path
from typing import Optional

import edge_tts
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from playsound3 import playsound   # ← Usa playsound3 para compatibilidade com Python 3.1x
import sounddevice as sd
import sys

# Corrige crash de codificação (UnicodeEncodeError) ao rodar com emojis no Windows CMD
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("=== DISPOSITIVOS DE ÁUDIO DISPONÍVEIS ===")
print(sd.query_devices())
print("\nDispositivos de ENTRADA (microfones):")
for i, dev in enumerate(sd.query_devices()):
    if dev['max_input_channels'] > 0:
        print(f"[{i}] {dev['name']}  (canais: {dev['max_input_channels']})")

# ====================== CONFIGURAÇÕES ======================
_BASE_DIR = Path(__file__).resolve().parent
_AUDIO_TEMP = _BASE_DIR / "audio_temp.wav"

VOZ = "pt-BR-FranciscaNeural"

# Lock para evitar reprodução simultânea
_audio_lock = threading.Lock()

# Evento para parar fala
_parar_fala_event = threading.Event()


# ====================== SÍNTESE DE VOZ ======================
async def _falar_async(texto: str) -> None:
    """Gera MP3 com edge-tts e reproduz com playsound."""
    if not texto or not texto.strip():
        return

    output_file = str(_BASE_DIR / f"meg_voz_{uuid.uuid4().hex[:8]}.mp3")

    try:
        communicate = edge_tts.Communicate(texto.strip(), VOZ)
        await communicate.save(output_file)

        print(f"🔊 Meg fala: {texto[:80]}{'...' if len(texto) > 80 else ''}")

        with _audio_lock:
            if _parar_fala_event.is_set():
                return
            playsound(output_file, block=True)   # block=True espera terminar

    except Exception as e:
        print(f"[ERRO] Falha na síntese de voz: {e}")
    finally:
        # Limpeza do arquivo
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
        except OSError:
            pass


def falar(texto: str) -> None:
    """Função principal para falar — segura para uso em threads."""
    if not texto or not texto.strip():
        return

    _parar_fala_event.clear()

    def run_fala():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_falar_async(texto))
        finally:
            loop.close()

    threading.Thread(target=run_fala, daemon=True).start()


def parar_fala() -> None:
    """Para a fala atual (não é 100% instantâneo com playsound, mas ajuda)."""
    _parar_fala_event.set()


# ====================== RECONHECIMENTO DE VOZ (mantido igual) ======================
_modelo_whisper = None
_whisper_lock = threading.Lock()

def _carregar_whisper():
    global _modelo_whisper
    if _modelo_whisper is None:
        with _whisper_lock:
            if _modelo_whisper is None:
                import whisper
                _modelo_whisper = whisper.load_model("base")
                print("✅ Modelo Whisper 'base' carregado.")
    return _modelo_whisper


def ouvir(segundos: int = 6) -> str:
    print("🎤 Ouvindo... (fale agora)")

    try:
        fs = 44100
        # Pegamos a qtde de canais do microfone padrao para nao forçar 1 e pegar a via muda
        device_info = sd.query_devices(sd.default.device[0], 'input')
        canais = int(device_info['max_input_channels']) or 1

        audio_float = sd.rec(int(segundos * fs), samplerate=fs, channels=canais, dtype="float32")
        sd.wait()

        # Mistura estereo pra mono se necessario
        if canais > 1:
            audio_flat = audio_float.mean(axis=1)
        else:
            audio_flat = audio_float.flatten()

        volume = np.abs(audio_flat).mean()
        pico = np.abs(audio_flat).max()
        print(f"[DIAGNÓSTICO] Volume: {volume:.5f} | Pico: {pico:.5f}")

        if pico == 0.0:
            print("❌ ERRO: O áudio está 100% mudo. O Windows bloqueou o acesso do Python ao Microfone em (Configurações > Privacidade > Microfone).")
            return ""

        if volume < 0.005:  # Limiar reduzido ainda mais (de 0.02 para 0.005) porque microfones sem ganho sao super baixos
            print("🔇 Silêncio detectado (niguem falou).")
            return ""

        audio_int16 = (audio_flat * 32767).astype(np.int16)
        write(str(_AUDIO_TEMP), fs, audio_int16)

        print("🧠 Transcrevendo...")
        modelo = _carregar_whisper()
        resultado = modelo.transcribe(str(_AUDIO_TEMP), fp16=False)
        texto = resultado["text"].strip()
        print(f"👤 Você disse: {texto}")
        return texto

    except Exception as e:
        print(f"[ERRO] Reconhecimento de voz: {e}")
        return ""
    finally:
        try:
            if _AUDIO_TEMP.exists():
                _AUDIO_TEMP.unlink()
        except:
            pass


# ====================== MODO CONVERSA CONTÍNUA ======================
# NOTA: Esta função não importa mais o módulo 'meg' diretamente, evitando
# acoplamento circular. O orquestrador (main.py) deve injetar os callbacks.

def modo_conversa_continua(obter_resposta, salvar_pergunta) -> None:
    """
    Modo de voz contínuo — aguarda fala, envia para o agente e responde em voz.

    Args:
        obter_resposta: callable(pergunta, historico) -> str
            Função que chama o agente e retorna a resposta como texto.
        salvar_pergunta: callable(pergunta) -> None
            Função que persiste a pergunta na memória permanente.
    """
    print("🎙️ Modo de voz contínuo ativado.")
    falar("Modo de voz ativado. Pode falar comigo, Pedro Arthur.")

    historico = []

    while True:
        pergunta = ouvir()
        if not pergunta:
            continue

        if any(p in pergunta.lower() for p in ["sair", "parar", "tchau"]):
            falar("Até logo!")
            break

        try:
            salvar_pergunta(pergunta)
            resposta = obter_resposta(pergunta, historico)
            falar(resposta)
            historico.append({"role": "user", "content": pergunta})
            historico.append({"role": "assistant", "content": resposta})
        except Exception as erro:
            print(f"[ERRO] {erro}")
            falar("Desculpe, ocorreu um erro.")


# ====================== EXECUÇÃO ======================
if __name__ == "__main__":
    # Para rodar o modo de voz standalone, injeta os serviços da camada de aplicação
    from meg.application.agent_service import montar_mensagens, obter_resposta_ollama
    from meg.application.memory_service import caca_informacoes, carregar_memoria_permanente

    def _obter_resposta(pergunta: str, historico: list) -> str:
        mem = carregar_memoria_permanente()
        mensagens = montar_mensagens(pergunta, historico, mem)
        return obter_resposta_ollama(mensagens)

    try:
        modo_conversa_continua(
            obter_resposta=_obter_resposta,
            salvar_pergunta=caca_informacoes,
        )
    except KeyboardInterrupt:
        print("\nEncerrado.")
        parar_fala()