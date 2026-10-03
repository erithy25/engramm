"""German knowledge questions through the English fact bank (Chat v3.1, German v1).

ENGRAMM's reading and fact bank are English. A German question with a common shape — "Wer hat
Hamlet geschrieben?", "Wie alt ist Angela Merkel?", "Was ist die Hauptstadt von Frankreich?" —
is turned into its English form by rules (no translation model), German place names are mapped
to their English titles ("Frankreich" → "France"), and an answer from the fact bank is written
back as a German sentence. Values (names, numbers, dates) are language-neutral; dates and
numbers get German formatting. Answers from English text are quoted as such ("auf Englisch").
"""

from __future__ import annotations

import re

# German names of frequently asked places and things → English titles (the fact bank also knows
# many German names as redirects; this list covers the common ones it may not)
EXONYMS = {
    "deutschland": "Germany", "frankreich": "France", "österreich": "Austria", "schweiz": "Switzerland",
    "italien": "Italy", "spanien": "Spain", "england": "England", "großbritannien": "United Kingdom",
    "vereinigtes königreich": "United Kingdom", "vereinigte staaten": "United States", "usa": "United States",
    "amerika": "United States", "russland": "Russia", "china": "China", "japan": "Japan", "indien": "India",
    "brasilien": "Brazil", "kanada": "Canada", "australien": "Australia", "mexiko": "Mexico", "ägypten": "Egypt",
    "türkei": "Turkey", "griechenland": "Greece", "niederlande": "Netherlands", "holland": "Netherlands",
    "belgien": "Belgium", "polen": "Poland", "schweden": "Sweden", "norwegen": "Norway", "dänemark": "Denmark",
    "finnland": "Finland", "portugal": "Portugal", "irland": "Ireland", "tschechien": "Czech Republic",
    "ungarn": "Hungary", "kroatien": "Croatia", "argentinien": "Argentina", "südafrika": "South Africa",
    "südkorea": "South Korea", "nordkorea": "North Korea", "neuseeland": "New Zealand", "island": "Iceland",
    "israel": "Israel", "iran": "Iran", "irak": "Iraq", "saudi-arabien": "Saudi Arabia", "ukraine": "Ukraine",
    "rumänien": "Romania", "bulgarien": "Bulgaria", "serbien": "Serbia", "luxemburg": "Luxembourg",
    "münchen": "Munich", "köln": "Cologne", "nürnberg": "Nuremberg", "wien": "Vienna", "rom": "Rome",
    "mailand": "Milan", "venedig": "Venice", "florenz": "Florence", "neapel": "Naples", "prag": "Prague",
    "warschau": "Warsaw", "moskau": "Moscow", "peking": "Beijing", "lissabon": "Lisbon", "brüssel": "Brussels",
    "kopenhagen": "Copenhagen", "athen": "Athens", "genf": "Geneva", "zürich": "Zurich", "kairo": "Cairo",
    "relativitätstheorie": "theory of relativity", "die relativitätstheorie": "theory of relativity",
    "glühbirne": "light bulb", "die glühbirne": "light bulb", "telefon": "telephone", "das telefon": "telephone",
    "fernrohr": "telescope", "das fernrohr": "telescope", "teleskop": "telescope", "das teleskop": "telescope",
    "buchdruck": "printing press", "den buchdruck": "printing press", "dampfmaschine": "steam engine",
    "die dampfmaschine": "steam engine", "flugzeug": "airplane", "das flugzeug": "airplane", "auto": "automobile",
    "das auto": "automobile", "fernseher": "television", "den fernseher": "television", "das internet": "Internet",
    "penizillin": "penicillin", "das penizillin": "penicillin", "die schwerkraft": "gravity", "dynamit": "dynamite",
    "das dynamit": "dynamite", "die evolutionstheorie": "evolution", "das rad": "wheel", "den computer": "computer",
    "mond": "Moon", "sonne": "Sun", "erde": "Earth", "mars": "Mars", "eiffelturm": "Eiffel Tower",
    "freiheitsstatue": "Statue of Liberty", "brandenburger tor": "Brandenburg Gate", "kölner dom": "Cologne Cathedral",
    "rhein": "Rhine", "donau": "Danube", "nil": "Nile", "amazonas": "Amazon River", "alpen": "Alps",
    "zugspitze": "Zugspitze", "bodensee": "Lake Constance", "berliner mauer": "Berlin Wall", "die berliner mauer": "the Berlin Wall", "ostsee": "Baltic Sea", "nordsee": "North Sea",
    "mittelmeer": "Mediterranean Sea", "atlantik": "Atlantic Ocean", "pazifik": "Pacific Ocean",
    "die vier jahreszeiten": "the four seasons", "vier jahreszeiten": "the four seasons", "die zauberflöte": "The Magic Flute",
    "zauberflöte": "The Magic Flute", "die mona lisa": "Mona Lisa", "mona lisa": "Mona Lisa", "die sternennacht": "The Starry Night",
    "sternennacht": "The Starry Night", "romeo und julia": "Romeo and Juliet", "das penicillin": "penicillin",
    "goethe": "Johann Wolfgang von Goethe", "schiller": "Friedrich Schiller", "beethoven": "Ludwig van Beethoven",
    "mozart": "Wolfgang Amadeus Mozart", "bach": "Johann Sebastian Bach", "einstein": "Albert Einstein",
    "merkel": "Angela Merkel", "scholz": "Olaf Scholz", "luther": "Martin Luther", "kant": "Immanuel Kant",
}

