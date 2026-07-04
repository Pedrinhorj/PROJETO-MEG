@echo off
chcp 65001 >nul
title Instalador - Assistente MEG

:: 1. FORÇA O TERMINAL A TRABALHAR NA PASTA DESTE ARQUIVO
cd /d "%~dp0"

echo ===================================================
echo     Instalador Automatizado - Assistente MEG
echo ===================================================
echo.

:: 2. Verifica e instala o Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python nao encontrado. Iniciando instalacao...
    winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    echo.
    echo [AVISO] O Python foi instalado. Por favor, feche esta janela e execute o instalador novamente para continuar.
    pause
    exit /b
) else (
    echo [+] Python detectado.
)

:: 3. Verifica e instala o Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama nao encontrado. Baixando e instalando...
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    echo [+] Ollama instalado com sucesso.
) else (
    echo [+] Ollama detectado.
)

:: 4. Inicia o servidor Ollama em segundo plano
echo [*] Iniciando o servidor local do Ollama...
start /B ollama serve >nul 2>&1
timeout /t 5 /nobreak >nul

:: 5. Instala dependencias do Python (Usando python -m pip)
echo [*] Instalando dependencias do projeto...
python -m pip install -r requirements.txt >nul

:: 6. Compila o Modelfile
echo [*] Baixando o modelo base e compilando a mente da MEG...
echo Isso pode demorar alguns minutos dependendo da conexao com a internet.
ollama create meg -f Modelfile

:: 7. Inicia a interface
echo ===================================================
echo [+] Instalacao concluida com sucesso!
echo [*] Iniciando a MEG...
echo ===================================================
python run_meg.py

pause