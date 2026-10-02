"""Comparisons from the fact bank (Chat v3.1, A7): "compare France and Germany", "which is bigger,
France or Germany?", "who is older, Einstein or Newton?", "is Mount Everest higher than K2?".

Every number comes from the fact bank (DBpedia/Wikidata infobox values) and is shown with both
entities, so the reply carries its own evidence. No neural network, no guessing: when one side
lacks the value, ENGRAMM says so instead of comparing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from engramm.kb.kgqa import KGQA, PERSON, PLACE, _fmt_date, _fmt_number, _num, _with_article
from engramm.kb.store import Entity

# what "bigger", "older" … mean, by kind of thing: (property, more-is-what, unit renderer)
_MEASURES = {
    "bigger": [(PLACE, "areaTotal", "area"), (("Mountain", "Volcano"), "elevation", "height"),
               (("Building", "Skyscraper", "Tower"), "height", "height"), (("River",), "length", "length"),
               (("Company",), "numberOfEmployees", "count")],
    "populous": [(PLACE, "populationTotal", "count")],
    "older": [(PERSON, "birthDate", "date_old"), (("Company", "Organisation", "Band", "University"), "foundingYear", "year_old"),
              (PLACE, "foundingDate", "date_old")],
    "younger": [(PERSON, "birthDate", "date_young")],
    "higher": [(("Mountain", "Volcano"), "elevation", "height"), (PLACE, "elevation", "height"),
               (("Building", "Skyscraper", "Tower"), "height", "height")],
    "longer": [(("River",), "length", "length"), (("Film",), "runtime", "minutes")],
}
_WORDS = {"bigger": "bigger", "larger": "bigger", "large": "bigger", "big": "bigger", "smaller": "bigger",
          "more populous": "populous", "more people": "populous", "bigger population": "populous",
          "larger population": "populous", "older": "older", "younger": "younger", "taller": "higher",
          "higher": "higher", "longer": "longer", "shorter": "longer", "lower": "higher"}
_INVERT = {"smaller", "shorter", "lower", "younger"}
_PROFILE = {
    "place": (("populationTotal", "Population", "count"), ("areaTotal", "Area", "area"), ("capital", "Capital", "text"),
              ("officialLanguage", "Official language", "text"), ("currency", "Currency", "text"),
              ("elevation", "Elevation", "height")),
    "person": (("birthDate", "Born", "date"), ("deathDate", "Died", "date"), ("nationality", "Nationality", "text"),
               ("occupation", "Occupation", "text"), ("knownFor", "Known for", "text")),
    "company": (("foundingYear", "Founded", "text"), ("headquarter", "Headquarters", "text"),
                ("industry", "Industry", "text"), ("numberOfEmployees", "Employees", "count")),
    "work": (("releaseDate", "Released", "date"), ("director", "Director", "text"), ("author", "Author", "text"),
             ("genre", "Genre", "text"), ("runtime", "Runtime", "minutes")),
    "mountain": (("elevation", "Height", "height"), ("mountainRange", "Range", "text"), ("country", "Country", "text")),
}

_LEAD = r"^(?:(?:hey|ok|okay|so|well|please|pls)[, ]+)*(?:(?:can|could|would) you |please )*"
_COMPARE = re.compile(_LEAD + r"(?:compare|comparison (?:of|between)|what(?:'s| is) the difference between|"
                      r"how (?:do|does) (?P<a0>.+?) compare (?:to|with)) ?(?P<a>.+?)?(?: (?:and|with|to|vs\.?|versus) "
                      r"(?P<b>.+?))?$")
_VS = re.compile(r"^(?P<a>[a-z0-9][\w .'-]{1,40}?) (?:vs\.?|versus) (?P<b>[a-z0-9][\w .'-]{1,40}?)$")
_WHICH = re.compile(_LEAD + r"(?:which|who|what) (?:one )?(?:is|was|are|has) (?P<w>bigger|larger|smaller|older|younger|"
                    r"taller|higher|longer|shorter|lower|more populous|more people|the bigger population|"
                    r"the larger population|a bigger population|a larger population)[,:]? (?P<a>.+?) or (?P<b>.+?)$")
_IS_THAN = re.compile(_LEAD + r"(?:is|was|are) (?P<a>.+?) (?P<w>bigger|larger|smaller|older|younger|taller|higher|longer|"
                      r"shorter|lower|more populous) than (?P<b>.+?)$")


@dataclass
class Comparison:
    text: str
    entities: tuple[Entity, Entity]
    evidence: str


# values of the lite fact bank known to be wrong (DBpedia lists France's overseas CFP franc as its only
# currency, the euro was lost when the bank was slimmed) — shown as missing rather than wrong
_KNOWN_WRONG = {("France", "currency"): {"CFP Franc"}}


class Comparer:
    def __init__(self, kgqa: KGQA):
        self.q = kgqa
        self.kb = kgqa.kb

    def _entities(self, phrase: str) -> list[Entity]:
        """Entities the phrase may name, best first ("Amazon" → the company, then the river)."""
        phrase = re.sub(r"^(?:the )", "", phrase.strip(" ?.!,"), flags=re.I)
        if not phrase or len(phrase.split()) > 6:
            return []
        seen, out = set(), []
        for t in (phrase, "The " + phrase, phrase + " River", "River " + phrase, "Mount " + phrase, phrase + " Inc.",
                  phrase + " (company)", phrase + " Corporation"):
            for e, _ in self.kb.link(t, limit=6):
                if e.id not in seen:
                    seen.add(e.id)
                    out.append(e)
        out.sort(key=lambda e: -(e.popularity + 1) * (3 if e.title.lower() == phrase.lower() else 1))
        return out

    def _entity(self, phrase: str) -> Entity | None:
        c = self._entities(phrase)
        return c[0] if c else None

    def _pair(self, a_txt: str, b_txt: str, fits) -> tuple[Entity, Entity] | None:
        """The best pair of candidates that fit together (the same kind of thing)."""
        ca, cb = self._entities(a_txt)[:6], self._entities(b_txt)[:6]
        best = None
        for i, a in enumerate(ca):
            for j, b in enumerate(cb):
                if a.id != b.id and fits(a, b):
                    if best is None or i + j < best[0]:
                        best = (i + j, a, b)
        return (best[1], best[2]) if best else None

    def _value(self, ent: Entity, prop: str):
        fs = self.kb.facts(ent.id, (prop,))
        for f in fs:
            if f.value and f.value not in _KNOWN_WRONG.get((ent.title, prop), ()):
                return f
        return None

    def _render(self, f, kind: str) -> str:
        v = f.value
        if kind == "count":
            n = _num(v)
            if n is None:
                return v
            return f"{n / 1e6:,.1f} million" if n >= 1e6 else _fmt_number(n)
        if kind == "area":
            n = _num(v)
            return f"{_fmt_number(n / 1e6)} km²" if n is not None else v
        if kind == "height":
            n = _num(v)
            return f"{_fmt_number(n)} m" if n is not None else v
        if kind == "length":
            n = _num(v)
            return (f"{_fmt_number(n / 1000)} km" if n >= 1000 else f"{_fmt_number(n)} m") if n is not None else v
        if kind == "minutes":
            n = _num(v)
            return f"{round(n / 60) if n > 400 else round(n)} minutes" if n is not None else v
        if kind == "date":
            return _fmt_date(v, f.dtype)[1]
        if f.value_entity is not None:
            return re.sub(r"\s*\([^)]*\)$", "", v)
        return v

    def _render_all(self, ent: Entity, prop: str, kind: str) -> str:
        if kind != "text":
            return self._render(self._value(ent, prop), kind)
        vals = list(dict.fromkeys(self._render(f, kind) for f in self.kb.facts(ent.id, (prop,))
                                  if f.value and f.value not in _KNOWN_WRONG.get((ent.title, prop), ())))
        # the main one first: the best-known value in the fact bank (France: Euro before CFP franc)
        vals.sort(key=lambda v: -self._popularity(v))
        return ", ".join(vals[:2]) if len(vals) <= 2 else ", ".join(vals[:2]) + " …"

    def _popularity(self, name: str) -> float:
        for cand in (name, name + " language"):   # "German" → the article "German language"
            try:
                hits = self.kb.link(cand, limit=1)
            except Exception:                    # a value that is no entity
                hits = []
            if hits:
                return float(hits[0][0].popularity or 0)
        return 0.0

    @staticmethod
    def _kind(ent: Entity) -> str | None:
        t = ent.type or ""
        if t in PLACE:
            return "place"
        if t in PERSON or t.endswith("Artist"):
            return "person"
        if t in ("Company", "Organisation", "University"):
            return "company"
        if t in ("Mountain", "Volcano"):
            return "mountain"
        if t in ("Film", "Book", "Novel", "Album", "TelevisionShow", "VideoGame"):
            return "work"
        return None

    # -- "compare X and Y" ---------------------------------------------------------------------

    def profile(self, a: Entity, b: Entity) -> Comparison | None:
        ka, kb_ = self._kind(a), self._kind(b)
        if ka is None or ka != kb_:
            return None
        rows, ev = [], []
        for prop, label, kind in _PROFILE[ka]:
            fa, fb = self._value(a, prop), self._value(b, prop)
            if fa is None and fb is None:
                continue
            va = self._render_all(a, prop, kind) if fa else "—"
            vb = self._render_all(b, prop, kind) if fb else "—"
            rows.append(f"• {label}: {va} vs {vb}")
            ev.append(f"{prop}: {fa.value if fa else '?'} / {fb.value if fb else '?'}")
        if len(rows) < 2:
            return None
        na, nb = _with_article(a.name, a.type), _with_article(b.name, b.type)
        head = f"{na[:1].upper() + na[1:]} vs {nb}:"
        summary = []
        if ka == "place":
            for prop, more in (("populationTotal", "more people"), ("areaTotal", "the larger area")):
                fa, fb = self._value(a, prop), self._value(b, prop)
                if fa and fb and _num(fa.value) is not None and _num(fb.value) is not None:
                    win = na if _num(fa.value) > _num(fb.value) else nb
                    summary.append(f"{win[:1].upper() + win[1:]} has {more}.")
        text = head + "\n" + "\n".join(rows) + ("\n\n" + " ".join(summary) if summary else "")
        return Comparison(text, (a, b), f"{a.title} / {b.title} — " + "; ".join(ev[:4]))

    # -- "which is bigger, X or Y?" ------------------------------------------------------------

    def measure(self, word: str, a: Entity, b: Entity) -> Comparison | None:
        key = _WORDS.get(word)
        if key is None:
            return None
        for kinds, prop, unit in _MEASURES[key]:
            if (a.type or "") not in kinds or (b.type or "") not in kinds:
                continue
            fa, fb = self._value(a, prop), self._value(b, prop)
            na, nb = _with_article(a.name, a.type), _with_article(b.name, b.type)
            if fa is None or fb is None:
                missing = na if fa is None else nb
                return Comparison(f"I can't compare them — my fact bank has no {prop_label(prop)} for {missing}.",
                                  (a, b), f"{a.title} / {b.title} — {prop}")
            if unit.startswith(("date", "year")):
                ya, yb = _year(fa.value), _year(fb.value)
                if ya is None or yb is None:
                    return None
                older_first = (fa.value <= fb.value) if unit.startswith("date") else (ya <= yb)
                if key == "younger" or word in _INVERT:
                    older_first = not older_first
                win, lose = (na, nb) if older_first else (nb, na)
                wa, wb = (self._render(fa, "date") if unit.startswith("date") else fa.value,
                          self._render(fb, "date") if unit.startswith("date") else fb.value)
                verb = {"older": "older", "younger": "younger"}.get(key if word not in _INVERT else word, word)
                if key == "older" and word == "younger":
                    verb = "younger"
                what = "born" if (a.type or "") in PERSON or (a.type or "").endswith("Artist") else "founded"
                text = (f"{win[:1].upper() + win[1:]} is {verb}: {na} was {what} {wa}, {nb} {wb}.")
                return Comparison(text, (a, b), f"{a.title}: {fa.value}; {b.title}: {fb.value}")
            xa, xb = _num(fa.value), _num(fb.value)
            if xa is None or xb is None:
                return None
            if xa == xb:
                return Comparison(f"They're the same: {self._render(fa, unit)} each.", (a, b),
                                  f"{a.title}: {fa.value}; {b.title}: {fb.value}")
            more = xa > xb
            if word in _INVERT:
                more = not more
            win, lose = (na, nb) if more else (nb, na)
            wv, lv = (self._render(fa, unit), self._render(fb, unit)) if (win == na) else \
                (self._render(fb, unit), self._render(fa, unit))
            adj = "more populous" if key == "populous" else word
            basis = {"area": " by area", "count": "" if key == "populous" else ""}.get(unit, "")
            text = f"{win[:1].upper() + win[1:]} is {adj}{basis}: {wv}, compared with {lv} for {lose}."
            return Comparison(text, (a, b), f"{a.title}: {fa.value}; {b.title}: {fb.value}")
        return None

    # -- the router ------------------------------------------------------------------------------

    def answer(self, norm: str) -> Comparison | None:
        s = norm.strip(" ?.!")
        m = _WHICH.match(s) or _IS_THAN.match(s)
        if m:
            w = m.group("w").replace("the ", "").replace("a ", "")
            if "population" in w:
                w = "more populous"
            key = _WORDS.get(w)
            if key is None:
                return None
            kinds = [k for k, _, _ in _MEASURES[key]]
            pair = self._pair(m.group("a"), m.group("b"),
                              lambda a, b: any((a.type or "") in k and (b.type or "") in k for k in kinds))
            if pair is None:
                return None
            return self.measure(w, *pair)
        m = _COMPARE.match(s)
        if m:
            a_txt, b_txt = m.group("a0") or m.group("a"), m.group("b")
            if m.group("a0") and m.group("a"):
                b_txt = m.group("a")
            if not a_txt or not b_txt:
                return None
            pair = self._pair(a_txt, b_txt, lambda a, b: self._kind(a) is not None and self._kind(a) == self._kind(b))
            return self.profile(*pair) if pair else None
        m = _VS.match(s)
        if m:
            pair = self._pair(m.group("a"), m.group("b"),
                              lambda a, b: self._kind(a) is not None and self._kind(a) == self._kind(b))
            return self.profile(*pair) if pair else None
        return None

    @staticmethod
    def is_request(norm: str) -> bool:
        """A comparison request, answerable or not (never something to remember)."""
        s = norm.strip(" ?.!")
        return bool(_COMPARE.match(s) and re.search(r"\b(?:and|with|to|vs|versus)\b", s)) or bool(_WHICH.match(s)) \
            or bool(_IS_THAN.match(s)) or bool(_VS.match(s))


def prop_label(prop: str) -> str:
    return {"areaTotal": "area", "populationTotal": "population", "elevation": "height", "height": "height",
            "length": "length", "birthDate": "birth date", "foundingYear": "founding year",
            "foundingDate": "founding date", "numberOfEmployees": "number of employees",
            "runtime": "running time"}.get(prop, prop)


def _year(v: str) -> int | None:
    m = re.match(r"(-?\d{1,4})", v)
    return int(m.group(1)) if m else None