# (German pattern, English template, answer kind for the German sentence)
_X = r"(?P<x>.+?)"
_Y = r"(?P<y>.+?)"
RULES = [
    (rf"wer hat {_X} geschrieben", "who wrote {x}", "wrote"),
    (rf"wer schrieb {_X}", "who wrote {x}", "wrote"),
    (rf"von wem (?:ist|stammt) {_X}", "who wrote {x}", "wrote"),
    (rf"wer hat {_X} gemalt", "who painted {x}", "painted"),
    (rf"wer malte {_X}", "who painted {x}", "painted"),
    (rf"wer hat {_X} erfunden", "who invented {x}", "invented"),
    (r"wer hat (?P<x>amerika) entdeckt", "who discovered america", "discovered"),     # the continent, not the United States
    (rf"wer hat {_X} entdeckt", "who discovered {x}", "discovered"),
    (rf"wer hat {_X} entwickelt", "who developed {x}", "invented"),
    (rf"wer hat {_X} gegründet", "who founded {x}", "founded_by"),
    (rf"wer hat {_X} (?:gebaut|entworfen)", "who designed {x}", "designed"),
    (rf"wer hat {_X} komponiert", "who composed {x}", "composed"),
    (rf"wer hat (?:bei )?{_X} regie geführt", "who directed {x}", "directed"),
    (rf"wer (?:ist|war) (?:der |die )?erste (?:präsident|präsidentin) (?:von |der |des )?{_X}", "who was the first president of {x}",
     "first_holder"),
    (rf"wer (?:ist|war) (?:der |die )?erste (?:premierminister|premierministerin) (?:von |der |des )?{_X}",
     "who was the first prime minister of {x}", "first_holder"),
    (rf"wer (?:ist|war) (?:der |die )?erste (?:bundeskanzler|bundeskanzlerin|kanzler|kanzlerin) (?:von |der |des )?{_X}",
     "who was the first chancellor of {x}", "first_holder"),
    (rf"wer (?:ist|war) (?:der |die )?erste (?:kaiser|kaiserin) (?:von |der |des )?{_X}", "who was the first emperor of {x}",
     "first_holder"),
    (rf"wie lange war {_X} (?:präsident|präsidentin)", "how long was {x} president", "tenure"),
    (rf"wie lange war {_X} (?:bundeskanzler|bundeskanzlerin|kanzler|kanzlerin)", "how long was {x} chancellor", "tenure"),
    (rf"wie lange war {_X} (?:premierminister|premierministerin)", "how long was {x} prime minister", "tenure"),
    (rf"wie lange war {_X} (?:könig|königin)", "how long was {x} king", "tenure"),
    (rf"wie lange war {_X} im amt", "how long was {x} in office", "tenure"),
    (rf"woher (?:kam|kommt|stammt|stammte) {_X}", "where was {x} from", "from"),
    (rf"welche nationalität (?:hat|hatte) {_X}", "what nationality was {x}", "from"),
    (rf"wer (?:ist|war) (?:der |die )?(?:präsident|präsidentin|staatsoberhaupt) von {_X}",
     "who is the president of {x}", "head_state"),
    (rf"wer (?:ist|war) (?:der |die )?(?:bundeskanzler|bundeskanzlerin|kanzler|kanzlerin|premierminister|"
     rf"premierministerin|regierungschef|regierungschefin) von {_X}", "who is the prime minister of {x}", "head_gov"),
    (rf"wer (?:ist|war) (?:der |die )?(?:könig|königin) von {_X}", "who is the king of {x}", "monarch"),
    (rf"wer (?:ist|war) (?:der |die )?bürgermeister(?:in)? von {_X}", "who is the mayor of {x}", "mayor"),
    (rf"wer (?:ist|war) (?:der |die )?(?:ceo|chef|chefin|vorstandschef|vorstandschefin) von {_X}",
     "who is the ceo of {x}", "ceo"),
    (rf"(?:was|wie) (?:ist|heißt|heisst) die hauptstadt von {_X}", "what is the capital of {x}", "capital"),
    (rf"was ist {_X}s hauptstadt", "what is the capital of {x}", "capital"),
    (rf"wie viele (?:einwohner|menschen|leute) (?:hat|leben in) {_X}", "what is the population of {x}", "population"),
    (rf"wie (?:groß|hoch) ist die (?:bevölkerung|einwohnerzahl) von {_X}", "what is the population of {x}", "population"),
    (rf"wie groß ist {_X}", "how big is {x}", "area"),
    (rf"wie hoch ist {_X}", "how tall is {x}", "height"),
    (rf"wie lang ist {_X}", "how long is {x}", "length"),
    (rf"wie tief ist {_X}", "how deep is {x}", "depth"),
    (rf"wann fiel {_X}", "when did {x} fall", "fell"),
    (rf"wann sank {_X}", "when did {x} sink", "sank"),
    (rf"welche sprachen? spricht man in {_X}", "what language is spoken in {x}", "language"),
    (rf"was (?:für eine sprache|spricht man) (?:spricht man )?in {_X}", "what language is spoken in {x}", "language"),
    (rf"wann ist {_X} gefallen", "when did {x} fall", "fell"),
    (rf"wie alt (?:ist|war|wurde) {_X}", "how old is {x}", "age"),
    (rf"wann (?:wurde|ist|war) {_X} geboren", "when was {x} born", "born_when"),
    (rf"wo (?:wurde|ist|war) {_X} geboren", "where was {x} born", "born_where"),
    (r"wann war (?P<x>das|es)", "when was that", "when_that"),
    (r"seit wann(?: ist (?P<x>er|sie)(?: (?:im amt|kanzler|kanzlerin|bundeskanzler|bundeskanzlerin|chef|chefin|präsident|präsidentin))?)?", "since when has he been in office", "since"),
    (r"(?:und )?(?:welche|in welcher) partei(?: ist| hat)?(?: (?P<x>er|sie))?(?: drin)?", "what party is he in", "party"),          # "wann war das?" after an event, not a death
    (rf"wann (?:ist|starb|war) {_X}(?: gestorben)?", "when did {x} die", "died_when"),
    (rf"wann starb {_X}", "when did {x} die", "died_when"),
    (rf"woran (?:ist|starb) {_X}(?: gestorben)?", "how did {x} die", "died_how"),
    (rf"wo (?:ist|starb) {_X} gestorben", "where did {x} die", "died_where"),
    (rf"wo starb {_X}", "where did {x} die", "died_where"),
    (rf"wann wurde {_X} gegründet", "when was {x} founded", "founded_when"),
    (rf"wann wurde {_X} (?:gebaut|errichtet|fertiggestellt|eröffnet)", "when was {x} built", "built_when"),
    (rf"wann (?:kam|erschien) {_X}(?: heraus| raus)?", "when was {x} released", "released"),
    (r"wo (?:hängt|hängen|ist|befindet sich) (?P<x>sie|es|er)(?: heute| jetzt)?", "where is it now", "where"),
    (rf"wo (?:hängt|hängen) {_X}(?: heute| jetzt)?", "where is {x}", "where"),
    (rf"in welchem land (?:liegt|ist) {_X}", "what country is {x} in", "country"),
    (rf"wo (?:liegt|ist|befindet sich) {_X}", "where is {x}", "where"),
    (rf"welche (?:sprache|sprachen) (?:spricht man|wird) in {_X}(?: gesprochen)?", "what is the official language of {x}",
     "language"),
    (rf"was ist die (?:amtssprache|landessprache) von {_X}", "what is the official language of {x}", "language"),
    (rf"welche sprachen? spricht man (?P<x>dort|da)", "what language do they speak", "language"),
    (rf"welche währung (?:hat|benutzt|nutzt) (?:man )?(?P<x>dort|da)", "what currency do they use", "currency"),
    (r"(?P<x>welche währung)", "what currency do they use", "currency"),
    (rf"welche währung (?:hat|benutzt|nutzt) {_X}", "what is the currency of {x}", "currency"),
    (rf"was ist die währung (?:von|in) {_X}", "what is the currency of {x}", "currency"),
    (rf"mit wem (?:ist|war) {_X} verheiratet", "who is {x} married to", "spouse"),
    (rf"wer (?:ist|war) (?:die frau|der mann|die ehefrau|der ehemann) von {_X}", "who is {x} married to", "spouse"),
    (rf"was (?:hat|machte|macht) {_X} beruflich", "what was {x}'s occupation", "occupation"),
    (rf"wofür ist {_X} (?:bekannt|berühmt)", "what is {x} known for", "known_for"),
    (rf"was hat {_X} (?:sonst noch )?geschrieben", "what did {x} write", "works"),
    (rf"(?:was ist|welches ist) größer,? {_X} oder {_Y}", "which is bigger, {x} or {y}", "compare"),
    (rf"(?:welches land|welche stadt) ist größer,? {_X} oder {_Y}", "which is bigger, {x} or {y}", "compare"),
    (rf"wo leben mehr (?:menschen|leute),? (?:in )?{_X} oder (?:in )?{_Y}", "which is more populous, {x} or {y}",
     "compare"),
    (rf"wer ist älter,? {_X} oder {_Y}", "who is older, {x} or {y}", "compare"),
    (rf"wer ist jünger,? {_X} oder {_Y}", "who is younger, {x} or {y}", "compare"),
    (rf"(?:was|welcher|welches) ist höher,? {_X} oder {_Y}", "which is higher, {x} or {y}", "compare"),
    (rf"(?:was|welcher|welches) ist länger,? {_X} oder {_Y}", "which is longer, {x} or {y}", "compare"),
    (rf"vergleiche? {_X} (?:und|mit) {_Y}", "compare {x} and {y}", "compare"),
    (rf"(?:was ist der unterschied zwischen) {_X} und {_Y}", "compare {x} and {y}", "compare"),
    (rf"(?:erzähl|erzähle|erzählt) (?:mir )?(?:etwas |was |ein bisschen )?(?:über|von) {_X}", "tell me about {x}", "about"),
    (rf"was weißt du über {_X}", "tell me about {x}", "about"),
    (rf"(?:wer|was) (?:ist|war|sind|waren) {_X}", "tell me about {x}", "about"),
    (rf"(?:erkläre?|erklär) (?:mir )?{_X}", "tell me about {x}", "about"),
]
_COMPILED = [(re.compile(rf"^(?:(?:und|aber|also|sag mal|weißt du|kannst du mir sagen),? )?{p}$"), e, k) for p, e, k in RULES]

