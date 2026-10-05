"""Build the Wikibooks advice index (V3): practical steps from a few freely licensed how-to books, in English and
German, each with its book and page as the source.

    python -m experiments.wikibooks_build --dumps /dev/shm/engramm/wb --out engramm/know/data/wikibooks.json.gz

Reads the pages-articles dumps (enwikibooks, dewikibooks), keeps the pages of the books in BOOKS, turns their wiki
text into plain sentences and keeps the steps: list items and sentences that start with an instruction ("Remove the
wheel", "Kühle die Brandwunde"). A page enters with at least two steps. Licence: Wikibooks, CC BY-SA 4.0 — every
answer shows the book and page.
"""
from __future__ import annotations

import argparse
import bz2
import gzip
import json
import re
from pathlib import Path
from xml.etree.ElementTree import iterparse

# book → (language, kind, words that name the book's topic in a conversation)
BOOKS = {
    "First Aid": ("en", "HEALTH", []),
    "Bicycles": ("en", "HOME", ["bike", "bicycle", "cycling", "cycle"]),
    "Automobile Repair": ("en", "HOME", ["car", "engine", "vehicle", "automobile"]),
    "Knots": ("en", "HOME", ["knot", "rope", "tie"]),
    "Erste Hilfe": ("de", "HEALTH", []),
    "Erste Hilfe im Gelände": ("de", "HEALTH", []),
    "Der Medicus - Ein Ratgeber für die Hausapotheke": ("de", "HEALTH", []),
    "Survival": ("de", "HOME", ["draußen", "wald", "wildnis", "zelt", "camping"]),
}
NOT_ADVICE = re.compile(r"^(?:consent|what needs to be done\?|kurs .*|verpflichtungen .*|.*(?:catalog|katalog).*|"
                        r"equipment and accessories|history|geschichte)$", re.I)
_UNUSED = {
}
SKIP_SEG = re.compile(r"^(?:maintenance and repair|tools and supplies|appendix.*|introduction|external links|"
                      r"inhaltsverzeichnis|einleitung|vorwort|literatur|weblinks|autoren|druckversion)$", re.I)
IMPERATIVE_EN = re.compile(r"^(?:Remove|Check|Make sure|Use|Apply|Place|Put|Keep|Turn|Clean|Wash|Rinse|Cool|Cover|Call|"
                           r"Do not|Don't|Never|Always|Hold|Press|Lift|Loosen|Tighten|Replace|Inflate|Deflate|Find|"
                           r"Mark|Insert|Pull|Push|Wipe|Dry|Let|Allow|Wait|Open|Close|Disconnect|Connect|Attach|"
                           r"Fill|Drain|Start|Stop|Seek|Get|Give|Raise|Elevate|Lay|Sit|Avoid|Try|Take|Pour|Spin|"
                           r"Slide|Fit|Align|Adjust|Test|Inspect|Look|Unscrew|Screw|Release|Locate|Run|Wrap|Tie)\b")
IMPERATIVE_DE = re.compile(r"^(?:\w+e |\w+en Sie |Nicht |Niemals |Immer |Sofort |Bei |Wenn )|^(?:Kühlen|Lagern|Legen|"
                           r"Rufen|Halten|Drücken|Waschen|Spülen|Decken|Bringen|Trinken|Vermeiden|Achten|Prüfen|"
                           r"Entfernen|Ruhigstellen|Hochlagern|Abdecken|Kühle|Lege|Rufe|Halte|Drücke|Wasche|"
                           r"Spüle|Decke|Bringe|Trinke|Vermeide|Achte|Prüfe|Entferne)\b")


def plain(wt: str) -> str:
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", wt, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    for _ in range(3):
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\{\|.*?\|\}", "", t, flags=re.S)
    t = re.sub(r"\[\[(?:File|Image|Datei|Bild|Category|Kategorie):[^\]]*(?:\[\[[^\]]*\]\][^\]]*)*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+ ([^\]]*)\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\]", "", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return t


def steps(wt: str, lang: str) -> list[str]:
    imp = IMPERATIVE_DE if lang == "de" else IMPERATIVE_EN
    out = []
    for line in plain(wt).splitlines():
        line = line.strip()
        if not line or line.startswith(("=", "|", "!", ":")):
            continue
        is_item = line[:1] in "*#"
        line = re.sub(r"^[*#:;]+\s*", "", line).strip()
        for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", line):
            s = s.strip()
            s = s.replace("&nbsp;", " ").replace("\xa0", " ")
            if not (20 <= len(s) <= 220) or re.search(r"https?://|\b(?:ISBN|siehe auch|see also)\b|[{}|#]|\w/\w", s):
                continue
            if imp.match(s) or (is_item and re.match(r"^[A-ZÄÖÜ]", s) and len(s.split()) >= 4):
                s = s if s[-1] in ".!?" else s + "."
                if s not in out:
                    out.append(s)
    instr = re.compile(r"\b(?:should|must|make sure|do not|don't|never|always|muss|müssen|sollte|sollten|soll|nicht|"
                       r"sofort|umgehend)\b", re.I)
    if not any(imp.match(x) or instr.search(x) for x in out):
        return []                                      # a description or a list of links, not instructions
    return out[:6]


def names(title: str, lang: str) -> list[str]:
    segs = [s for s in title.split("/")[1:] if not SKIP_SEG.match(s.strip())]
    if not segs:
        return []
    last = segs[-1].strip().lower()
    out = [last, re.sub(r"\s*\([^)]*\)", "", last).strip(), re.sub(r"^(?:fixing|mending|adjusting|replacing|checking|cleaning|removing|changing|how to) (?:a |an |the )?",
                        "", last)]
    return list(dict.fromkeys(n for n in out if len(n) > 3))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dumps", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    items = []
    for lang in ("en", "de"):
        books = {b: v for b, v in BOOKS.items() if v[0] == lang}
        for ev, el in iterparse(bz2.open(a.dumps / f"{lang}.xml.bz2"), events=("end",)):
            if not el.tag.endswith("}page"):
                continue
            title = el.find("{*}title").text or ""
            book = title.split("/")[0]
            if book in books and el.find("{*}redirect") is None and "/" in title:
                text = el.find("{*}revision/{*}text").text or ""
                st = steps(text, lang)
                ns = names(title, lang)
                if len(st) >= 2 and ns and not NOT_ADVICE.match(ns[0]):
                    items.append({"title": title, "lang": lang, "kind": books[book][1], "book_words": books[book][2],
                                  "names": ns, "steps": st})
            el.clear()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(items, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {a.out}: {len(items)} pages (en {sum(i['lang'] == 'en' for i in items)}, "
          f"de {sum(i['lang'] == 'de' for i in items)}), {a.out.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    main()
