"""Entry point of the frozen ENGRAMM server (the desktop app's sidecar).

Same as ``python -m engramm.app``; the app starts it with ``--desktop --pack DIR --memory FILE``.
"""

import multiprocessing
import sys

from engramm.app.server import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