_MONTHS = {"January": "Januar", "February": "Februar", "March": "März", "April": "April", "May": "Mai",
           "June": "Juni", "July": "Juli", "August": "August", "September": "September", "October": "Oktober",
           "November": "November", "December": "Dezember"}


_PRONOUNS = {"er": "he", "sie": "she", "ihn": "him", "ihm": "him", "es": "it", "ihr": "her", "ihnen": "them",
             "die": "it", "der": "it", "das": "it", "den": "it", "dort": "there", "da": "there"}


def _english_name(x: str) -> str:
    x = x.strip(" ?.!,„“\"")
    x = re.sub(r"^(?:der|die|das|den|dem|des|ein|eine|einen|einem|einer)\s+", "", x)
    low = x.lower()
    if low in _PRONOUNS:
        return _PRONOUNS[low]                # "wann wurde er geboren?" → "when was he born" (resolved later)
    if low in EXONYMS:
        return EXONYMS[low]
    # keep the user's capitals; the messages arrive lower-cased, so title-case each word
    return " ".join(w if any(c.isupper() for c in w) else (w[:1].upper() + w[1:]) for w in x.split())


def german_display(x: str) -> str:
    """How the user wrote the name, title-cased ("frankreich" → "Frankreich")."""
    x = re.sub(r"^(?:der|die|das|den|dem|des)\s+", "", x.strip(" ?.!,„“\""))
    return " ".join(w if any(c.isupper() for c in w) else (w[:1].upper() + w[1:]) for w in x.split())


