# -*- mode: python ; coding: utf-8 -*-
import os

# Pasta raiz do projeto
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['run_meg.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Inclui o Modelfile para leitura de parâmetros pelo código
        ('Modelfile', '.'),
        # Inclui toda a pasta megconfig (módulos de aprendizado/memória)
        ('megconfig', 'megconfig'),
        # Inclui memória persistente se já existir
        ('ArmazenamentoMemoria', 'ArmazenamentoMemoria'),
    ],
    hiddenimports=[
        # Ollama
        'ollama',
        'ollama._client',
        'ollama._types',
        # DuckDuckGo
        'duckduckgo_search',
        'duckduckgo_search.duckduckgo_search',
        # Módulos internos do projeto
        'megconfig',
        'megconfig.core',
        'megconfig.core.meg_brain',
        'megconfig.learning',
        'megconfig.learning.book_learning',
        'megconfig.learning.knowledge_extractor',
        'megconfig.learning.module_manager',
        'megconfig.retrieval',
        'megconfig.retrieval.memory_search',
        'megconfig.memory',
        # PDF
        'PyPDF2',
        # DOCX
        'docx',
        # Tkinter (geralmente já incluso, mas por garantia)
        'tkinter',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        # Stdlib que às vezes precisa de ajuda
        'json',
        'threading',
        'pathlib',
        'logging',
        'datetime',
        're',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui o que não precisamos para manter o exe menor
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'notebook',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Meg',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icone.ico' if os.path.exists('icone.ico') else None,
    version_file=None,
)
