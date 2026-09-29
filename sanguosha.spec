from pathlib import Path

root = Path(SPECPATH)
datas = [
    (str(root / "assets"), "assets"),
    (str(root / "data"), "data"),
    (str(root / "config"), "config"),
]
a = Analysis(
    [str(root / "src" / "sanguosha" / "__main__.py")],
    pathex=[str(root / "src")], binaries=[], datas=datas,
    hiddenimports=["websockets", "websockets.asyncio.client"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Sanguosha",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="Sanguosha-Windows-x64")
