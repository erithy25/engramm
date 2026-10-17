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
         (str(ROOT / "engramm" / "app" / "web"), "engramm/app/web"),
         # the tokenizers of the Sela-1 and Sela-2 networks (engramm/lm/sela.py; the weights ship beside the server,
         # in models/; a Sela-2 weights file names its tokenizer by file name and SHA-256)
         (str(ROOT / "data" / "lm_tokenizer.json"), "data")]
if (ROOT / "data" / "lm2_tokenizer.json").exists():
    datas.append((str(ROOT / "data" / "lm2_tokenizer.json"), "data"))
# the confidence model for answers from the network channels (experiments/atlas_calib.py)
if (ROOT / "engramm" / "web" / "atlas_calib.json").exists():
    datas.append((str(ROOT / "engramm" / "web" / "atlas_calib.json"), "engramm/web"))
hidden = (collect_submodules("engramm.chat") + collect_submodules("engramm.kb") + collect_submodules("engramm.nlp")
          + collect_submodules("engramm.app") + collect_submodules("engramm.web") + ["engramm.lm.chat", "engramm.lm.semantic", "engramm.lm.stream",
                                                 "engramm.lm.tokenizer", "engramm.lm.dashboard", "engramm.lm.sela",
                                                 "engramm.lm.sela_chat", "engramm.lm.chat_format"])

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
# UTF-8 mode: open() and the standard streams use UTF-8 on every system. A frozen app ignores PYTHONUTF8 and, on Windows,
# would otherwise read text in the code page (cp1252), which broke loading the lite pack (17 Oct 2026).
options = [("X utf8", None, "OPTION")]
exe = EXE(pyz, a.scripts, options, exclude_binaries=True, name="engramm-server", console=True, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="engramm-server")