def to_english(norm: str) -> tuple[str, str, str, str] | None:
    """(English question, answer kind, the thing asked about in English, as the user wrote it) for a
    German question, or None."""
    s = norm.strip(" ?.!")
    for rx, eng, kind in _COMPILED:
        m = rx.match(s)
        if not m:
            continue
        x = _english_name(m.group("x") or "er")          # "seit wann?" names nobody: "he", resolved from the conversation
        if not x or len(x.split()) > 7:
            return None
        if kind == "about" and x.lower() in ("du", "ich", "das", "los", "dein name", "mein name", "it", "he", "she"):
            return None
        y = _english_name(m.group("y")) if "y" in rx.groupindex and m.group("y") else ""
        return eng.format(x=x, y=y), kind, x, german_display(m.group("x") or "er")
    return None


_GERMAN_OF: dict[str, str] = {}
for _de, _en in EXONYMS.items():          # the first German name of a place is its usual one
    if _en[:1].isupper() and not _de.startswith(("die ", "der ", "das ", "den ")) and _de.title() != _en \
            and _en not in ("England", "Israel", "Iran", "China", "Japan", "Portugal", "Mars", "Zugspitze"):
        _GERMAN_OF.setdefault(_en, " ".join(w[:1].upper() + w[1:] for w in _de.split()))


