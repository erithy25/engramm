"""Checks the static website before publishing: every local file a page references exists, no
external scripts or styles, no trackers.

    python3 site/check_site.py site
"""

import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    problems = []
    for page in root.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        for ref in re.findall(r'(?:src|href)="([^"#]+)"', html):
            if ref.startswith(("http://", "https://", "mailto:")):
                continue
            if not (root / ref).exists():
                problems.append(f"{page.name}: missing {ref}")
        for ext in re.findall(r'<(?:script|link)[^>]+(?:src|href)="(https?://[^"]+)"', html):
            problems.append(f"{page.name}: external resource {ext}")
        if re.search(r"google-analytics|googletagmanager|gtag\(|plausible|matomo", html):
            problems.append(f"{page.name}: tracker")
    for p in problems:
        print(p)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
