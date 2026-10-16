"""Main text of a web page by rules (the jusText idea, no neural network): split the page into
blocks, drop scripts, navigation, headers, footers, forms and asides, then keep a block when it is
long enough, mostly not links and has a natural share of function words.

    paragraphs(html_text) -> list[str]
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_SKIP = frozenset("script style noscript template svg canvas nav header footer aside form button select option "
                  "iframe object embed menu dialog figure figcaption".split())
_BLOCK = frozenset("p div li h1 h2 h3 h4 h5 h6 td th dd dt blockquote pre article section main br tr table ul ol "
                   "dl address".split())
_STOP = frozenset("""the of and to a in is that for it as was with be by on not he i this are or his from at which
but have an they you were had her she there been one all we their has would when who will more if no out so said
what up its about into than them can only other new some could time these two may then do first any my now such like
our over man me even most made after also did many before must through back years where much your way well down
should because each just those people how too little state good very make world still own see men work long get here
between both life being under never day same another know while last might us great old year off come since against
go came right used take three""".split())
_BAD_CLASS = re.compile(r"(?:^|[\s_-])(?:nav|menu|footer|header|sidebar|cookie|banner|advert|ads?|promo|social|share|"
                        r"related|comment|subscribe|newsletter|breadcrumb|popup|modal)(?:$|[\s_-])", re.I)


# footnote and edit markers ("[12]", "[a]", "[citation needed]", "[edit]") are not text
_MARKERS = re.compile(r"\s*\[(?:\d{1,4}|[a-z]|note \d+|nb \d+|citation needed|clarification needed|edit|"
                      r"when\?|who\?|according to whom\?|dubious – discuss|failed verification)\]", re.I)


class _Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.stack: list[tuple[str, bool]] = []
        self.blocks: list[tuple[str, int, str]] = []    # (text, link chars, tag)
        self.cur: list[str] = []
        self.link_chars = 0
        self.in_a = 0
        self.tag = "p"
        self.title = ""
        self._in_title = False

    def _flush(self):
        text = " ".join("".join(self.cur).split())
        if text:
            self.blocks.append((text, self.link_chars, self.tag))
        self.cur, self.link_chars = [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        bad = bool(_BAD_CLASS.search(f"{a.get('class', '')} {a.get('id', '')} {a.get('role', '')}")) or \
            a.get("aria-hidden") == "true" or "display:none" in (a.get("style") or "").replace(" ", "")
        if tag == "title":
            self._in_title = True
        if tag in _SKIP or (bad and tag in ("div", "section", "ul", "aside", "span", "p", "table")):
            self.stack.append((tag, True))
            self.skip += 1
            return
        if tag in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source",
                   "track", "wbr"):
            if tag == "br":
                self.cur.append(" ")
            return
        self.stack.append((tag, False))
        if tag in _BLOCK:
            self._flush()
            self.tag = tag
        if tag == "a":
            self.in_a += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        while self.stack:
            t, skipped = self.stack.pop()
            if skipped:
                self.skip -= 1
            if t == "a" and not skipped:
                self.in_a = max(0, self.in_a - 1)
            if t == tag:
                break
        if tag in _BLOCK:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if self.skip:
            return
        self.cur.append(data)
        if self.in_a:
            self.link_chars += len(data.strip())


def paragraphs(page: str, min_len: int = 60, max_link_density: float = 0.3, min_stop: float = 0.22) -> list[str]:
    """The main-text paragraphs of an HTML page, in page order."""
    p = _Blocks()
    try:
        p.feed(page)
        p.close()
    except Exception:                       # broken markup: keep what was read
        pass
    p._flush()
    out = []
    for text, links, tag in p.blocks:
        text = _MARKERS.sub("", html.unescape(text)).strip()
        if tag in ("h1", "h2", "h3") and 15 <= len(text) <= 150 and links / max(1, len(text)) < 0.5:
            out.append(text)                # a heading keeps the reading order
            continue
        if len(text) < min_len:
            continue
        if links / max(1, len(text)) > max_link_density:
            continue
        words = re.findall(r"[a-zA-Z']+", text.lower())
        if len(words) < 8:
            continue
        stop = sum(w in _STOP for w in words) / len(words)
        if stop < min_stop:
            continue
        out.append(text)
    # headings with no paragraph after them are noise
    cleaned = []
    for i, t in enumerate(out):
        if len(t) <= 150 and (i + 1 >= len(out) or len(out[i + 1]) <= 150) and not t.endswith((".", "!", "?")):
            continue
        cleaned.append(t)
    return cleaned


def page_title(page: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    return " ".join(html.unescape(m.group(1)).split()) if m else ""


# ---------------------------------------------------------------------------
# the reference zone at the end of a Wikipedia article's plain text
# ---------------------------------------------------------------------------

_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9\"“„(\[])")
# titles: always a name after them
_TITLES = frozenset("mr mrs ms messrs dr prof st mt ft jr sr capt col lt sgt cmdr adm rev hon gen gov sen rep".split())
# short forms whose full stop ends no sentence unless a sentence starts after it, English and German (lower case)
_SHORT = frozenset("""vs etc inc ltd co corp bros no nos vol vols pp ca approx est fig figs dept univ jan feb mar apr jun jul aug
sep sept oct nov dec al bzw ggf inkl max min mio mrd nr str tsd usw vgl sog evtl chr jh jhd hl abs bspw geb gest verh ehem
insb zzgl mind gegr okt dez sek std bd hrsg aufl ff dgl ebd lat griech engl franz ital span""".split())
# the words a sentence starts with — after "SpaceX and X." or "… usw." one does
_STARTERS = frozenset("""the a an he she it they we i you his her its their our this that these those there here in on at by
for from with after before during since until when while although though however but and or so as if because today many
most some all each both other another such according der die das den dem des ein eine einer eines er sie es wir ich man
sein seine ihr ihre dies diese dieser dieses im am vom zum zur auf aus bei mit nach seit von vor während als wenn weil da
doch aber und oder auch heute damit dort hier später danach zudem außerdem jedoch allerdings""".split())
# what a German ordinal stands before ("am 6. März 1902", "im 20. Jahrhundert", "1. FC Köln")
_ORDINAL_NOUN = re.compile(r"(?:januar|jänner|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember|"
                           r"jahrhunderts?|jahrtausends?|fc|liga|bundesliga|platz|klasse|mal|weltkrieg|staffel|folge|band|"
                           r"kapitel|auflage|runde|spieltag|rang|armee|division|sinfonie|symphonie)\b", re.I)


def split_sentences(text: str) -> list[str]:
    """The sentences of a text. A full stop ends none after an initial ("J. K. Rowling", "z. B.",
    "U.S."), a title or short form ("Dr.", "Mio.", "bzw.") or a German ordinal ("am 6. März 1902",
    "im 20. Jahrhundert"): a sentence cut there ("… written by British author J.", "Mai 1949 wurde
    das Grundgesetz verkündet.") answers nothing. After a single letter or a short form a sentence
    still ends when the next word starts one ("… SpaceX and X. He has been …")."""
    out, start = [], 0
    for m in _BREAK.finditer(text):
        before = text[start:m.start()].split()
        if before and before[-1].endswith(".") and _no_end(before, text[m.end():m.end() + 24]):
            continue
        out.append(text[start:m.start()])
        start = m.end()
    out.append(text[start:])
    return out


def _no_end(before: list[str], after: str) -> bool:
    """The full stop of the last word of ``before`` (followed by ``after``) ends no sentence."""
    core = before[-1].rstrip(".").lstrip("([\"'“„‚*")
    if not core:
        return False
    nxt = re.match(r"[\"'“„(\[]*([^\W\d_]+)", after)
    starts = bool(nxt) and nxt.group(1).lower() in _STARTERS
    if len(core) == 1 and core.isalpha():                       # an initial: "J.", "z.", "B."
        # "… X. He …" ends a sentence; "z. B. Die …" does not (an abbreviation of initials)
        return not starts or (len(before) > 1 and re.fullmatch(r"[^\W\d_]\.", before[-2]) is not None)
    if "." in core and all(0 < len(p) <= 2 and p.isalpha() for p in core.split(".")):
        return not starts                                       # "U.S.", "e.g.", "z.B.", "Ph.D."
    if core.lower() in _TITLES:
        return True
    if core.lower() in _SHORT:
        return not starts
    return core.isdigit() and len(core) <= 2 and bool(_ORDINAL_NOUN.match(after))


class _Sentences:
    """``SENTENCE.split(text)``, as with the regular expression this replaces."""

    @staticmethod
    def split(text: str) -> list[str]:
        return split_sentences(text)


SENTENCE = _Sentences()
_REF = re.compile(
    r"\bRetrieved\b|\bArchived from\b|\(PDF\)|\bISBN\b|\bISSN\b|\bOCLC\b|\bdoi:|\bS2CID\b|\bPMID\b|"
    r"^\W*[\"“][^\"”]{2,300}[\"”]\.?\s*(?:\([^)]{1,40}\)\.?)?\s*$|"      # "Title". / "Title" (in German).
    r"^\(?\d{4}\)?\.?$|"                                                     # (1863).
    r"^[A-Z][\w'’-]+, [A-Z][\w.'’ -]{0,40}(?:\(\d{4}|;|\.$)|"               # King, B.B.; …  Nanos, Nik (2017)
    r"\b(?:pp?|vol|ed|eds)\.\s*\d|"                                          # p. 10, vol. 3
    r"\.(?:com|org|net|gov|edu|int|co\.uk|ac\.uk|de|fr|ca|au|in|io)\.?\s*$|"  # ends in a site name
    r"\bWikimedia Commons has media\b", re.I)


def is_reference(sentence: str) -> bool:
    """A line of a reference list, bibliography or link list (not a sentence of the article)."""
    s = sentence.strip()
    if _REF.search(s):
        return True
    words = s.split()
    return len(words) <= 3 and not any(w.islower() and w.isalpha() and len(w) > 3 for w in words)


def strip_references(text: str, keep: int = 3, window: int = 8, need: int = 5) -> str:
    """The article without its trailing reference zone: the text is cut where, from a sentence on,
    at least ``need`` of the next ``window`` sentences look like references. The first ``keep``
    sentences always stay."""
    sents = SENTENCE.split(text.strip())
    if len(sents) <= keep + need:
        return text.strip()
    # walk back from the end (the zone is at the end); stop after a long run of real sentences
    flags: dict[int, bool] = {}
    flag = lambda j: flags[j] if j in flags else flags.setdefault(j, is_reference(sents[j]))   # noqa: E731
    cut, plain = None, 0
    for i in range(len(sents) - 1, keep - 1, -1):
        if flag(i):
            plain = 0
            if sum(flag(j) for j in range(i, min(i + window, len(sents)))) >= min(need, len(sents) - i):
                cut = i
        else:
            plain += 1
            if plain >= 2 * window:
                break
    return " ".join(sents[:cut]).strip() if cut is not None else text.strip()