_TITLES_DE = {"The Sorrows of Young Werther": "Die Leiden des jungen Werthers", "Romeo and Juliet": "Romeo und Julia",
              "The Magic Flute": "Die Zauberflöte", "War and Peace": "Krieg und Frieden", "The Divine Comedy": "Die Göttliche Komödie",
              "The Last Supper": "Das Abendmahl", "The Starry Night": "Die Sternennacht", "The Four Seasons": "Die vier Jahreszeiten",
              "The Little Prince": "Der kleine Prinz", "The Metamorphosis": "Die Verwandlung", "The Trial": "Der Process",
              "The Communist Manifesto": "Das Kommunistische Manifest", "The Origin of Species": "Über die Entstehung der Arten",
              "On the Origin of Species": "Über die Entstehung der Arten", "The Odyssey": "Die Odyssee", "The Iliad": "Die Ilias",
              "The Brothers Karamazov": "Die Brüder Karamasow", "Crime and Punishment": "Schuld und Sühne", "The Tin Drum": "Die Blechtrommel",
              "The Magic Mountain": "Der Zauberberg", "Buddenbrooks": "Buddenbrooks", "The Robbers": "Die Räuber",
              "Elective Affinities": "Die Wahlverwandtschaften", "Wilhelm Meister's Apprenticeship": "Wilhelm Meisters Lehrjahre",
              "Italian Journey": "Italienische Reise", "The Sorcerer's Apprentice": "Der Zauberlehrling"}


def de_value(v: str) -> str:
    """'24 April 1452' → '24. April 1452'; '68,605,616' → '68.605.616'; 'X and Y' → 'X und Y'."""
    v = re.sub(r"^(?:on|in) ", "", v.strip())
    v = re.sub(r"\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December)\b",
               lambda m: f"{m.group(1)}. {_MONTHS[m.group(2)]}", v)
    v = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b",
               lambda m: _MONTHS[m.group(1)], v)
    v = re.sub(r"(?<=\d),(?=\d{3}\b)", ".", v)
    v = re.sub(r"(?<=\d)\.(?=\d{1,2}\b)(?!\d{3})", ",", v) if "km²" in v or " m" in v else v
    v = re.sub(r"(?<=\d) (?:metres|meters|metre|meter)\b", " m", v)
    v = re.sub(r"(?<=\d) (?:kilometres|kilometers)\b", " km", v)
    v = v.replace(" and ", " und ").replace(" (among others)", " (unter anderem)").replace("sq mi", "Quadratmeilen")
    v = v.replace(" BC", " v. Chr.").replace("(as of my data)", "(Stand meiner Daten)")
    for en_t, de_t in _TITLES_DE.items():           # well-known works under their German titles
        v = v.replace(en_t, de_t)
    # English place names back to their German names ("Rome" → "Rom", "Munich" → "München")
    return re.sub(r"\b(" + "|".join(re.escape(k) for k in sorted(_GERMAN_OF, key=len, reverse=True)) + r")\b",
                  lambda m: _GERMAN_OF[m.group(1)], v) if _GERMAN_OF else v


