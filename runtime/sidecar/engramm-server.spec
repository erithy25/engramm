# PyInstaller spec of the ENGRAMM server sidecar (one folder: fast start, no unpacking per launch).
#   pyinstaller --noconfirm --distpath DIST --workpath WORK runtime/sidecar/engramm-server.spec
# The result DIST/engramm-server/ goes into the app as resources/sidecar/.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]

# engramm is a namespace package, so PyInstaller does not collect its data files by itself: every
# file next to the code goes in (conversation bank, verb list, word lists and models of
# engramm/understand, the how-to and Wikibooks indexes of engramm/know, the shelf release keys, the
# built chat page). Listing them one by one once left out understand/ and know/: the desktop app
# then answered practical questions with generic advice (runtime/sidecar/smoke_test.py checks it).
datas = sorted((str(f), str(f.parent.relative_to(ROOT)))
               for f in (ROOT / "engramm").rglob("*")
               if f.is_file() and f.suffix not in (".py", ".pyc") and "__pycache__" not in f.parts)
hidden = (collect_submodules("engramm.chat") + collect_submodules("engramm.kb") + collect_submodules("engramm.nlp")
          + collect_submodules("engramm.app") + collect_submodules("engramm.web") + collect_submodules("engramm.understand")
          + collect_submodules("engramm.know") + collect_submodules("engramm.learn")
          + ["engramm.lm.chat", "engramm.lm.semantic", "engramm.lm.stream", "engramm.lm.tokenizer", "engramm.lm.dashboard"])

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
# Python's UTF-8 mode in the frozen server, however it is started: on Windows text files would
# otherwise be read in the ANSI code page, and the pack's UTF-8 JSON fails to load
options = [("X utf8", None, "OPTION")]
exe = EXE(pyz, a.scripts, options, exclude_binaries=True, name="engramm-server", console=True, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="engramm-server")
