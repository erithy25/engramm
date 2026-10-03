"""German conversation, v0 (Chat v3, phase 9).

ENGRAMM's reading and fact bank are English, so in German it chats, listens, remembers and
answers crises, and says honestly that knowledge questions work in English for now. The texts
are in ``data/conv/de.yaml`` (compiled into the conversation bank under ``de``).

* ``is_german``: counts German and English function words; German needs at least one clearly German
  word (not "was", "die", "also" …) and more German than English hits;
* ``understand``: safety first, then memory statements ("Ich heiße Anna" → "My name is Anna."
  for the shared memory), questions about the user's name, small talk, feelings, arithmetic;
* everything else gets the honest fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-zäöüß]+")
_END = re.compile(r"[\s.!?…,;:]+$")


def normalise_de(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[’‘`´']", " ", s)
    s = re.sub(r"(^|[\s,])(engramm|bot)([\s,!.?]|$)", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,")
    return _END.sub("", s).strip(" ,")


def is_german(text: str, spec: dict) -> bool:
    words = _WORD.findall(text.lower())
    if not words:
        return False
    de, en = set(spec["detect"]["german"]), set(spec["detect"]["english"])
    ambiguous = set(spec["detect"].get("ambiguous", []))
    strict = sum(w in de and w not in ambiguous for w in words)
    if strict == 0 and not re.search(r"[äöüß]", text.lower()):
        return False                      # "When was he born?": no clearly German word
    n_de = sum(w in de for w in words)
    n_en = sum(w in en and w not in de for w in words)
    return n_de > n_en or (n_de == n_en and bool(re.search(r"[äöüß]", text.lower())))


# memory statements → the English sentence the shared memory understands
_STATEMENTS = [
    (re.compile(r"^(?:ich heiße|ich heisse|mein name ist|man nennt mich|nenn mich) ([a-zäöüß][\w\-äöüß]*(?: [a-zäöüß][\w\-äöüß]*)?)$"),
     "name", "My name is {0}."),
    (re.compile(r"^ich wohne (?:jetzt |mittlerweile |inzwischen |seit kurzem |neuerdings )?in ([\w\-äöüß ]{2,40})$"), "fact", "I live in {0}."),
    (re.compile(r"^ich lebe (?:jetzt |mittlerweile |inzwischen |seit kurzem )?in ([\w\-äöüß ]{2,40})$"), "fact", "I live in {0}."),
    (re.compile(r"^ich komme aus ([\w\-äöüß ]{2,40})$"), "fact", "I am from {0}."),
    (re.compile(r"^ich bin (\d{1,3}) jahre alt$"), "fact", "I am {0} years old."),
    (re.compile(r"^ich bin (\d{1,3})$"), "fact", "I am {0} years old."),
    (re.compile(r"^ich arbeite als ([\w\-äöüß ]{2,40})$"), "fact", "I work as {0}."),
    (re.compile(r"^ich bin (?:ein |eine |von beruf |beruflich )?(designer(?:in)?|lehrer(?:in)?|arzt|ärztin|krankenpfleger(?:in)?|krankenschwester|"
                r"ingenieur(?:in)?|programmierer(?:in)?|entwickler(?:in)?|softwareentwickler(?:in)?|anwalt|anwältin|koch|köchin|"
                r"verkäufer(?:in)?|polizist(?:in)?|architekt(?:in)?|journalist(?:in)?|friseur(?:in)?|mechaniker(?:in)?|elektriker(?:in)?|"
                r"bäcker(?:in)?|buchhalter(?:in)?|berater(?:in)?|manager(?:in)?|pilot(?:in)?|apotheker(?:in)?|erzieher(?:in)?|"
                r"physiotherapeut(?:in)?|psychologe|psychologin|schauspieler(?:in)?|musiker(?:in)?|künstler(?:in)?|fotograf(?:in)?|"
                r"grafikdesigner(?:in)?|webdesigner(?:in)?|tischler(?:in)?|schreiner(?:in)?|maler(?:in)?|gärtner(?:in)?|"
                r"pfleger(?:in)?|altenpfleger(?:in)?|sozialarbeiter(?:in)?|übersetzer(?:in)?|steuerberater(?:in)?|zahnarzt|zahnärztin)$"),
     "fact", "I work as a {0}."),
    (re.compile(r"^mein lieblingsessen ist ([\w\-äöüß ]{2,40})$"), "fact", "My favourite food is {0}."),
    (re.compile(r"^meine lieblingsfarbe ist ([\w\-äöüß ]{2,40})$"), "fact", "My favourite colour is {0}."),
    (re.compile(r"^(?:also |ich glaube,? )?ich (?:mag|liebe|trage) (?:die farbe )?(?:am liebsten |total |sehr |echt )?"
                r"(blau|rot|grün|gelb|schwarz|weiß|lila|violett|rosa|pink|orange|grau|braun|türkis|beige|gold|silber)"
                r"(?: am liebsten| total| sehr| gern| gerne)?$"), "fact", "My favourite colour is {0}."),
    (re.compile(r"^(?:also |ich glaube,? )?(?:ich esse (?:am liebsten|total gern|sehr gern|gern|gerne)|mein lieblingsgericht ist) "
                r"([\w\-äöüß ]{2,30}?)(?: am liebsten)?$"), "fact", "My favourite food is {0}."),
    (re.compile(r"^(?:also |ehrlich gesagt )?ich (?:mag|liebe) (?!(?:kein\w*|nicht|dich|euch|es|das|den|die|ihn|sie|ihm|ihr|"
                r"dein|mich|so|gar|überhaupt|eigentlich|lieber|auch)\b)([a-zäöüß][\w\-äöüß]*(?: [a-zäöüß][\w\-äöüß]*)?)"
                r"(?: sehr| total| echt| so| gern| gerne)?$"), "fact", "I like {0}."),
]
_SHOWN_DE = {"name": "du heißt {0}", "I live in {0}.": "du wohnst in {0}", "I am from {0}.": "du kommst aus {0}",
             "I am {0} years old.": "du bist {0}", "I work as {0}.": "du arbeitest als {0}", "I work as a {0}.": "du bist {0}",
             "My favourite food is {0}.": "dein Lieblingsessen ist {0}", "My favourite colour is {0}.": "deine Lieblingsfarbe ist {0}",
             "I like {0}.": "du magst {0}"}


def statement_de(s: str) -> tuple[str, str, str, str] | None:
    """(kind, value, English sentence, German confirmation) for a German statement about you."""
    for rx, what, english in _STATEMENTS:
        m = rx.match(s.strip())
        if m:
            value = _title(m.group(1)) if what in ("name", "fact") and not m.group(1).isdigit() else m.group(1)
            shown = _SHOWN_DE.get("name" if what == "name" else english, "{0}").format(value)
            return what, value, english.format(value), shown
    return None


_ASK_NAME = re.compile(r"^(wie heiße ich|wie heisse ich|weißt du (noch )?(wie ich heiße|meinen namen)|"
                       r"kennst du meinen namen|wer bin ich|was ist mein name)$")
_CALC = re.compile(r"^(?:was (?:ist|ergibt|sind)|wie ?viel (?:ist|sind|ergibt)|rechne|berechne)\s+(.+)$")
_DE_OPS = [(r"\bmal\b", "*"), (r"\bplus\b", "+"), (r"\bminus\b", "-"), (r"\bgeteilt durch\b", "/"),
           (r"\bdurch\b", "/"), (r"(\d),(\d)", r"\1.\2")]


def _title(words: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in words.split())


@dataclass
class Understood:
    kind: str                          # safety | remember | ask_name | intent | feeling | calc | fallback
    data: dict = field(default_factory=dict)


def understand(text: str, spec: dict) -> Understood:
    s = normalise_de(text)
    for kind in ("crisis", "refuse"):
        for r in spec["safety"].get(kind, []):
            if any(re.search(t, s) for t in r["triggers"]):
                return Understood("safety", {"rule": r["id"], "response": r["response"]})
    for rx, what, english in _STATEMENTS:
        m = rx.match(s)
        if m:
            value = _title(m.group(1)) if what in ("name", "fact") and not m.group(1).isdigit() else m.group(1)
            return Understood("remember", {"what": what, "value": value, "english": english.format(value)})
    if _ASK_NAME.match(s):
        return Understood("ask_name")
    m = _CALC.match(re.sub(r"^(?:und|also|ok|okay) ", "", s))
    if m:
        expr = m.group(1)
        for pat, rep in _DE_OPS:
            expr = re.sub(pat, rep, expr)
        if re.fullmatch(r"[\d\s.+\-*/()^%]+", expr) and re.search(r"\d", expr):
            return Understood("calc", {"expr": expr.strip()})
    # "hallo, wie geht es dir": the greeting and the question are one message; the question counts
    rest = re.sub(r"^(?:hallo|hi|hey|moin|servus|na|guten (?:morgen|tag|abend))\b[ ,!.]*", "", s).strip()
    # "cool, tschüss" / "ok danke, bis dann": a short reaction before the real message
    rest = re.sub(r"^(?:(?:cool|super|ok|okay|alles klar|gut|prima|toll|nice|perfekt|na dann|ja|alright)\b[ ,!.]*)+(?=\S)", "", rest).strip() or rest
    for form in ([rest, s] if rest and rest != s else [s]):
        for it in spec["intents"]:
            for p in it["patterns"]:
                if re.fullmatch(p, form):
                    return Understood("intent", {"id": it["id"]})
    fe = spec["feelings"]
    for c in fe["categories"]:
        for t in c["triggers"]:
            m = re.search(t, s)
            if m:
                before = s[:m.start()].rstrip().split(" ")[-3:]
                neg = any(" ".join(before[i:]) in fe["negators"] for i in range(len(before)))
                return Understood("feeling", {"id": c["id"], "valence": c["valence"], "negated": neg})
    return Understood("fallback")


# ---------------------------------------------------------------------------
# German v1: everyday requests, moments and advice (Chat v3.1)
# ---------------------------------------------------------------------------

_REC_DE = [
    ("food", r"(?:was (?:soll|kann|könnte) ich (?:heute |heute abend |jetzt )?(?:essen|kochen)|was koche ich (?:heute|heute abend)|"
             r"was gibt es (?:heute )?zu essen|(?:essens|koch|rezept|abendessen)ideen?|ich weiß nicht,? was ich (?:essen|kochen) soll|"
             r"hast du (?:eine )?(?:idee|ideen) (?:fürs|für das) (?:abendessen|mittagessen|essen))"),
    ("book", r"(?:(?:kannst du mir |empfiehl mir |empfehl mir )?(?:ein|ein gutes) buch empfehlen|empfiehl mir ein buch|"
             r"buchempfehlungen?|was soll ich (?:als nächstes )?lesen|hast du (?:ein )?buchtipps?|"
             r"(?:vielleicht |dann |oder )?(?:ein buch|was zum lesen|lesen)[.,]? (?:was|welches) (?:empfiehlst du|würdest du (?:mir )?empfehlen)(?: mir)?|"
             r"was (?:empfiehlst du|würdest du empfehlen) (?:mir )?(?:für ein buch|an büchern|zum lesen)|welches buch (?:soll ich lesen|empfiehlst du(?: mir)?))"),
    ("movie", r"(?:(?:kannst du mir )?einen (?:guten )?film empfehlen|empfiehl mir einen film|filmempfehlungen?|"
              r"was soll ich (?:heute |heute abend |jetzt |nachher )?(?:gucken|schauen|anschauen|ansehen|sehen)|welchen film soll ich (?:gucken|schauen|sehen)|"
              r"(?:vielleicht |dann |oder )?(?:ein film|einen film)[.,]? (?:was|welchen) (?:empfiehlst du|würdest du (?:mir )?empfehlen)(?: mir)?|"
              r"was (?:empfiehlst du|würdest du empfehlen) (?:mir )?(?:für einen film|an filmen)|welchen film empfiehlst du(?: mir)?)"),
    ("series", r"(?:(?:kannst du mir )?eine (?:gute )?serie empfehlen|empfiehl mir eine serie|serienempfehlungen?|"
               r"welche serie soll ich (?:gucken|schauen|sehen))"),
    ("music", r"(?:(?:kannst du mir )?musik empfehlen|musikempfehlungen?|was soll ich (?:hören|anhören))"),
    ("podcast", r"(?:(?:kannst du mir |empfiehl mir )?(?:einen |ein paar )?(?:guten |gute )?podcasts? empfehlen|empfiehl mir (?:einen )?podcast|podcast-?(?:tipps?|empfehlungen?)|"
                r"welchen podcast (?:soll ich hören|empfiehlst du))"),
    ("game", r"(?:(?:kannst du mir )?ein (?:gutes )?spiel empfehlen|spielempfehlungen?|was soll ich spielen|"
             r"was können wir spielen)"),
    ("activity", r"(?:(?:mir ist (?:so |total )?langweilig,? )?was (?:kann|soll|könnte) ich (?:(?:heute|abend|jetzt|noch|nachher|später|"
                 r"gleich|am wochenende|denn|so)\s+)*(?:machen|tun|unternehmen)|was kann man (?:heute |am wochenende )?machen|ideen für (?:heute|das wochenende|"
                 r"den abend))"),
    ("gift", r"(?:geschenkideen?|was schenkt man (?:so|denn|da|zu weihnachten|zum geburtstag|jemandem)?(?: so)?|was kann man (?:so )?schenken|"
             r"was soll ich (?:meiner|meinem|meinen|einer|einem) [a-zäöüß]+ schenken|was schenke ich (?:meiner|meinem|meinen) [a-zäöüß]+(?: zum geburtstag| zu weihnachten)?|"
             r"was kann ich (?:meiner|meinem|meinen) [a-zäöüß]+ schenken)"),
    ("travel", r"(?:wohin soll ich (?:reisen|fahren|in den urlaub)|reiseziele?|urlaubsideen|reiseideen)"),
    ("hobby", r"(?:(?:ein )?neues hobby|hobbyideen|welches hobby soll ich anfangen)"),
    ("sleep", r"(?:ich kann nicht (?:ein)?schlafen|tipps zum (?:ein)?schlafen|wie schlafe ich besser|schlaftipps)"),
    ("study", r"(?:lerntipps|wie lerne ich (?:besser|effektiver)|tipps zum lernen)"),
    ("focus", r"(?:ich kann mich nicht konzentrieren|wie werde ich produktiver|ich prokrastiniere|konzentrationstipps)"),
    ("exercise", r"(?:sporttipps|sportideen|wie werde ich fit|wie bewege ich mich mehr)"),
    ("petname", r"(?:namen für (?:meinen|meine) (?:hund|katze|welpen|kater|hamster|hasen)|wie soll ich (?:meinen|meine) "
                r"(?:hund|katze|welpen|kater) nennen)"),
]
_REC_DE_RX = [(k, re.compile(rf"^(?:(?:hey|hi|hallo|na|sag mal|also),? )*{p}$")) for k, p in _REC_DE]
_ADVICE_DE = re.compile(r"^(?:(?:und|also|okay|ok|hm+),? )*(?:was soll ich (?:jetzt |da |bloß |nur )?(?:tun|machen)|"
                        r"was würdest du (?:an meiner stelle )?(?:tun|machen)|hast du (?:einen |ein paar )?(?:rat|tipp|tipps)"
                        r"(?: für mich)?|ich weiß nicht,? was ich (?:tun|machen) soll|was meinst du|was denkst du|"
                        r"was rätst du mir|wie gehe ich damit um|was kann ich (?:dagegen |da |jetzt |denn )?(?:tun|machen)|"
                        r"was hilft (?:dagegen|da)|hast du (?:eine )?idee(?:,? was ich tun kann)?|"
                        r"soll ich (?:was|etwas|das|es|ihm|ihr|ihnen) (?:was |etwas )?(?:sagen|ansprechen)|soll ich (?:mit )?(?:ihm|ihr|ihnen) reden|"
                        r"soll ich (?:das|es) ansprechen|ich weiß nicht,? ob ich (?:was|etwas) sagen soll|soll ich mich beschweren)$")
_NEG_DE = {"nervt": 2, "nervig": 2, "genervt": 2, "anstrengend": 2, "stressig": 2, "gestresst": 2, "schlimm": 2,
           "schrecklich": 3, "furchtbar": 3, "mies": 2, "blöd": 2, "doof": 2, "scheiße": 3, "beschissen": 3,
           "ätzend": 2, "langweilig": 1, "unfair": 2, "gemein": 2, "krank": 2, "kaputt": 2, "müde": 2,
           "erschöpft": 2, "traurig": 2, "wütend": 2, "sauer": 2, "enttäuscht": 2, "durchgefallen": 3,
           "verloren": 2, "verpasst": 1, "gestritten": 2, "angeschrien": 2, "angemeckert": 2, "ärger": 2,
           "streit": 2, "chaos": 2, "katastrophe": 3, "albtraum": 3, "überfordert": 3, "hasse": 2, "schlecht": 2,
           "gekündigt": 3, "entlassen": 3, "verlassen": 3, "abgelehnt": 3, "nervös": 2, "angst": 2, "fertig": 1}
_POS_DE = {"super": 2, "toll": 2, "großartig": 3, "genial": 3, "klasse": 2, "schön": 2, "wunderbar": 3,
           "fantastisch": 3, "geil": 2, "cool": 1, "befördert": 3, "bestanden": 3, "gewonnen": 3, "geschafft": 2,
           "glücklich": 2, "stolz": 3, "entspannt": 2, "lecker": 2, "verlobt": 3, "geheiratet": 3, "gefreut": 2,
           "spaß": 2, "perfekt": 2, "gut": 1}
_PHRASE_NEG_DE = re.compile(r"\b(?:lang|anstrengend|hart|stressig|blöd|mies|schlecht|schlimm|furchtbar)(?:er|en|e)?"
                            r" (?:tag|abend|morgen)|(?:lange|anstrengende|harte|stressige|blöde|miese|schlechte) woche|"
                            r"zu viel arbeit|nicht geschlafen|schlecht geschlafen|nichts geklappt|geht mir auf die nerven\b")
_PHRASE_POS_DE = re.compile(r"\b(?:toller|schöner|guter|super) (?:tag|abend|urlaub)|(?:tolle|schöne|gute) woche|"
                            r"gut gelaufen|neuen job|gute nachrichten\b")
_POSS_DE = {"mein": "dein", "meine": "deine", "meinem": "deinem", "meinen": "deinen", "meiner": "deiner"}
_PEOPLE_DE = frozenset("""chef chefin kollege kollegin kollegen mutter mama vater papa eltern bruder schwester freund
freundin freunde mann frau partner partnerin lehrer lehrerin nachbar nachbarin mitbewohner mitbewohnerin hund katze
sohn tochter kinder oma opa vermieter kunde kundin team""".split())
_EVENT_DE = re.compile(r"\b(prüfung|klausur|test|meeting|besprechung|präsentation|vorstellungsgespräch|termin|projekt|"
                       r"deadline|arzttermin|fahrprüfung)\b")
_PLACE_DE = re.compile(r"\b(?:bei der|auf der|in der) (arbeit|schule|uni|firma)\b")


def experience_de(s: str):
    """(valence, topic, person, timeword) for a German first-person moment, or None."""
    if s.endswith("?") or re.match(r"^(?:wer|was|wann|wo|warum|wieso|wie|welche[rs]?|kannst|hast|bist)\b", s):
        return None
    words = re.findall(r"[a-zäöüß]+", s)
    if not (set(words) & {"ich", "mir", "mich", "mein", "meine", "meinem", "meinen", "meiner", "wir", "uns"}) and \
            not re.search(r"\b(?:heute|gestern|arbeit|schule|uni)\b", s) and \
            not (_PHRASE_NEG_DE.search(s) or _PHRASE_POS_DE.search(s)):    # "war ein langer Tag": no "ich" needed
        return None
    stems = [_stem_de(w) for w in words]
    neg = sum(_NEG_DE.get(w, _NEG_DE.get(st_, 0)) for w, st_ in zip(words, stems))
    pos = sum(_POS_DE.get(w, _POS_DE.get(st_, 0)) for w, st_ in zip(words, stems))
    stemmed = " ".join(stems)
    neg += 2 if (_PHRASE_NEG_DE.search(s) or _PHRASE_NEG_DE.search(stemmed)) else 0
    pos += 2 if (_PHRASE_POS_DE.search(s) or _PHRASE_POS_DE.search(stemmed)) else 0
    if re.search(r"\bnicht (?:so |sehr |besonders )?(?:gut|toll|schön|super)\b", s):
        neg, pos = neg + 2, max(0, pos - 2)
    if max(neg, pos) < 2 or neg == pos:
        return None
    topic, person, timeword = None, False, None
    m = re.search(r"\b(mein|meine|meinem|meinen|meiner) ([a-zäöüß]+)", s)
    if m and m.group(2) not in ("leben", "name", "gott"):
        topic, person = f"{_POSS_DE[m.group(1)]} {m.group(2)[:1].upper() + m.group(2)[1:]}", m.group(2) in _PEOPLE_DE
        if person:                                        # "mit meinem freund gestritten": "Was hat dein Freund …", never "deinem Freund"
            noun = m.group(2)
            plural = noun in ("eltern", "kinder", "freunde", "freundinnen", "kollegen", "nachbarn", "geschwister", "großeltern", "schwiegereltern")
            fem = noun.endswith("in") or noun in ("mutter", "mama", "schwester", "frau", "oma", "tante", "tochter", "cousine", "nichte", "familie")
            art = "deine" if plural or fem else "dein"
            topic = f"{art} {noun[:1].upper() + noun[1:]}"
    elif _PLACE_DE.search(s):
        topic = "die " + _PLACE_DE.search(s).group(1)[:1].upper() + _PLACE_DE.search(s).group(1)[1:]
    elif _EVENT_DE.search(s):
        w = _EVENT_DE.search(s).group(1)
        art = "das" if w in ("meeting", "projekt", "vorstellungsgespräch") else "der" if w in ("test", "termin", "arzttermin") else "die"
        topic = f"{art} {w[:1].upper() + w[1:]}"
    elif re.search(r"\b(?:tag|woche|abend|morgen)\b", s):
        timeword = re.search(r"\b(tag|woche|abend|morgen)\b", s).group(1)
    return ("negative" if neg > pos else "positive"), topic, person, timeword


def _stem_de(w: str) -> str:
    """"anstrengenden" → "anstrengend", "stressigen" → "stressig": the common adjective endings."""
    for end in ("sten", "ster", "stes", "en", "er", "es", "em", "e"):
        if len(w) > len(end) + 4 and w.endswith(end):
            return w[: -len(end)]
    return w


def rec_kind_de(s: str) -> str | None:
    for kind, rx in _REC_DE_RX:
        if rx.match(s):
            return kind
    return None


def advice_de(s: str) -> bool:
    return bool(_ADVICE_DE.match(s))


_NEUTRAL = {
    "laugh": re.compile(r"^(?:ha(?:ha)+h?|hihi+|hehe+|lo+l+|xd+|lmao|😂+|🤣+|😄+|:d+)(?:,? (?:ok(?:ay)?|gut|klar|stimmt|ja|na gut|alles klar|fair))?$"),
    "ack": re.compile(r"^(?:ok(?:ay)?|okey|alles klar|verstehe|ach so|aha|achso|gut|na gut|klar|stimmt|genau|hm+|mhm)$"),
    "yes": re.compile(r"^(?:ja+|jo|jap|jep|jawohl|gerne|gern|klar doch|auf jeden fall|sicher|natürlich)$"),
    "no": re.compile(r"^(?:nein|nee+|ne|nö|nope|lieber nicht|nicht wirklich|auf keinen fall)$"),
    "positive": re.compile(r"^(?:cool|super|toll|nice|krass|wow|geil|stark|klasse|spitze|top)$"),
}


def neutral_de(s: str) -> str | None:
    """'laugh' / 'ack' / 'yes' / 'no' / 'positive' for short replies, so a German conversation stays German."""
    for kind, rx in _NEUTRAL.items():
        if rx.match(s):
            return kind
    return None
