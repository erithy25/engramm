"""Answers from Wikidata and Wikipedia for the web search: the part of it that does not depend on
search engines.

Without an API key the search engines are the weak link. DuckDuckGo answers a client it distrusts
with a bot check (HTTP 202), Bing answers one without cookies with pages for the question's first
word ("real madrid founded" → realtor.com, realapp.com). Wikimedia's APIs answer every client that
names itself (a User-Agent with a contact URL: 200 requests a minute, 10 without one), so a
question about something with a Wikidata entry gets its answer from the entry's statements:

* "When was Real Madrid founded?" → Real Madrid CF, inception (P571) → 6 March 1902
* "Who is currently the president of the USA?" → United States, head of state (P35), the
  statement without an end date → Donald Trump
* "Wie hoch ist die Zugspitze?" → Zugspitze, elevation above sea level (P2044) → 2962 m

The question is read with rules: the words that name a relation ("founded", "CEO", "wie hoch"),
the rest without question words and articles is the thing asked about. The thing is looked up by
name (wbsearchentities, only entries whose name or alias is the one asked about), the property
on the first entries that have it (wbgetclaims), the names of the values in one call
(wbgetentities). "What is X" / "Wer ist X" get the first sentences of X's Wikipedia article (REST
summary), and every question gets the text of the Wikipedia article that matches its keywords
best as one more page to read (search, then the plain-text extract).

What goes out: the name of the thing asked about (Wikidata, the summary) and the question's
keywords (Wikipedia's search), over the web search channel like the question to a search engine;
the network log keeps the host only. At most two Wikimedia requests run at once (its rules: three)
and after a "too many requests" (429, 503) ENGRAMM leaves Wikimedia alone for a minute.
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass

from engramm.web.egress import Egress, Request

WIKIDATA = "https://www.wikidata.org/w/api.php?"
TIMEOUT = 8.0
QUIET = 60.0                       # seconds without Wikimedia requests after it said "too many"
ARTICLE_CHARS = 60_000


def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


@dataclass(frozen=True)
class Rel:
    """A relation a question can ask for: its words, the Wikidata properties that hold it (tried in
    turn), the kind of value and the answer sentence in English and German ({s} the thing, {v}
    the value, {when} "on 6 March 1902" / "am 6. März 1902", {w} the word the question used)."""
    key: str
    rx: re.Pattern
    props: tuple[str, ...]
    kind: str                      # "date" | "item" | "quantity" | "age"
    en: str
    de: str
    name_en: str
    name_de: str
    now: bool = False              # the value that holds today (a statement that ended does not)
    many: bool = False             # several values make the answer (founders, authors)
    drop: frozenset = frozenset()  # words of the question that belong to the relation, not the thing
    kw: re.Pattern | None = None   # the relation's own words, when ``rx`` also spans the thing ("where was X born")


def _drop(words: str) -> frozenset:
    return frozenset(words.split())


# first match wins: "who founded" before "when … founded", "where … born" before "born"
RELATIONS: tuple[Rel, ...] = (
    Rel("founder", _rx(r"^\s*(?:who|wer)\b.*\b(?:founded|started|established|gründete|gegründet|gründeten)\b|"
                       r"\b(?:founders?|gründer(?:in|innen)?)\b"),
        ("P112",), "item", "{s} was founded by {v}.", "{s} wurde von {v} gegründet.", "founded by", "Gründer", many=True,
        kw=_rx(r"\b(?:founded|started|established|gründete|gegründet|gründeten|founders?|gründer(?:in|innen)?)\b")),
    Rel("birthplace", _rx(r"^\s*where\b.*\bborn\b|^\s*wo\b.*\bgeboren\b|\b(?:place of birth|birthplace|geburtsort)\b"),
        ("P19",), "item", "{s} was born in {v}.", "{s} wurde in {v} geboren.", "place of birth", "Geburtsort",
        kw=_rx(r"\b(?:born|geboren|place of birth|birthplace|geburtsort)\b")),
    Rel("deathplace", _rx(r"^\s*where\b.*\b(?:died|did .+ die)\b|^\s*wo\b.*\b(?:gestorben|starb)\b|"
                          r"\b(?:place of death|sterbeort)\b"),
        ("P20",), "item", "{s} died in {v}.", "{s} starb in {v}.", "place of death", "Sterbeort",
        kw=_rx(r"\b(?:died|die|gestorben|starb|place of death|sterbeort)\b")),
    Rel("age", _rx(r"\bhow old\b|\bwie alt\b"), ("P569",), "age", "", "", "age", "Alter", drop=_drop("old alt years jahre")),
    Rel("birth", _rx(r"\b(?:born|birthday|date of birth|geboren|geburtstag|geburtsdatum)\b"), ("P569",), "date",
        "{s} was born {when}.", "{s} wurde {when} geboren.", "date of birth", "Geburtsdatum"),
    Rel("death", _rx(r"\b(?:died|death|gestorben|starb|todestag)\b|\bdid .+ die\b"), ("P570",), "date",
        "{s} died {when}.", "{s} starb {when}.", "date of death", "Todesdatum",
        kw=_rx(r"\b(?:died|die|death|gestorben|starb|todestag)\b")),
    Rel("release", _rx(r"\b(?:released|published|came out|launched|erschienen|veröffentlicht|herausgekommen)\b"),
        ("P577", "P571"), "date", "{s} was released {when}.", "{s} erschien {when}.", "publication date",
        "Erscheinungsdatum"),
    Rel("opening", _rx(r"\b(?:opened|inaugurated|eröffnet|eingeweiht)\b"), ("P1619", "P571"), "date",
        "{s} was opened {when}.", "{s} wurde {when} eröffnet.", "opening", "Eröffnung"),
    Rel("inception", _rx(r"\b(?:founded|established|formed|built|constructed|gegründet|gründung|entstanden|erbaut|gebaut|"
                         r"errichtet)\b"),
        ("P571", "P1619"), "date", "{s} was founded {when}.", "{s} wurde {when} gegründet.", "inception", "Gründung"),
    Rel("dissolved", _rx(r"\bdid .+ (?:fall|end)\b|\b(?:fell|dissolved|abolished|demolished|aufgelöst|abgerissen|fiel)\b"),
        ("P576",), "date", "{s} ended {when}.", "{s} endete {when}.", "end", "Ende",
        kw=_rx(r"\b(?:fall|fell|end|ended|dissolved|abolished|demolished|aufgelöst|abgerissen|fiel)\b")),
    Rel("ceo", _rx(r"\b(?:ceo|chief executive(?: officer)?|vorstandsvorsitzende[rn]?|vorstandschef(?:in)?|"
                   r"konzernchef(?:in)?|geschäftsführer(?:in)?)\b"),
        ("P169",), "item", "The CEO of {s} is {v}.", "CEO von {s} ist {v}.", "chief executive officer",
        "Vorstandsvorsitz", now=True),
    Rel("head_gov", _rx(r"\b(?:prime minister|premier|chancellor|head of government|mayor|governor|"
                        r"(?:bundes)?kanzler(?:in)?|regierungschef(?:in)?|premierminister(?:in)?|ministerpräsident(?:in)?|"
                        r"(?:ober)?bürgermeister(?:in)?|gouverneur(?:in)?)\b"),
        ("P6",), "item", "The {w} of {s} is {v}.", "{W} von {s} ist {v}.", "head of government", "Regierungschef",
        now=True),
    Rel("head_state", _rx(r"(?<!vice )\b(?:president|head of state|king|queen|monarch|emperor|(?:bundes)?präsident(?:in)?|"
                          r"staatsoberhaupt|könig(?:in)?|kaiser(?:in)?)\b"),
        ("P35", "P488"), "item", "The {w} of {s} is {v}.", "{W} von {s} ist {v}.", "head of state", "Staatsoberhaupt",
        now=True),
    Rel("capital", _rx(r"\b(?:capital|hauptstadt)\b"), ("P36",), "item", "The capital of {s} is {v}.",
        "Die Hauptstadt von {s} ist {v}.", "capital", "Hauptstadt", now=True),
    Rel("population", _rx(r"\b(?:population|inhabitants|residents|how many people|einwohner\w*|bevölkerung|"
                          r"wie viele menschen)\b"),
        ("P1082",), "quantity", "{s} has a population of {v}{asof}.", "{s} hat {v} Einwohner{asof}.", "population",
        "Einwohner", now=True, drop=_drop("people live lives living menschen leben wohnen many viele")),
    # a building's or a person's height (P2048) before the elevation of where it stands (P2044, a mountain's)
    Rel("elevation", _rx(r"\bhow (?:tall|high)\b|\b(?:height|elevation|altitude)\b|\bwie hoch\b|\bhöhe\b"),
        ("P2048", "P2044"), "quantity", "{s} is {v} high.", "{s} ist {v} hoch.", "height", "Höhe"),
    Rel("length", _rx(r"\bhow long\b|\blength\b|\bwie lang\b|\blänge\b"), ("P2043",), "quantity", "{s} is {v} long.",
        "{s} ist {v} lang.", "length", "Länge"),
    Rel("area", _rx(r"\bhow (?:big|large)\b|\b(?:area|surface area)\b|\bwie groß\b|\bfläche\b"), ("P2046", "P2048"),
        "quantity", "{s} has an area of {v}.", "{s} hat eine Fläche von {v}.", "area", "Fläche"),
    Rel("author", _rx(r"\b(?:wrote|written|author|writer|schrieb|geschrieben|autor(?:in)?|verfasst|verfasser(?:in)?)\b"),
        ("P50",), "item", "{s} was written by {v}.", "{s} wurde von {v} geschrieben.", "author", "Autor", many=True),
    Rel("director", _rx(r"\b(?:directed|director|regie|regisseur(?:in)?)\b"), ("P57",), "item",
        "{s} was directed by {v}.", "Regie bei {s} führte {v}.", "director", "Regie", many=True),
    Rel("composer", _rx(r"\b(?:composed|composer|komponiert|komponist(?:in)?)\b"), ("P86",), "item",
        "{s} was composed by {v}.", "{s} wurde von {v} komponiert.", "composer", "Komponist", many=True),
    Rel("painter", _rx(r"\b(?:painted|painter|gemalt|maler(?:in)?)\b"), ("P170",), "item", "{s} was painted by {v}.",
        "{s} wurde von {v} gemalt.", "creator", "Urheber"),
    Rel("architect", _rx(r"\b(?:architect|designed|architekt(?:in)?|entworfen)\b"), ("P84",), "item",
        "{s} was designed by {v}.", "{s} wurde von {v} entworfen.", "architect", "Architekt", many=True),
    Rel("inventor", _rx(r"\b(?:invented|inventor|discovered|discoverer|erfunden|erfinder(?:in)?|entdeckt|entdecker(?:in)?)\b"),
        ("P61",), "item", "{s} was {w} by {v}.", "{s} wurde von {v} {w}.", "discoverer or inventor", "Entdecker", many=True),
    Rel("coach", _rx(r"\b(?:head coach|coach|manager|trainer(?:in)?|cheftrainer(?:in)?|chefcoach)\b"), ("P286",), "item",
        "The head coach of {s} is {v}.", "Trainer von {s} ist {v}.", "head coach", "Cheftrainer", now=True),
    Rel("hq", _rx(r"\b(?:headquarters|headquartered|hauptsitz|firmensitz|unternehmenssitz)\b"), ("P159",), "item",
        "{s} is headquartered in {v}.", "{s} hat seinen Sitz in {v}.", "headquarters", "Sitz", now=True),
    Rel("owner", _rx(r"\b(?:owns|owner|owned by|gehört|besitzer(?:in)?|eigentümer(?:in)?)\b"), ("P127",), "item",
        "{s} is owned by {v}.", "{s} gehört {v}.", "owned by", "Eigentümer", now=True, many=True),
    Rel("currency", _rx(r"\b(?:currency|währung)\b"), ("P38",), "item", "The currency of {s} is {v}.",
        "Die Währung von {s} ist {v}.", "currency", "Währung", now=True),
    Rel("language", _rx(r"\b(?:official languages?|what languages? (?:is|are) spoken|amtssprachen?|welche sprache)\b"),
        ("P37",), "item", "The official language of {s}: {v}.", "Amtssprache von {s}: {v}.", "official language",
        "Amtssprache", many=True, kw=_rx(r"\b(?:official|languages?|spoken|amtssprachen?|sprache)\b")),
    Rel("spouse", _rx(r"\b(?:married|wife|husband|spouse|verheiratet|ehefrau|ehemann)\b|\b(?:frau|mann)\s+von\b"),
        ("P26",), "item", "{s} is married to {v}.", "{s} ist mit {v} verheiratet.", "spouse", "Ehepartner", now=True,
        kw=_rx(r"\b(?:married|wife|husband|spouse|verheiratet|ehefrau|ehemann|frau|mann)\b")),
    Rel("children", _rx(r"\b(?:children|kids|kinder)\b"), ("P40",), "item", "{s}'s children: {v}.", "Kinder von {s}: {v}.",
        "child", "Kinder", many=True),
    Rel("stadium", _rx(r"\b(?:stadium|home ground|stadion|heimspielstätte)\b"), ("P115",), "item", "{s} plays at {v}.",
        "Heimstadion von {s}: {v}.", "home venue", "Heimstadion", now=True),
    # "Who won the 2022 FIFA World Cup?" — a season's or a race's winner (the live check answered with a
    # sentence about rainbow flags at that World Cup)
    Rel("winner", _rx(r"^\s*(?:who|which (?:team|country|club|nation|player|driver|film|movie))\s+(?:has\s+)?won\b|"
                      r"\bwinners? of\b|^\s*wer\s+(?:hat|gewann)\b.*\b(?:gewonnen|gewann)\b|"
                      r"\b(?:sieger|gewinner)(?:in)?\s+(?:der|des|von)\b"),
        ("P1346",), "item", "{v} won {s}.", "{v} gewann {s}.", "winner", "Sieger", now=True,
        drop=_drop("team country club nation player driver film movie"),
        kw=_rx(r"\b(?:won|winners?|gewann|gewonnen|sieger(?:in)?|gewinner(?:in)?)\b")),
    Rel("team", _rx(r"\bplays? for\b|\bwhich (?:team|club)\b|\bwelche[nm]? (?:verein|team|klub|club)\b|\bspielt (?:für|bei)\b"),
        ("P54",), "item", "{s} plays for {v}.", "{s} spielt für {v}.", "member of sports team", "Verein", now=True,
        kw=_rx(r"\b(?:plays?|playing|team|club|verein|klub|spielt)\b")),
    Rel("party", _rx(r"\b(?:political party|which party|partei)\b"), ("P102",), "item", "{s} is a member of the {v}.",
        "{s} ist Mitglied der Partei {v}.", "member of political party", "Partei", now=True),
    Rel("employees", _rx(r"\b(?:employees|staff|mitarbeiter\w*|beschäftigte)\b"), ("P1128",), "quantity",
        "{s} has {v} employees{asof}.", "{s} hat {v} Mitarbeiter{asof}.", "employees", "Mitarbeiter", now=True,
        drop=_drop("many viele")),
    Rel("revenue", _rx(r"\b(?:revenue|turnover|umsatz)\b"), ("P2139",), "quantity", "The revenue of {s} is {v}{asof}.",
        "Der Umsatz von {s} beträgt {v}{asof}.", "revenue", "Umsatz", now=True),
    Rel("gdp", _rx(r"\b(?:gdp|gross domestic product|bip|bruttoinlandsprodukt)\b"), ("P2131",), "quantity",
        "The GDP of {s} is {v}{asof}.", "Das BIP von {s} beträgt {v}{asof}.", "nominal GDP", "BIP", now=True),
    Rel("net_worth", _rx(r"\b(?:net worth|how rich|vermögen|wie reich)\b"), ("P2218",), "quantity",
        "{s} has a net worth of {v}{asof}.", "Das Vermögen von {s} beträgt {v}{asof}.", "net worth", "Vermögen", now=True),
    Rel("located", _rx(r"^\s*(?:where is|where are|where's|wo liegt|wo liegen|wo ist|wo befindet sich)\b|\blocated\b"),
        ("P131", "P17"), "item", "{s} is in {v}.", "{s} liegt in {v}.", "located in", "liegt in",
        kw=_rx(r"\b(?:located|liegt|liegen|befindet)\b")),
    Rel("country", _rx(r"\b(?:which|what|in which) country\b|\bwelche[mn]? land\b"), ("P17",), "item", "{s} is in {v}.",
        "{s} liegt in {v}.", "country", "Staat", kw=_rx(r"\b(?:country|land|liegt|is)\b")),
    Rel("nationality", _rx(r"\b(?:nationality|citizenship|staatsangehörigkeit|nationalität)\b"), ("P27",), "item",
        "{s} is a citizen of {v}.", "Staatsangehörigkeit von {s}: {v}.", "citizenship", "Staatsangehörigkeit", many=True),
    Rel("parent", _rx(r"\b(?:parent company|parent organi[sz]ation|mutterkonzern|muttergesellschaft)\b"), ("P749",),
        "item", "{s} belongs to {v}.", "{s} gehört zu {v}.", "parent organization", "Mutterkonzern", now=True),
    Rel("boiling", _rx(r"\bboiling (?:point|temperature)\b|\bsiede(?:punkt|temperatur)\b|"
                       r"\bat what temperature does .+ boil\b|\bbei wie viel(?:en)? grad (?:siedet|kocht)\b"),
        ("P2102",), "quantity", "The boiling point of {s} is {v}.", "Der Siedepunkt von {s} liegt bei {v}.",
        "boiling point", "Siedepunkt", kw=_rx(r"\bboiling (?:point|temperature)\b|\bsiede(?:punkt|temperatur)\b|"
                                              r"\bat what temperature does\b|\bboil\b|\bbei wie viel(?:en)? grad\b|"
                                              r"\bsiedet\b|\bkocht\b")),
    Rel("melting", _rx(r"\bmelting (?:point|temperature)\b|\bschmelz(?:punkt|temperatur)\b|"
                       r"\bat what temperature does .+ melt\b|\bbei wie viel(?:en)? grad schmilzt\b"),
        ("P2101",), "quantity", "The melting point of {s} is {v}.", "Der Schmelzpunkt von {s} liegt bei {v}.",
        "melting point", "Schmelzpunkt", kw=_rx(r"\bmelting (?:point|temperature)\b|\bschmelz(?:punkt|temperatur)\b|"
                                               r"\bat what temperature does\b|\bmelt\b|\bbei wie viel(?:en)? grad\b|"
                                               r"\bschmilzt\b")),
)
# a value found under another property than the relation's first one has its own sentence
_BY_PROP = {"P2048": ("{s} is {v} tall.", "{s} ist {v} groß."), "P17": ("{s} is in {v}.", "{s} liegt in {v}."),
            "P488": ("The {w} of {s} is {v}.", "{W} von {s} ist {v}."), "P1619": (None, None), "P571": (None, None)}

# question words, auxiliaries, articles, linking prepositions and time words: what is left of a
# question without them and without the relation's words names the thing asked about
_FILLER = frozenset("""who whom whose what what's which when where where's why how is are was were be been being am do does
did done has have had will would can could should shall may might must the a an of in on at to for from by with and or about
as into its this that these those there here me my you your please tell know say give show find search look up google
ist sind war waren bin bist seid wird werden wurde wurden worden hat haben hatte hatten habe kann können könnte soll sollte
muss der die das den dem des ein eine einer eines einem einen von vom zu zum zur im am an auf aus bei mit nach für über um
durch gegen ohne bis und oder es er sie wer wen wem wessen was welche welcher welches welchen welchem wann wo woher wohin
warum wieso weshalb wie mir mich mal bitte sag sage weißt du kannst current currently now today presently actually still
latest recent recently aktuell aktuelle aktueller aktuellen aktuelles derzeit derzeitige derzeitiger derzeitigen jetzt
heute momentan zurzeit gerade amtierende amtierender amtierenden""".split())
# "the German chancellor" → Germany
_DEMONYMS = {
    "german": "Germany", "germany's": "Germany", "deutsche": "Deutschland", "deutschen": "Deutschland",
    "deutscher": "Deutschland", "deutschlands": "Deutschland", "american": "United States", "us": "United States",
    "u.s.": "United States", "usa": "United States", "amerikanische": "USA", "amerikanischen": "USA",
    "french": "France", "französische": "Frankreich", "französischen": "Frankreich", "british": "United Kingdom",
    "uk": "United Kingdom", "britische": "Vereinigtes Königreich", "britischen": "Vereinigtes Königreich",
    "russian": "Russia", "russische": "Russland", "russischen": "Russland", "chinese": "China",
    "chinesische": "China", "chinesischen": "China", "italian": "Italy", "italienische": "Italien",
    "italienischen": "Italien", "spanish": "Spain", "spanische": "Spanien", "spanischen": "Spanien",
    "austrian": "Austria", "österreichische": "Österreich", "österreichischen": "Österreich", "swiss": "Switzerland",
    "schweizer": "Schweiz", "canadian": "Canada", "kanadische": "Kanada", "japanese": "Japan", "japanische": "Japan",
    "indian": "India", "indische": "Indien", "brazilian": "Brazil", "turkish": "Turkey", "türkische": "Türkei",
    "ukrainian": "Ukraine", "ukrainische": "Ukraine", "polish": "Poland", "polnische": "Polen", "dutch": "Netherlands",
    "niederländische": "Niederlande", "israeli": "Israel", "israelische": "Israel", "australian": "Australia",
    "mexican": "Mexico", "argentinian": "Argentina", "irish": "Ireland", "swedish": "Sweden", "norwegian": "Norway",
    "danish": "Denmark", "finnish": "Finland", "greek": "Greece", "portuguese": "Portugal", "belgian": "Belgium",
}
# a head of government or state without a country: the one a German speaker means
_IMPLIED = {"bundeskanzler": "Deutschland", "bundeskanzlerin": "Deutschland", "kanzler": "Deutschland",
            "kanzlerin": "Deutschland", "bundespräsident": "Deutschland", "bundespräsidentin": "Deutschland",
            "chancellor": "Germany"}

# "What is X?" / "Wer ist X?": the first sentences of X's article
_DEFINE = (
    _rx(r"^\s*(?:what|who)(?:'s|\s+is|\s+are|\s+was|\s+were)\s+(?:a\s+|an\s+|the\s+)?(?P<x>.+?)\s*[?.!]*$"),
    _rx(r"^\s*(?:tell me (?:something |more )?about|define|explain)\s+(?:a\s+|an\s+|the\s+)?(?P<x>.+?)\s*[?.!]*$"),
    _rx(r"^\s*what does\s+(?P<x>.+?)\s+(?:mean|stand for)\s*[?.!]*$"),
    _rx(r"^\s*(?:wofür|für was)\s+steht\s+(?:die\s+|der\s+|das\s+)?(?:abkürzung\s+)?(?P<x>.+?)\s*[?.!]*$"),
    _rx(r"^\s*(?:was|wer)\s+(?:ist|sind|war|waren)\s+(?:ein\s+|eine\s+|der\s+|die\s+|das\s+)?(?P<x>.+?)\s*[?.!]*$"),
    _rx(r"^\s*(?:erzähl(?:e)?\s+mir\s+(?:etwas\s+|was\s+|mehr\s+)?(?:über|von)|was bedeutet|was heißt|erkläre?(?:\s+mir)?)\s+"
        r"(?:ein\s+|eine\s+|der\s+|die\s+|das\s+|den\s+)?(?P<x>.+?)\s*[?.!]*$"),
)
# "what does X mean / stand for", "wofür steht X", "was bedeutet X": what X is, whatever relation word X holds
_MEANS = _rx(r"^\s*(?:what does\s+.+?\s+(?:mean|stand for)|(?:wofür|für was)\s+steht\s.+|was bedeutet\s.+)\s*[?.!]*$")
# questions about the moment or the asker: no encyclopedia article answers them
_VOLATILE = _rx(r"\b(?:weather|forecast|wetter|price|prices|preis|preise|kurs|stock|aktie|score|ergebnis|result|news|"
                r"nachrichten|today|tonight|tomorrow|yesterday|heute|morgen|gestern|open|opening|geöffnet|öffnungszeiten|"
                r"time is it|uhrzeit|my|mine|your|mein|meine|dein|deine|best|beste|besten|cheapest|günstigste|last|latest|"
                r"letzte[nmrs]?|neueste[nmrs]?)\b")

_WORD = re.compile(r"[^\W_][\w'’.\-]*")
_MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December"],
           "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                  "November", "Dezember"]}
# units of Wikidata quantities: (English, German)
UNITS = {"Q11573": ("m", "m"), "Q828224": ("km", "km"), "Q712226": ("km²", "km²"), "Q25343": ("m²", "m²"),
         "Q3710": ("ft", "ft"), "Q253276": ("mi", "mi"), "Q174728": ("cm", "cm"), "Q174789": ("mm", "mm"),
         "Q11570": ("kg", "kg"), "Q191118": ("t", "t"), "Q11229": ("%", "%"), "Q35852": ("ha", "ha"),
         "Q232291": ("sq mi", "sq mi"), "Q180154": ("km/h", "km/h"), "Q211256": ("mph", "mph"),
         "Q577": ("years", "Jahre"), "Q4917": ("US$", "US-Dollar"), "Q4916": ("€", "Euro"), "Q25224": ("£", "Pfund"),
         "Q8146": ("¥", "Yen"), "Q25344": ("CHF", "Franken"), "Q41044": ("₽", "Rubel"), "Q39099": ("¥", "Renminbi"),
         "Q25267": ("°C", "°C"), "Q42289": ("°F", "°F"), "Q11579": ("K", "K")}
_CURRENCY = {"Q4917", "Q4916", "Q25224", "Q8146", "Q25344", "Q41044", "Q39099"}
# "Argentina national football team won the 2022 FIFA World Cup." says "Argentina"
_NATIONAL_TEAM = re.compile(r"\s+(?:men's\s+|women's\s+)?national\s+(?:association\s+)?(?:football|soccer|rugby union|"
                            r"rugby league|rugby|basketball|ice hockey|handball|volleyball|cricket|baseball|water polo|"
                            r"field hockey)\s+team$", re.I)


@dataclass
class Asked:
    """What a question asks: a relation of a thing ("founded" of "real madrid"), or what the thing is."""
    subject: str
    rel: Rel | None = None
    word: str = ""                 # the question's word for the relation ("president", "Bundeskanzler")
    typed: str = ""                # the thing as the question names it ("usa", "German"); "" when implied


@dataclass
class Fact:
    """An answer from Wikimedia: the sentence, the short answer, where it comes from."""
    text: str                      # "Real Madrid was founded on 6 March 1902."
    answer: str                    # "6 March 1902"
    kind: str                      # the relation's kind, or "summary" for "what is X"
    title: str                     # the thing's name: "Real Madrid CF"
    url: str                       # its Wikipedia article (else its Wikidata page)
    evidence: str                  # "Real Madrid CF – inception: 6 March 1902" or the summary itself
    person: bool = False           # the answer names a person ("he" can refer to it next)
    qid: str = ""                  # the thing's Wikidata item ("Q8682"): a follow-up's "it" is that one
    desc: str = ""                 # its description ("association football club in Madrid, Spain")
    values: tuple = ()             # the answer's items ("Q3052772"): a follow-up's "he" is that one

    @property
    def host(self) -> str:
        return urllib.parse.urlsplit(self.url).hostname or "wikidata.org"


def parse(question: str, lang: str = "en") -> Asked | None:
    """The relation a question asks for and the thing it asks about, or what it asks to define;
    None when it is neither (or about the asker, or about the moment)."""
    q = re.sub(r"\s+", " ", question.strip())
    q = re.sub(r"(?i)\b(what|who|where|how)['’]s\b", r"\1 is", q)
    if _MEANS.match(q):                          # "What does GDP mean?" asks what GDP is, not the GDP of "mean"
        x = defined(q)
        return Asked(x, typed=x) if x else None
    for rel in RELATIONS:
        for m in rel.rx.finditer(q):
            word = m.group(0)
            # "Stephen King", "Queen Elizabeth": a capitalised relation word inside a name is part of it
            before = q[:m.start()].split()
            if word[:1].isupper() and before and before[-1][:1].isupper() and before[-1].lower() not in _FILLER \
                    and lang != "de":
                continue
            rest = rel.kw.sub(" ", q) if rel.kw is not None else (q[:m.start()] + " " + q[m.end():])
            subject = typed = _subject(rest.strip(), rel)
            low = subject.lower()
            if low in _DEMONYMS:
                subject = _DEMONYMS[low]
            if not subject:
                key = re.sub(r"\W", "", word.lower())
                subject = _IMPLIED.get(key) or ("Deutschland" if lang == "de" and rel.key in ("head_gov", "head_state")
                                                else "")
            if subject and len(subject.split()) <= 6 and not _VOLATILE.search(subject):
                return Asked(subject, rel, _word(word), typed)
            break
    x = defined(q)
    return Asked(x, typed=x) if x else None


def defined(question: str) -> str | None:
    """The X of "what is X" / "wer ist X" (a thing to define), or None."""
    q = re.sub(r"(?i)\b(what|who|where|how)['’]s\b", r"\1 is", " ".join(question.split()))
    for rx in _DEFINE:
        m = rx.match(q)
        if m:
            x = m.group("x").strip(" \"'“”„")
            if x and len(x.split()) <= 6 and not _VOLATILE.search(x) and not re.search(r"\b(?:you|du|i|ich)\b", x, re.I):
                return x
            return None
    return None


def _word(word: str) -> str:
    """The relation word as the answer sentence uses it: "the president" → "president"."""
    return re.sub(r"(?i)^(?:the|a|an)\s+", "", word.strip())


def _subject(rest: str, rel: Rel) -> str:
    words = [w.rstrip(".?!,;:") for w in _WORD.findall(rest)]
    keep = [re.sub(r"['’]s$", "", w) for w in words
            if w and w.lower() not in _FILLER and w.lower() not in rel.drop and w.lower().rstrip("'’s") not in _FILLER]
    return " ".join(keep).strip()


def _same_name(asked: str, hit: dict) -> bool:
    """Is a search hit the thing asked about: its name, the alias the search matched or its name
    without a suffix ("Real Madrid" for "Real Madrid Club de Fútbol"), spelled alike?"""
    want = " ".join(re.sub(r"[^\w ]", " ", asked.lower()).split())
    names = [str(hit.get("label") or ""), str((hit.get("match") or {}).get("text") or "")]
    names += [str(a) for a in (hit.get("aliases") or [])]
    for name in names:
        have = " ".join(re.sub(r"[^\w ]", " ", name.lower()).split())
        if not have:
            continue
        if have == want or difflib.SequenceMatcher(None, have, want).ratio() >= 0.85:
            return True
        if have.startswith(want + " ") and len(want) >= 4:      # "real madrid" → "real madrid club de futbol"
            return True
    return False


def _disambiguation(hit: dict) -> bool:
    d = str(hit.get("description") or "").lower()
    return "disambiguation" in d or "begriffsklärung" in d or d.startswith(("wikimedia list", "wikimedia-liste"))


# -- statements and values ------------------------------------------------------------------------

def _time_key(t: str | None) -> tuple[int, int, int]:
    m = re.match(r"([+-])(\d+)-(\d\d)-(\d\d)", t or "")
    if not m:
        return (0, 0, 0)
    year = int(m.group(2)) * (-1 if m.group(1) == "-" else 1)
    return (year, int(m.group(3)), int(m.group(4)))


def _qualifier(st: dict, prop: str) -> dict | None:
    for q in (st.get("qualifiers") or {}).get(prop, []):
        if q.get("snaktype") == "value":
            return q.get("datavalue", {}).get("value")
    return None


def _ended(st: dict, today: tuple[int, int, int]) -> bool:
    """Not true today: it ended (end time today or before) or has not begun (start time after today)."""
    end, start = _qualifier(st, "P582"), _qualifier(st, "P580")
    return (isinstance(end, dict) and _time_key(end.get("time")) <= today) or \
        (isinstance(start, dict) and _time_key(start.get("time")) > today)


def choose(statements: list[dict], now: bool, many: bool, today: dt.date | None = None) -> list[dict]:
    """The statements that answer: none deprecated, the preferred ones if there are; for a question
    about today none that ended (an end time before today) or has not begun; the newest first (point
    in time, then start time); one, or up to three for a relation with several values."""
    day = today or dt.date.today()
    key_today = (day.year, day.month, day.day)
    pool = [s for s in statements if s.get("rank") != "deprecated"
            and (s.get("mainsnak") or {}).get("snaktype") == "value"]
    if now:
        pool = [s for s in pool if not _ended(s, key_today)]
    if not pool:
        return []
    preferred = [s for s in pool if s.get("rank") == "preferred"]
    pool = preferred or pool

    def newest(s: dict) -> tuple:
        point = _qualifier(s, "P585")
        start = _qualifier(s, "P580")
        return (_time_key(point.get("time")) if isinstance(point, dict) else (0, 0, 0),
                _time_key(start.get("time")) if isinstance(start, dict) else (0, 0, 0))
    if now:
        pool = sorted(pool, key=newest, reverse=True)
    return pool[:3] if many else pool[:1]


def format_date(value: dict, lang: str) -> tuple[str, str]:
    """(date, "when" phrase): ("6 March 1902", "on 6 March 1902") / ("6. März 1902", "am 6. März 1902");
    by precision: day, month ("in March 1902"), year ("in 1902" / "1902"), decade, century."""
    m = re.match(r"([+-])(\d+)-(\d\d)-(\d\d)", str(value.get("time") or ""))
    if not m:
        return "", ""
    year, month, day = int(m.group(2)), int(m.group(3)), int(m.group(4))
    bc = m.group(1) == "-"
    prec = int(value.get("precision") or 11)
    de = lang == "de"
    y = (f"{year} v. Chr." if de else f"{year} BC") if bc else str(year)
    months = _MONTHS["de" if de else "en"]
    if prec >= 11 and month and day:
        text = f"{day}. {months[month - 1]} {y}" if de else f"{day} {months[month - 1]} {y}"
        return text, (f"am {text}" if de else f"on {text}")
    if prec == 10 and month:
        text = f"{months[month - 1]} {y}"
        return text, (f"im {text}" if de else f"in {text}")
    if prec == 9 or prec >= 10:
        return y, (y if de else f"in {y}")
    if prec == 8:
        decade = year - year % 10
        return (f"{decade}er-Jahre", f"in den {decade}er-Jahren") if de else (f"{decade}s", f"in the {decade}s")
    century = (year - 1) // 100 + 1
    return (f"{century}. Jahrhundert", f"im {century}. Jahrhundert") if de else (f"{_ordinal(century)} century",
                                                                             f"in the {_ordinal(century)} century")


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def format_number(x: float, lang: str, decimals: int = 2) -> str:
    """3913644 → "3,913,644" / "3.913.644"; 1232.5 → "1,232.5" / "1.232,5"."""
    if abs(x - round(x)) < 1e-9 or decimals == 0:
        s = f"{int(round(x)):,}"
    else:
        s = f"{x:,.{decimals}f}".rstrip("0").rstrip(".")
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".") if lang == "de" else s


def format_quantity(value: dict, lang: str, unit_names: dict | None = None) -> str:
    """A Wikidata quantity with its unit: "2,962 m", "3,913,644", "US$27.36 trillion" / "27,36 Billionen US-Dollar"."""
    try:
        amount = float(str(value.get("amount", "0")))
    except ValueError:
        return ""
    unit = str(value.get("unit") or "1").rsplit("/", 1)[-1]
    de = lang == "de"
    if unit in _CURRENCY or (abs(amount) >= 1e9 and unit != "1"):
        for size, en_word, de_word in ((1e12, "trillion", "Billionen"), (1e9, "billion", "Milliarden"),
                                       (1e6, "million", "Millionen")):
            if abs(amount) >= size:
                num = f"{format_number(amount / size, lang)} {de_word if de else en_word}"
                break
        else:
            num = format_number(amount, lang)
        sym = UNITS.get(unit, (None, None))[1 if de else 0] or (unit_names or {}).get(unit, "")
        if not sym:
            return num
        return f"{sym}{num}" if not de and sym in ("US$", "€", "£", "¥", "₽") else f"{num} {sym}"
    # as precise as a sentence needs: 2962.06 m → "2,962 m", 12.345 km → "12.3 km", 1.81 m → "1.81 m"
    num = format_number(amount, lang, decimals=0 if abs(amount) >= 1000 else 1 if abs(amount) >= 10 else 2)
    if unit == "1":
        return num
    sym = UNITS.get(unit, (None, None))[1 if de else 0] or (unit_names or {}).get(unit, "")
    return f"{num} {sym}".strip()


def _join(names: list[str], lang: str) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + (" und " if lang == "de" else " and ") + names[-1]


_DESC_STOP = frozenset("""a an the of in on at for and or to from by with based located former born died
der die das des den dem ein eine einer eines in im am an auf aus bei mit von vom zu zur zum und oder
""".split())


def _desc_words(desc: str) -> set[str]:
    """The words of a Wikidata description that say what kind of thing it is (years and fillers aside)."""
    return {w for w in re.findall(r"[^\W\d_]{2,}", desc.lower()) if w not in _DESC_STOP}


def _pinned(name: str, pin: dict[str, str] | None) -> str | None:
    """The Wikidata item the conversation fixed for this name, if any."""
    if not pin or not name:
        return None
    want = " ".join(name.lower().split())
    return next((qid for k, qid in pin.items() if " ".join(k.lower().split()) == want), None)


def _recase(text: str, typed: str, label: str) -> str:
    """The thing as the question typed it ("real madrid"), written as its name is ("Real Madrid")."""
    out = []
    for w in typed.split():
        m = re.search(rf"\b{re.escape(w)}\b", label, re.I)
        out.append(m.group(0) if m else w)
    fixed = " ".join(out)
    return re.sub(re.escape(typed), fixed, text, count=1, flags=re.I) if typed and fixed != typed else text


# -- the client -------------------------------------------------------------------------------------

class WikiKnowledge:
    """Wikidata's statements and Wikipedia's articles over the egress (search channel)."""

    def __init__(self, egress: Egress):
        self.egress = egress
        self._quiet_until = 0.0
        self._lock = threading.Lock()

    # transport
    def _get(self, url: str, host: str, what: str, explicit: bool) -> dict | None:
        if time.time() < self._quiet_until:
            return None
        req = Request("search", url, what, (host,), headers=(("Accept", "application/json"),), explicit=explicit,
                      plain_agent=True, timeout=TIMEOUT)
        # through the pool: these run while the search engine is asked (the service answers one at a time)
        res = self.egress.fetch_many([req])[0]
        if res is None:
            return None
        if res.status in (429, 503):
            with self._lock:
                self._quiet_until = time.time() + QUIET
            return None
        if not res.ok:
            return None
        try:
            return json.loads(res.body.decode("utf-8", "replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _wikidata(self, explicit: bool, **params) -> dict | None:
        return self._get(WIKIDATA + urllib.parse.urlencode({**params, "format": "json"}), "www.wikidata.org",
                         "facts:wikidata", explicit)

    def find(self, name: str, lang: str, explicit: bool) -> list[dict]:
        """Entries named ``name`` (or with it as an alias), best first; no disambiguation pages."""
        hits: list[dict] = []
        for lg in dict.fromkeys((lang, "en")):
            d = self._wikidata(explicit, action="wbsearchentities", search=name[:120], language=lg, uselang=lang,
                               limit=7, type="item")
            hits = [h for h in ((d or {}).get("search") or []) if not _disambiguation(h) and _same_name(name, h)]
            if hits:
                break
        return hits

    def same_kind(self, name: str, like: str, lang: str, explicit: bool, like_desc: str = "") -> str | None:
        """The item named ``name`` that is the same kind of thing as the item ``like`` ("Barcelona"
        after Real Madrid: the football club, not the city; "Bayern" after a club: FC Bayern, not
        Bavaria). Candidates: the name's own search (names, aliases) and Wikidata's full-text search
        (which finds "FC Barcelona" for "Barcelona" when that is no alias). The same kind: a
        description that shares at least half the words of like's description ("association football
        club in Madrid, Spain" — not "capital city of Catalonia, Spain"); of those, the one most
        Wikipedias have an article on (FC Barcelona, not its reserve team, nor the club of Tarrafal).
        Classes (P31) did not do: Wikidata types Real Madrid and FC Barcelona differently (CI, 2026).
        None when nothing qualifies — then the plain search decides."""
        if not like_desc:
            like_desc = (self.labels([like], lang, explicit).get(like) or {}).get("description", "")
        kind = _desc_words(like_desc)
        if not kind:
            return None
        cands: list[str] = []
        d = self._wikidata(explicit, action="wbsearchentities", search=name[:120], language=lang, uselang=lang,
                           limit=7, type="item")
        cands += [str(h.get("id") or "") for h in (d or {}).get("search") or []]
        r = self._wikidata(explicit, action="query", list="search", srsearch=name[:120], srlimit=10, srnamespace=0,
                           srprop="")
        cands += [str(h.get("title") or "") for h in ((r or {}).get("query") or {}).get("search") or []]
        cands = [q for q in dict.fromkeys(cands) if re.fullmatch(r"Q\d+", q) and q != like][:15]
        if not cands:
            return None
        e = self._wikidata(explicit, action="wbgetentities", ids="|".join(cands),
                           props="labels|aliases|descriptions|sitelinks",
                           languages="|".join(dict.fromkeys((lang, "mul", "en"))))
        ents = (e or {}).get("entities") or {}
        want = " ".join(name.lower().split())
        best, best_key = None, None
        for qid in cands:
            ent = ents.get(qid) or {}
            names = [" ".join(str(v.get("value") or "").lower().split()) for v in (ent.get("labels") or {}).values()]
            names += [" ".join(str(a.get("value") or "").lower().split())
                      for vs in (ent.get("aliases") or {}).values() for a in vs]
            if not any(t == want or re.search(rf"\b{re.escape(want)}\b", t) for t in names):
                continue                                 # not named so
            descs = ent.get("descriptions") or {}
            desc = str((descs.get(lang) or descs.get("en") or {}).get("value") or "")
            shared = len(_desc_words(desc) & kind) / len(kind)
            if shared < 0.5:
                continue                                 # another kind of thing
            key = (len(ent.get("sitelinks") or {}), shared, -cands.index(qid))
            if best_key is None or key > best_key:
                best, best_key = qid, key
        return best

    def labels(self, ids: list[str], lang: str, explicit: bool) -> dict[str, dict]:
        """{id: {"label", "description", "url"}} — names in the conversation's language (else the one
        for all languages, "mul", which many people's items have instead of "en" since 2024 — "Emmanuel
        Macron" — else English), the Wikipedia article in it (else the English one, else the Wikidata
        page). An item without a name is left out: its id ("Q3052772") is no answer."""
        ids = list(dict.fromkeys(i for i in ids if re.fullmatch(r"Q\d+", i)))[:40]
        if not ids:
            return {}
        d = self._wikidata(explicit, action="wbgetentities", ids="|".join(ids), props="labels|descriptions|sitelinks",
                           languages="|".join(dict.fromkeys((lang, "mul", "en"))), sitefilter=f"{lang}wiki|enwiki")
        out = {}
        for qid, e in ((d or {}).get("entities") or {}).items():
            labels, descs, links = e.get("labels") or {}, e.get("descriptions") or {}, e.get("sitelinks") or {}
            label = (labels.get(lang) or labels.get("mul") or labels.get("en") or {}).get("value")
            if not label:
                continue
            desc = (descs.get(lang) or descs.get("en") or {}).get("value") or ""
            url = f"https://www.wikidata.org/wiki/{qid}"
            for lg in dict.fromkeys((lang, "en")):
                title = (links.get(f"{lg}wiki") or {}).get("title")
                if title:
                    url = f"https://{lg}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                    break
            out[qid] = {"label": label, "description": desc, "url": url}
        return out

    # answers
    def answer(self, question: str, lang: str = "en", explicit: bool = False,
               pin: dict[str, str] | None = None) -> Fact | None:
        """The answer to a question about a thing's relation (from its Wikidata statements) or about
        what a thing is (its Wikipedia article's first sentences); None when there is none. ``pin``:
        names whose Wikidata item is known from the conversation ({"Barcelona": "Q7156"} after
        "When was Real Madrid founded?" — the club, not the city; {"Emmanuel Macron": "Q3052772"}
        for "how old is he?")."""
        asked = parse(question, lang)
        if asked is None:
            return None
        if asked.rel is not None:
            fact = self._statement(question, asked, lang, explicit, pin)
            if fact is not None:
                return fact
            # no statement: what the whole "who/what is X" names, if the question is one
            x = defined(question)
            return self.summary(x, lang, explicit, pin) if x else None
        return self.summary(asked.subject, lang, explicit, pin)

    def _statement(self, question: str, asked: Asked, lang: str, explicit: bool,
                   pin: dict[str, str] | None = None) -> Fact | None:
        rel = asked.rel
        pinned = _pinned(asked.subject, pin)
        hits = [{"id": pinned}] if pinned else self.find(asked.subject, lang, explicit)[:3 if len(rel.props) == 1 else 2]
        for hit in hits:
            qid = hit.get("id", "")
            for prop in rel.props:
                d = self._wikidata(explicit, action="wbgetclaims", entity=qid, property=prop)
                chosen = choose(((d or {}).get("claims") or {}).get(prop) or [], rel.now, rel.many)
                values = [s["mainsnak"]["datavalue"] for s in chosen if "datavalue" in s.get("mainsnak", {})]
                if not values:
                    continue
                death = None
                if rel.kind == "age":
                    dd = self._wikidata(explicit, action="wbgetclaims", entity=qid, property="P570")
                    died = choose(((dd or {}).get("claims") or {}).get("P570") or [], False, False)
                    death = died[0]["mainsnak"].get("datavalue") if died else None
                return self._compose(question, asked, lang, explicit, qid, prop, values, chosen, death,
                                     str(hit.get("description") or ""), bool(pinned))
        return None

    def _compose(self, question: str, asked: Asked, lang: str, explicit: bool, qid: str, prop: str,
                 values: list[dict], chosen: list[dict], death: dict | None, desc: str = "",
                 pinned: bool = False) -> Fact | None:
        rel = asked.rel
        items = [v["value"]["id"] for v in values if v.get("type") == "wikibase-entityid"]
        units = [str(v["value"].get("unit", "")).rsplit("/", 1)[-1] for v in values if v.get("type") == "quantity"]
        names = self.labels([qid] + items + [u for u in units if u not in UNITS], lang, explicit)
        thing = names.get(qid, {"label": asked.subject, "url": f"https://www.wikidata.org/wiki/{qid}"})
        label = thing["label"]
        desc = desc or thing.get("description", "")
        de = lang == "de"
        when = asof = ""
        person = False
        v0 = values[0]
        if rel.kind == "age" and v0.get("type") == "time":
            born, born_when = format_date(v0["value"], lang)
            b = _time_key(v0["value"].get("time"))
            if death is not None:
                end = _time_key(death["value"].get("time"))
                years = end[0] - b[0] - ((end[1], end[2]) < (b[1], b[2]))
                died, died_when = format_date(death["value"], lang)
                text = (f"{label} starb {died_when} im Alter von {years} Jahren." if de
                        else f"{label} died {died_when} at the age of {years}.")
                answer = f"{years}"
            else:
                today = dt.date.today()
                years = today.year - b[0] - ((today.month, today.day) < (b[1], b[2]))
                text = (f"{label} ist {years} Jahre alt (geboren {born_when})." if de
                        else f"{label} is {years} years old (born {born_when}).")
                answer = f"{years}"
            return Fact(text, answer, rel.kind, label, thing["url"], f"{label} – {rel.name_de if de else rel.name_en}: "
                        f"{born}", person=False, qid=qid, desc=desc)
        if v0.get("type") == "time":
            answer, when = format_date(v0["value"], lang)
        elif v0.get("type") == "quantity":
            unit_names = {u: names.get(u, {}).get("label", "") for u in units}
            answer = format_quantity(v0["value"], lang, unit_names)
            point = _qualifier(chosen[0], "P585")
            if isinstance(point, dict) and _time_key(point.get("time"))[0] > 0:
                year = _time_key(point.get("time"))[0]
                asof = f" (Stand {year})" if de else f" (as of {year})"
        elif items:
            if any(i not in names for i in items):
                return None                          # a value without a name (or Wikidata did not answer)
            answer = _join([_NATIONAL_TEAM.sub("", names[i]["label"]) if rel.key == "winner" else names[i]["label"]
                            for i in items], lang)
            person = rel.kind == "item" and rel.key in ("head_state", "head_gov", "ceo", "coach", "founder", "author",
                                                         "director", "composer", "painter", "architect", "inventor",
                                                         "spouse")
        elif v0.get("type") in ("string", "monolingualtext"):
            val = v0["value"]
            answer = val.get("text") if isinstance(val, dict) else str(val)
        else:
            return None
        if not answer:
            return None
        if rel.key == "located" and prop == "P131" and len(items) == 1:
            # "Zugspitze" → "Grainau, Germany": the place and its country, when the place is not the country
            country = self._country(qid, explicit, lang, exclude=items[0])
            if country:
                answer = f"{answer}, {country}"
        text = self._sentence(question, asked, lang, label, answer, when, asof, prop)
        typed = asked.subject
        if pinned and typed and label.lower() != typed.lower() and typed.lower() in label.lower():
            # a thing the conversation picked ("Barcelona" after Real Madrid): say which ("FC Barcelona")
            text = re.sub(rf"\b{re.escape(typed)}\b", label, text, count=1, flags=re.I)
        evidence = f"{label} – {rel.name_de if de else rel.name_en}: {answer}{asof}"
        return Fact(text, answer, rel.kind, label, thing["url"], evidence, person=person, qid=qid, desc=desc,
                    values=tuple(items))

    def _country(self, qid: str, explicit: bool, lang: str, exclude: str) -> str:
        d = self._wikidata(explicit, action="wbgetclaims", entity=qid, property="P17")
        chosen = choose(((d or {}).get("claims") or {}).get("P17") or [], True, False)
        if not chosen:
            return ""
        cid = chosen[0]["mainsnak"]["datavalue"]["value"]["id"]
        if cid == exclude:
            return ""
        return self.labels([cid], lang, explicit).get(cid, {}).get("label", "")

    @staticmethod
    def _sentence(question: str, asked: Asked, lang: str, label: str, answer: str, when: str, asof: str,
                  prop: str) -> str:
        """The answer as a sentence: in English the question's own words turned into a statement
        ("Donald Trump is currently the president of the USA."), in German the common forms
        ("Der aktuelle Bundeskanzler ist Friedrich Merz."), else the relation's sentence."""
        rel = asked.rel
        value = answer
        if lang == "de":
            from engramm.chat.dialog import _head_de
            head = _head_de(question, _Short(answer, rel.kind))
            if head:
                return _recase(head, asked.subject, label)
        else:
            from engramm.chat.realize import answer_sentence
            head = answer_sentence(question, answer)
            if head and not asof:
                return _recase(head, asked.subject, label)
        en, de_ = _BY_PROP.get(prop, (None, None))
        template = (de_ if lang == "de" else en) or (rel.de if lang == "de" else rel.en)
        w = asked.word
        text = template.format(s=label, v=value, when=when, asof=asof, w=w.lower() if lang != "de" else w,
                               W=w[:1].upper() + w[1:])
        if lang == "de" and text.startswith(label):
            # the question's article: "Wer hat das Telefon erfunden?" → "Das Telefon wurde von … erfunden."
            m = re.search(rf"\b(der|die|das|den)\s+{re.escape(asked.subject)}\b", question, re.I)
            if m:
                text = f"{'der' if m.group(1).lower() == 'den' else m.group(1).lower()} {text}"
        return text[:1].upper() + text[1:]

    def summary(self, name: str, lang: str = "en", explicit: bool = False,
                pin: dict[str, str] | None = None) -> Fact | None:
        """What a thing is: the first sentences of its Wikipedia article (REST summary) — the article
        of that very title first, which is Wikipedia's main meaning ("DNA": the molecule; Wikidata's
        search ranked Little Mix's album first in CI), else the article of the first Wikidata hit."""
        host = f"{'de' if lang == 'de' else 'en'}.wikipedia.org"
        pinned = _pinned(name, pin)
        if pinned:                                      # the thing the conversation is about, not a namesake
            info = self.labels([pinned], lang, explicit).get(pinned)
            if not info or "wikipedia.org/wiki/" not in info["url"]:
                return None
            u = urllib.parse.urlsplit(info["url"])
            return self._summary_of(u.hostname, u.path.split("/wiki/", 1)[1], explicit, info["label"], info["url"],
                                    pinned, info.get("description", ""))
        typed = " ".join(name.split()).strip(" \"'“”„?!.")
        tries = [typed[:1].upper() + typed[1:]] if typed else []
        if typed.islower() and 1 < len(typed.split()) <= 4:
            tries.append(typed.title())                  # "elon musk" → "Elon Musk"
        for title in tries:
            fact = self._summary_of(host, urllib.parse.quote(title.replace(" ", "_")), explicit)
            if fact is not None:
                return fact
        hits = self.find(name, lang, explicit)
        if not hits:
            return None
        info = self.labels([hits[0]["id"]], lang, explicit).get(hits[0]["id"])
        if not info or "wikipedia.org/wiki/" not in info["url"]:
            return None
        u = urllib.parse.urlsplit(info["url"])
        return self._summary_of(u.hostname, u.path.split("/wiki/", 1)[1], explicit, info["label"], info["url"],
                                hits[0]["id"], str(hits[0].get("description") or info.get("description", "")))

    def _summary_of(self, host: str, title: str, explicit: bool, label: str | None = None,
                    url: str | None = None, qid: str = "", desc: str = "") -> Fact | None:
        """The first two sentences of one article (``title`` as in its URL); None for a missing page,
        a disambiguation page or an extract too short to say anything."""
        d = self._get(f"https://{host}/api/rest_v1/page/summary/{title}", host, "facts:wikipedia", explicit)
        if not d or d.get("type") == "disambiguation":
            return None
        extract = " ".join(str(d.get("extract") or "").split())
        if len(extract) < 40:
            return None
        text = _first_sentences(extract, 2, 420)
        page = ((d.get("content_urls") or {}).get("desktop") or {}).get("page") or f"https://{host}/wiki/{title}"
        return Fact(text, "", "summary", label or str(d.get("title") or urllib.parse.unquote(title).replace("_", " ")),
                    url or page, text, qid=qid or str(d.get("wikibase_item") or ""),
                    desc=desc or str(d.get("description") or ""))

    def article(self, question: str, lang: str = "en", explicit: bool = False) -> list[dict]:
        """The Wikipedia article that matches the question's keywords best, as a page to read:
        [{"t", "x", "url", "host", "rank"}] (one, or none)."""
        from engramm.web.search import content_words
        words = content_words(question)
        if not words.strip():
            return []
        host = f"{'de' if lang == 'de' else 'en'}.wikipedia.org"
        api = f"https://{host}/w/api.php?"
        d = self._get(api + urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": words[:200],
                                                    "srlimit": 2, "srprop": "", "format": "json"}),
                      host, "facts:wikipedia", explicit)
        titles = [h.get("title") for h in ((d or {}).get("query") or {}).get("search") or [] if h.get("title")]
        if not titles:
            return []
        d = self._get(api + urllib.parse.urlencode({"action": "query", "prop": "extracts", "explaintext": 1,
                                                    "exsectionformat": "plain", "redirects": 1, "titles": titles[0],
                                                    "format": "json"}),
                      host, "facts:wikipedia", explicit)
        pages = list((((d or {}).get("query") or {}).get("pages") or {}).values())
        text = str((pages[0] if pages else {}).get("extract") or "")
        if len(text) < 200:
            return []
        title = str(pages[0].get("title") or titles[0])
        url = f"https://{host}/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        return [{"t": f"{title} - Wikipedia", "x": text[:ARTICLE_CHARS], "url": url, "host": host, "rank": 0}]


@dataclass
class _Short:
    text: str
    kind: str


def _first_sentences(text: str, n: int, limit: int) -> str:
    from engramm.web.clean import split_sentences
    parts = split_sentences(text)
    out = ""
    for p in parts[:n]:
        if out and len(out) + len(p) + 1 > limit:
            break
        out = f"{out} {p}".strip()
    return out or text[:limit]
