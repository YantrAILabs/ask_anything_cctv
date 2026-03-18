# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Include assets
added_files = [
    ('onsite.ico', '.'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'pystray',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageTk',
        'cv2',
        'numpy',
        'asyncio',
        'websockets.legacy.server',
        'websockets.legacy.client',
        'websockets.legacy',
        'agent_ui',
        'discovery',
        'yantrai_tunnel',
        'server_link',
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
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OnsiteAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['onsite.ico'],
)
