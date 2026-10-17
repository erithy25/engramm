# PyInstaller spec of the ENGRAMM server sidecar (one folder: fast start, no unpacking per launch).
#   pyinstaller --noconfirm --distpath DIST --workpath WORK runtime/sidecar/engramm-server.spec
# The result DIST/engramm-server/ goes into the app as resources/sidecar/.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]

# engramm is a namespace package, so PyInstaller collects none of its data files by itself. Every file in the
# package that is not code goes in, at the same place: the conversation bank, the letters, the realizer's verbs, the
# lexicons and the frame model of engramm/understand, the how-to index of engramm/know, the feeds, the release keys
# and the built chat page. Code finds them next to itself (Path(__file__).parent / ...); a file left out does not
# fail loudly — the frozen app then answered "My laptop is broken." with "what's a laptop?" (builds up to 17 Oct 2026).
PACKAGE_DATA = sorted(f for f in (ROOT / "engramm").rglob("*")
                      if f.is_file() and f.suffix not in (".py", ".pyc") and "__pycache__" not in f.parts
                      and f.name != ".DS_Store")
datas = [(str(f), str(f.parent.relative_to(ROOT))) for f in PACKAGE_DATA]
# the tokenizers of the Sela-1 and Sela-2 networks (engramm/lm/sela.py; the weights ship beside the server, in models/;
# a Sela-2 weights file names its tokenizer by file name and SHA-256)
datas.append((str(ROOT / "data" / "lm_tokenizer.json"), "data"))
if (ROOT / "data" / "lm2_tokenizer.json").exists():
    datas.append((str(ROOT / "data" / "lm2_tokenizer.json"), "data"))
hidden = (collect_submodules("engramm.chat") + collect_submodules("engramm.kb") + collect_submodules("engramm.nlp")
          + collect_submodules("engramm.understand") + collect_submodules("engramm.know") + collect_submodules("engramm.learn")
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
