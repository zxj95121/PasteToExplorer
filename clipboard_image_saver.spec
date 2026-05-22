# -*- mode: python ; coding: utf-8 -*-
import os

_datas = [
    ('assets/images/logo.png', 'assets/images'),
    ('assets/images/logo0.png', 'assets/images'),
    ('tray_icon.png', '.'),
]
for src, dst in [('assets/zanshang.png', 'assets'), ('zanshang.png', '.')]:
    if os.path.exists(src):
        _datas.append((src, dst))

a = Analysis(
    ['clipboard_image_saver.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        'pystray', 'PIL', 'PIL.Image', 'PIL.ImageGrab', 'PIL.ImageDraw',
        'win32com', 'win32com.client', 'pythoncom',
        'win32gui', 'win32con', 'win32api', 'win32clipboard', 'win32event',
        'customtkinter', 'tkinter',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='PasteToExplorer',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    upx_exclude=[], runtime_tmpdir=None, console=False,
    disable_windowed_traceback=False, argv_emulation=False,
    target_arch='x86_64', codesign_identity=None, entitlements_file=None,
    icon='icon.ico',
)