SENTENCES = {
    "wrote": "{x} wurde von {v} geschrieben.", "painted": "{x} wurde von {v} gemalt.",
    "invented": "{x} wurde von {v} erfunden.", "discovered": "{x} wurde von {v} entdeckt.",
    "founded_by": "{x} wurde von {v} gegründet.", "designed": "{x} wurde von {v} entworfen.",
    "composed": "{x} wurde von {v} komponiert.", "directed": "Regie bei {x} führte {v}.",
    "head_state": "Staatsoberhaupt von {x} ist {v} (Stand meiner Daten).",
    "head_gov": "Regierungschef von {x} ist {v} (Stand meiner Daten).",
    "monarch": "Staatsoberhaupt von {x} ist {v} (Stand meiner Daten).",
    "mayor": "Bürgermeister von {x} ist {v} (Stand meiner Daten).",
    "ceo": "Zu den Schlüsselpersonen bei {x} gehört {v} (Stand meiner Daten).",
    "capital": "Die Hauptstadt von {x} ist {v}.", "population": "{x} hat {v} Einwohner (Stand meiner Daten).",
    "area": "{x} ist {v} groß.", "height": "{x} ist {v} hoch.", "length": "{x} ist {v} lang.", "depth": "{x} ist {v} tief.", "fell": "{x} fiel {v}.", "sank": "{x} sank {v}.", "language": "In {x} spricht man {v}.",
    "born_when": "{x} wurde am {v} geboren.", "born_where": "{x} wurde in {v} geboren.",
    "died_when": "{x} starb am {v}.", "died_where": "{x} starb in {v}.", "died_how": "Todesursache bei {x}: {v}.",
    "founded_when": "{x} wurde {v} gegründet.", "built_when": "{x} wurde {v} fertiggestellt.",
    "released": "{x} erschien {v}.", "country": "{x} liegt in {v}.", "where": "{x} liegt in {v}.",
    "language": "In {x} spricht man {v}.", "currency": "Die Währung von {x} ist {v}.", "party": "{x} gehört zur Partei {v}.",
    "spouse": "{x} ist bzw. war mit {v} verheiratet.", "occupation": "{x}: {v}.", "from": "{x} stammt aus {v}.",
    "known_for": "{x} ist bekannt für {v}.", "works": "Zu den bekanntesten Werken von {x} gehören {v}.",
}


