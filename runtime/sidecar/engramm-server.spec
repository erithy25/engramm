# PyInstaller spec of the ENGRAMM server sidecar (one folder: fast start, no unpacking per launch).
#   pyinstaller --noconfirm --distpath DIST --workpath WORK runtime/sidecar/engramm-server.spec
# The result DIST/engramm-server/ goes into the app as resources/sidecar/.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]

# engramm is a namespace package, so its data files are listed here: the conversation bank, the
# realizer's verb list and the built chat page
datas = [(str(ROOT / "engramm" / "chat" / "conv_bank.json"), "engramm/chat"),
         (str(ROOT / "engramm" / "chat" / "letters.json"), "engramm/chat"),
         (str(ROOT / "engramm" / "web" / "feeds.json"), "engramm/web"),
         (str(ROOT / "engramm" / "chat" / "data"), "engramm/chat/data"),
         (str(ROOT / "engramm" / "app" / "web"), "engramm/app/web")]
hidden = (collect_submodules("engramm.chat") + collect_submodules("engramm.kb") + collect_submodules("engramm.nlp")
          + collect_submodules("engramm.app") + collect_submodules("engramm.web") + ["engramm.lm.chat", "engramm.lm.semantic", "engramm.lm.stream",
                                                 "engramm.lm.tokenizer", "engramm.lm.dashboard"])

a = Analysis(
    [str(ROOT / "runtime" / "sidecar" / "engramm_server.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "matplotlib", "pandas", "torch", "faiss", "sklearn", "pyarrow", "IPython", "pytest",
              "engramm.chat.studio"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="engramm-server", console=True, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="engramm-server")
