"""Superlative questions answered from the fact bank: "What is the tallest mountain in the world?",
"the longest river", "the most populous country", "the tallest building".

The text look-up is weak at these (the words "tallest mountain" appear in many articles about
other things), while the fact bank holds the measured value for every entity of a type. A
question is answered only for the type/property pairs below, each checked by hand on the
packed data, and only for the whole world: "in Africa" or "in Germany" would need regions the
fact bank does not reliably carry, so those questions go back to the normal path.

Data guards:
* mountain ranges are stored with the type Mountain ("Himalayas" with Everest's height): an
  entity that is the ``mountainRange`` of another entity is a range, not a mountain;
* countries include historical states ("Russian Empire", "Mongol Empire"): only current
  sovereign states (``SOVEREIGN``) count;
* duplicated rows for one entity count once (the largest plausible value: one row says Georgia
  has 36 trillion people);
* the Caspian Sea is stored as a body of water but is the usual answer for the largest lake;
* volcanoes and cities are left out: the packed data gives Kilimanjaro (not Ojos del Salado) and
  Beijing (city limits differ by source), and a wrong answer is worse than none.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_ADJ = r"(?P<adj>tallest|highest|longest|largest|biggest|deepest|smallest|shortest|most populous|most populated|" \
       r"least populous|most people|lowest)"
_NOUN = r"(?P<noun>mountains?|peaks?|rivers?|lakes?|buildings?|skyscrapers?|volcano(?:es|s)?|countr(?:y|ies)|cit(?:y|ies))"
SUPERLATIVE_Q = re.compile(
    r"^(?:(?:and|so|ok|okay|hey)[, ]+)?(?:what|which)(?:'?s| is| was| are)? (?:the )?" + _ADJ + r" " + _NOUN +
    r"(?: (?:in|on|of) (?:the )?(?:world|earth|planet))?(?: (?:by|in) (?P<by>area|size|population|length|height))?"
    r"(?: right now| today| currently)?\??$", re.I)

# (noun, adjective) → (entity types, property, highest first?, kind of value)
_RULES = {
    ("mountain", "tallest"): (("Mountain",), "elevation", True, "height"),
    ("mountain", "highest"): (("Mountain",), "elevation", True, "height"),
    ("peak", "highest"): (("Mountain",), "elevation", True, "height"),
    ("peak", "tallest"): (("Mountain",), "elevation", True, "height"),
    ("river", "longest"): (("River",), "length", True, "length"),
    ("lake", "largest"): (("Lake",), "areaTotal", True, "area"),
    ("lake", "biggest"): (("Lake",), "areaTotal", True, "area"),
    ("building", "tallest"): (("Building", "Skyscraper"), "height", True, "tall"),
    ("building", "highest"): (("Building", "Skyscraper"), "height", True, "tall"),
    ("skyscraper", "tallest"): (("Building", "Skyscraper"), "height", True, "tall"),
    ("country", "largest"): (("Country",), "areaTotal", True, "area"),
    ("country", "biggest"): (("Country",), "areaTotal", True, "area"),
    ("country", "smallest"): (("Country",), "areaTotal", False, "area"),
    ("country", "most populous"): (("Country",), "populationTotal", True, "people"),
    ("country", "most populated"): (("Country",), "populationTotal", True, "people"),
    ("country", "most people"): (("Country",), "populationTotal", True, "people"),
    ("country", "least populous"): (("Country",), "populationTotal", False, "people"),
}

# no real value lies above these (metres, square metres, people)
_CAP = {"elevation": 9_000, "length": 7_500_000, "areaTotal": 2e13, "populationTotal": 2e9, "height": 1_000}
_EXTRA = {"areaTotal": ("Caspian Sea",)}

# current sovereign states (UN members and observers) as the fact bank titles them
SOVEREIGN = frozenset("""
Afghanistan|Albania|Algeria|Andorra|Angola|Antigua and Barbuda|Argentina|Armenia|Australia|Austria|Azerbaijan|
The Bahamas|Bahrain|Bangladesh|Barbados|Belarus|Belgium|Belize|Benin|Bhutan|Bolivia|Bosnia and Herzegovina|Botswana|
Brazil|Brunei|Bulgaria|Burkina Faso|Burundi|Cambodia|Cameroon|Canada|Cape Verde|Central African Republic|Chad|Chile|
China|Colombia|Comoros|Republic of the Congo|Democratic Republic of the Congo|Costa Rica|Croatia|Cuba|Cyprus|
Czech Republic|Denmark|Djibouti|Dominica|Dominican Republic|East Timor|Ecuador|Egypt|El Salvador|Equatorial Guinea|
Eritrea|Estonia|Eswatini|Ethiopia|Fiji|Finland|France|Gabon|The Gambia|Georgia (country)|Germany|Ghana|Greece|
Grenada|Guatemala|Guinea|Guinea-Bissau|Guyana|Haiti|Honduras|Hungary|Iceland|India|Indonesia|Iran|Iraq|
Republic of Ireland|Israel|Italy|Ivory Coast|Jamaica|Japan|Jordan|Kazakhstan|Kenya|Kiribati|North Korea|South Korea|
Kuwait|Kyrgyzstan|Laos|Latvia|Lebanon|Lesotho|Liberia|Libya|Liechtenstein|Lithuania|Luxembourg|Madagascar|Malawi|
Malaysia|Maldives|Mali|Malta|Marshall Islands|Mauritania|Mauritius|Mexico|Federated States of Micronesia|Moldova|
Monaco|Mongolia|Montenegro|Morocco|Mozambique|Myanmar|Namibia|Nauru|Nepal|Netherlands|New Zealand|Nicaragua|Niger|
Nigeria|North Macedonia|Norway|Oman|Pakistan|Palau|Panama|Papua New Guinea|Paraguay|Peru|Philippines|Poland|
Portugal|Qatar|Romania|Russia|Rwanda|Saint Kitts and Nevis|Saint Lucia|Saint Vincent and the Grenadines|Samoa|
San Marino|São Tomé and Príncipe|Saudi Arabia|Senegal|Serbia|Seychelles|Sierra Leone|Singapore|Slovakia|Slovenia|
Solomon Islands|Somalia|South Africa|South Sudan|Spain|Sri Lanka|Sudan|Suriname|Sweden|Switzerland|Syria|Tajikistan|
Tanzania|Thailand|Togo|Tonga|Trinidad and Tobago|Tunisia|Turkey|Turkmenistan|Tuvalu|Uganda|Ukraine|
United Arab Emirates|United Kingdom|United States|Uruguay|Uzbekistan|Vanuatu|Vatican City|Venezuela|Vietnam|Yemen|
Zambia|Zimbabwe|State of Palestine
""".replace("\n", "").split("|"))


@dataclass
class Superlative:
    title: str
    value: float
    kind: str
    text: str


def _singular(noun: str) -> str:
    noun = noun.lower()
    for plural, single in (("countries", "country"), ("cities", "city"), ("volcanoes", "volcano"), ("volcanos", "volcano")):
        if noun == plural:
            return single
    return noun[:-1] if noun.endswith("s") and noun not in ("countries",) else noun


def _value_text(kind: str, v: float) -> str:
    if kind == "height":
        return f"{v:,.0f} m ({v * 3.28084:,.0f} ft) high"
    if kind == "tall":
        return f"{v:,.0f} m tall"
    if kind == "length":
        return f"about {v / 1000:,.0f} km long"
    if kind == "area":
        return f"about {v / 1e6:,.0f} km² in area" if v >= 1e6 else f"about {v / 1e6:,.2f} km² in area"
    return f"home to about {v:,.0f} people"


def answer(db, question: str, rank: int = 1) -> Superlative | None:
    """The answer to a superlative question from the fact bank's sqlite connection, or None;
    ``rank`` 2 is the runner-up ("and the second?")."""
    q = " ".join(question.strip().split())
    q = re.sub(r"^((?:(?:and|so|ok|okay|hey)[, ]+)?)(?:which|what) (country|city) has the (?:most people|most inhabitants|largest population|"
               r"biggest population|highest population)", r"\1which is the most populous \2", q, flags=re.I)   # "which country has the most people?"
    m = SUPERLATIVE_Q.match(q)
    if not m:
        return None
    noun, adj = _singular(m.group("noun")), m.group("adj").lower()
    by = (m.group("by") or "").lower()
    if noun == "country" and adj in ("largest", "biggest") and by == "population":
        adj = "most populous"
    if noun == "country" and adj == "smallest" and by == "population":
        adj = "least populous"
    rule = _RULES.get((noun, adj))
    if rule is None:
        return None
    types, prop, desc, kind = rule
    marks = ",".join("?" for _ in types)
    extra = _EXTRA.get(prop, ()) if noun == "lake" else ()
    title_marks = ",".join("?" for _ in extra) or "''"
    rows = db.execute(
        f"SELECT e.id, e.title, MAX(CAST(f.value AS REAL)) FROM entity e JOIN fact f ON f.entity = e.id "
        f"WHERE (e.type IN ({marks}) OR e.title IN ({title_marks})) AND f.prop = ? "
        f"AND f.dtype IN ('double', 'nonNegativeInteger', 'integer') AND CAST(f.value AS REAL) <= ? "
        f"GROUP BY e.id", (*types, *extra, prop, _CAP[prop])).fetchall()
    if not rows:
        return None
    ranges = set()
    if "Mountain" in types:
        ranges = {r[0] for r in db.execute("SELECT DISTINCT value FROM fact WHERE prop = 'mountainRange'")}
    cands = [(t, v) for _, t, v in rows if v and v > 0 and t not in ranges and
             (noun != "country" or t in SOVEREIGN)]
    if not cands:
        return None
    cands.sort(key=lambda x: (-x[1], x[0]) if desc else (x[1], x[0]))
    if rank > len(cands):
        return None
    title, value = cands[rank - 1]
    nth = {1: "", 2: "second-", 3: "third-"}.get(rank)
    if nth is None:
        return None
    phrase = f"the {nth}{adj} {noun} in the world"
    shown = title
    if (noun in ("river", "lake") and not title.startswith("Lake ")) or title.startswith(("United ", "Netherlands")):
        shown = "The " + title                          # "The Nile", "The Caspian Sea", "The United States"
    text = f"{shown} is {phrase}, {_value_text(kind, value)}."
    return Superlative(title, value, kind, text)