def de_sentence(kind: str, x: str, value: str, age_text: str | None = None) -> str | None:
    if kind == "age" and age_text:
        m = re.search(r"died at the age of (\d+)", age_text)
        if m:
            return f"{x} wurde {m.group(1)} Jahre alt."
        m = re.search(r"is (\d+) years old", age_text)
        if m:
            return f"{x} ist {m.group(1)} Jahre alt."
        return None
    tmpl = SENTENCES.get(kind)
    if tmpl is None or not value:
        return None
    v = de_value(value)
    if kind == "party":                               # the usual German party names
        v = {"Christian Democratic Union of Germany": "CDU", "Social Democratic Party of Germany": "SPD", "Alliance 90/The Greens": "Bündnis 90/Die Grünen",
             "Free Democratic Party (Germany)": "FDP", "Free Democratic Party": "FDP", "Christian Social Union in Bavaria": "CSU",
             "Alternative for Germany": "AfD", "The Left (Germany)": "Die Linke"}.get(value, v)
    if kind == "currency":
        v = v[:1].upper() + v[1:]                     # "Yen", "Euro": nouns are capitalised in German
    if kind == "born_when" and re.fullmatch(r"\d{3,4}", v):
        tmpl = "{x} wurde {v} geboren."
    if kind == "language":
        langs = {"Portuguese": "Portugiesisch", "German": "Deutsch", "French": "Französisch", "Spanish": "Spanisch", "English": "Englisch",
                 "Italian": "Italienisch", "Dutch": "Niederländisch", "Russian": "Russisch", "Japanese": "Japanisch", "Chinese": "Chinesisch",
                 "Mandarin": "Mandarin", "Arabic": "Arabisch", "Turkish": "Türkisch", "Polish": "Polnisch", "Swedish": "Schwedisch",
                 "Greek": "Griechisch", "Korean": "Koreanisch", "Hindi": "Hindi", "Danish": "Dänisch", "Norwegian": "Norwegisch",
                 "Finnish": "Finnisch", "Czech": "Tschechisch", "Hungarian": "Ungarisch"}
        v = re.sub(r"\b[A-Z][a-z]+\b", lambda m: langs.get(m.group(0), m.group(0)), v)
        if re.search(r"\b(?:Portuguese|French|Spanish|English|Italian|Dutch|Russian|Japanese|Chinese|Arabic)\b", v):
            return None                                   # an unknown language name: rather the English sentence
    if kind in ("built_when", "founded_when", "released", "fell", "sank"):
        if re.match(r"^\d{1,2}\. ", v):
            tmpl = tmpl.replace("{v}", "am {v}")         # "wurde am 31. März 1889 fertiggestellt"
        elif re.match(r"^[A-ZÄÖÜ][a-zäöü]+ \d{3,4}$", v):
            tmpl = tmpl.replace("{v}", "im {v}")
    if kind == "from" and age_text and re.search(r"\bwas from\b", age_text):
        tmpl = "{x} stammte aus {v}."
    if kind == "spouse" and age_text:
        if re.search(r"\bis married to\b", age_text):
            tmpl = "{x} ist mit {v} verheiratet."        # the English answer knows the person is alive
        elif re.search(r"\bwas married to\b", age_text):
            tmpl = "{x} war mit {v} verheiratet."
    if kind in ("born_when", "died_when") and not re.match(r"^\d{1,2}\.", v):
        tmpl = tmpl.replace("am {v}", "{v}")
        if re.match(r"^[A-ZÄÖÜ][a-zäöü]+ \d{3,4}$", v):
            v = "im " + v
    return tmpl.format(x=x, v=v)


_TERMS = {"chemie": "chemistry", "informatik": "computer science", "erdkunde": "geography", "wirtschaft": "economics", "klima": "climate",
          "klimawandel": "climate change", "schwerkraft": "gravity", "erdbeben": "earthquake", "vulkan": "volcano", "regenbogen": "rainbow",
          "schwarzes loch": "black hole", "urknall": "Big Bang", "zelle": "cell (biology)", "atom": "atom", "stromkreis": "electric circuit",
          "elektrizität": "electricity", "magnetismus": "magnetism", "verdauung": "digestion", "impfung": "vaccination", "virus": "virus",
          "bakterien": "bacteria", "treibhauseffekt": "greenhouse effect", "inflation": "inflation", "mehrwertsteuer": "value-added tax",
          "aktie": "stock", "zinsen": "interest", "blockchain": "blockchain", "künstliche intelligenz": "artificial intelligence"}


def term_variants(x: str) -> list[str]:
    """English spellings of a German technical word, for the English reading: "Photosynthese" → "Photosynthesis",
    "Biologie" → "Biology", "Physik" → "Physics", "Demokratie" → "Democracy", "Kapitalismus" → "Capitalism"."""
    low = re.sub(r"^(?:ein|eine|einen|einem|einer|der|die|das)\s+", "", x.strip().lower())
    out = []
    if low in _TERMS:
        out.append(_TERMS[low])
    rules = [(r"kratie$", "cracy"), (r"ese$", "esis"), (r"ie$", "y"), (r"ik$", "ics"), (r"ismus$", "ism"), (r"ität$", "ity"), (r"tion$", "tion"),
             (r"ur$", "ure"), (r"ei$", "y"), (r"isch$", "ic"), (r"k", "c")]
    for pat, rep in rules:
        if re.search(pat, low):
            v = re.sub(pat, rep, low, count=1)
            if v != low or pat == r"tion$":
                out.append(v)
    out += [re.sub(r"k", "c", v) for v in list(out) if "k" in v]
    seen, res = set(), []
    for v in out:
        v = v[:1].upper() + v[1:]
        if v.lower() not in seen:
            seen.add(v.lower())
            res.append(v)
    return res

