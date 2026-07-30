# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for the NovaCaption desktop bundle."""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

ROOT = Path(SPECPATH)
RUNTIME_DIR = Path(os.environ.get("VIDEOCAPTIONER_DESKTOP_RUNTIME_DIR", ROOT / "build" / "desktop-runtime"))
APP_ICON = ROOT / "resource" / "assets" / (
    "novacaption.icns" if sys.platform == "darwin" else "novacaption.ico"
)


def _data(src: Path, dest: str):
    return (str(src), dest)


datas = [
    _data(ROOT / "resource" / "assets", "resource/assets"),
    _data(ROOT / "resource" / "fonts", "resource/fonts"),
    _data(ROOT / "resource" / "subtitle_style", "resource/subtitle_style"),
    _data(ROOT / "resource" / "translations", "resource/translations"),
    _data(ROOT / "videocaptioner" / "core" / "prompts", "videocaptioner/core/prompts"),
    _data(ROOT / "LICENSE", "."),
    _data(ROOT / "NOTICE.md", "."),
]

runtime_bin = RUNTIME_DIR / "resource" / "bin"
if runtime_bin.exists():
    datas.append(_data(runtime_bin, "resource/bin"))

hiddenimports = [
    "PyQt5",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.QtMultimedia",
    "PyQt5.QtMultimediaWidgets",
    "PyQt5.QtSvg",
    "PyQt5.sip",
    "openai",
    "requests",
    "edge_tts",
    "diskcache",
    "yt_dlp",
    "modelscope",
    "psutil",
    "json_repair",
    "langdetect",
    "pydub",
    "tenacity",
    "GPUtil",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "fontTools",
    "fontTools.ttLib",
]
hiddenimports += collect_submodules("qfluentwidgets")

excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "numpy.testing",
    "pytest",
    "pyright",
    "ruff",
    "test",
    "unittest",
]

a = Analysis(
    [str(ROOT / "videocaptioner" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name="NovaCaption",
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
    icon=str(APP_ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NovaCaption",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="NovaCaption.app",
        bundle_identifier="com.yuhou.novacaption",
        icon=str(ROOT / "resource" / "assets" / "novacaption.icns"),
        info_plist={
            "CFBundleName": "NovaCaption",
            "CFBundleDisplayName": "NovaCaption",
            "NSHighResolutionCapable": True,
        },
    )
