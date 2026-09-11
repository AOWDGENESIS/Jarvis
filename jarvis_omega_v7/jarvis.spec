# -*- mode: python ; coding: utf-8 -*-
# JARVIS OMNI v8.0 - PyInstaller Spec
# Ausfuehren: pyinstaller jarvis.spec
# Ergebnis: dist/JARVIS_OMNI/ mit jarvis.exe

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('core', 'core'),
        ('data', 'data'),
        ('docs', 'docs'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'fastapi', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops',
        'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'psutil', 'requests', 'edge_tts', 'pyttsx3',
        'sqlite3', 'aiofiles', 'anyio', 'starlette',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='JARVIS_OMNI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='jarvis_icon.svg',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='JARVIS_OMNI',
)
