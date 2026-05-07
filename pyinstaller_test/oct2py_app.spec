# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for the oct2py test app."""

from PyInstaller.utils.hooks import collect_all, copy_metadata

oct2py_datas, oct2py_binaries, oct2py_hiddenimports = collect_all("oct2py")
kernel_datas, kernel_binaries, kernel_hiddenimports = collect_all("octave_kernel")

# Any package that calls importlib.metadata.version() at import time needs its
# dist-info present in the frozen bundle.  Rather than maintaining a manual
# list, collect metadata for every installed distribution so nothing is missed.
from importlib.metadata import distributions as _distributions

pkg_metadata = []
for _dist in _distributions():
    _name = _dist.metadata.get("Name")
    if _name:
        try:
            pkg_metadata += copy_metadata(_name)
        except Exception:
            pass

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=oct2py_binaries + kernel_binaries,
    datas=oct2py_datas + kernel_datas + pkg_metadata,  # codespell:ignore datas
    hiddenimports=oct2py_hiddenimports + kernel_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,  # codespell:ignore datas
    [],
    name="oct2py_app",
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
