# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# Build datas list conditionally based on what files exist
# PyInstaller runs from the directory containing the spec file
datas_list = [('yapmetasploitgui250.png', '.')]
if os.path.exists('icon.png'):
    datas_list.append(('icon.png', '.'))
if os.path.exists('yaplab.png'):
    datas_list.append(('yaplab.png', '.'))

a = Analysis(
    ['core/metasploit_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pystray',
        'threading',
        'queue',
        'subprocess',
        'shutil',
        'pathlib',
        're',
        'json',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # Not needed
        'numpy',  # Not needed (unless PIL requires it)
        'scipy',  # Not needed
        'pandas',  # Not needed
        'IPython',  # Not needed
        'jupyter',  # Not needed
        'notebook',  # Not needed
        'pytest',  # Not needed
        'setuptools',  # Not needed at runtime
        'distutils',  # Not needed at runtime
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='yap-metasploit-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols to reduce size and improve startup
    upx=False,  # UPX can slow startup, keep False
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,  # Strip symbols to reduce size
    upx=False,  # UPX can slow startup
    upx_exclude=[],
    name='yap-metasploit-gui',
)

