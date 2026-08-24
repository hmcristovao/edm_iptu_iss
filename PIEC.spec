# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH)

datas = [
    (
        str(project_root / "src" / "parametrizacao" / "parametros.txt"),
        "src/parametrizacao",
    ),
]
binaries = []
hiddenimports = [
    "src.moduloII.preparacao",
    "src.moduloII.enriquecimento",
    "src.moduloII.gerar_revisado",
    "src.moduloIII.reassociacao",
    "src.moduloIV.base_imobiliario",
]

for package in ("nicegui",):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

for package in (
    "bs4",
    "Crypto",
    "html5lib",
    "lxml",
    "openpyxl",
    "recordlinkage",
    "xlrd",
):
    hiddenimports += collect_submodules(package)

a = Analysis(
    ["app_nicegui.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PIEC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
