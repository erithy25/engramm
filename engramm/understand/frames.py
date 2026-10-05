"""Situation frames: what happened, to whom, with what — read from one chat message (English or German).

The frame is general: it is built from the situation lexicon (engramm/understand/lex.py: WordNet classes, FrameNet
evidence) and a handful of syntactic patterns (possessives, copula + state word, "doesn't work", questions), never
from a list of conversation topics. A message about a cracked tablet screen, a burst pipe or a bitten finger gets a
frame although no line of code names tablets, pipes or fingers.

    Frame.kind    DAMAGE INJURY ILLNESS LOSS THEFT CONFLICT FAILURE MONEY DELAY WORRY SUCCESS MILESTONE ACQUIRE
                  DEATH FEEL_NEG FEEL_POS PLAN ACTIVITY or "" (no situation)
    Frame.who     me / child / partner / relative / friend / pet / colleague / other   (whom it happened to)
    Frame.obj     the main thing (lemma), Frame.obj_cats its categories, Frame.body a body part
    Frame.cause   an animal or person that caused it ("a wasp stung me")
    Frame.ask     what a question asks: what_do / how / should / is_bad / when / why / can / yesno / opinion

The frame classifier is rule-scored here; engramm/learn/ adjusts its weights from the user's corrections.
"""
from __future__ import annotations

from engramm.understand import _re as re
from dataclasses import dataclass, field

from engramm.understand.lex import Entry, lexicon

# ---- function words (never looked up in the lexicon) ------------------------------------------------------------
_STOP_EN = set("""a an the this that these those my your his her its our their me i we you he she it they them us him
some any no not never very really so too just also only even still yet again already of in on at to for from with by
about into onto over under out up down off and or but if because when while as than then there here what which who whom
whose where why how is am are was were be been being do does did have has had will would shall should can could may
might must ok okay oh hey hi hello yeah yes well um uh lol haha omg pls please like got get gets getting
one two three four five six seven eight nine ten twenty hundred half few several""".split())
_STOP_DE = set("""der die das den dem des ein eine einen einem einer eines mein meine meinen meinem meiner meines dein
deine deinen deinem deiner sein seine seinen seinem seiner ihr ihre ihren ihrem ihrer unser unsere unseren ich du er sie
es wir ihr mich mir dich dir uns euch ihn ihm ihnen man nicht nie kein keine keinen sehr so zu auch nur noch schon
wieder gerade eben mal halt doch ja nein und oder aber wenn weil als dass ob dann da hier was wer wen wem wie wo warum
wann welche welcher welches ist bin bist sind war waren sein habe hab hast hat haben hatte hatten wird werde werden
würde kann kannst können konnte soll sollte sollen muss musst müssen darf will willst wollen von vom zum zur im am an
auf aus bei mit nach seit über unter vor durch für gegen ohne um bis ok okay hey hi hallo na also echt total voll
ganz einfach jetzt heute gestern morgen eins zwei drei vier fünf sechs sieben acht neun zehn zwanzig hundert halb
paar""".split())

_PERSON_EN = {
    "child": "son daughter kid kids child children baby toddler boy girl little one",
    "partner": "wife husband girlfriend boyfriend partner fiance fiancee spouse",
    "relative": "mom mum mother dad father parents brother sister grandma grandpa grandmother grandfather aunt uncle "
                "cousin niece nephew family",
    "friend": "friend friends bestie mate buddy roommate flatmate housemate neighbour neighbor",
    "colleague": "boss colleague coworker co-worker manager teacher landlord client customer",
    "pet": "dog cat puppy kitten pet rabbit hamster bird horse",
}
_PERSON_DE = {
    "child": "sohn tochter kind kinder baby kleiner kleine junge mädchen",
    "partner": "frau mann freundin freund partner partnerin verlobter verlobte",
    "relative": "mama mutter papa vater eltern bruder schwester oma opa großmutter großvater tante onkel cousin cousine "
                "nichte neffe familie",
    "friend": "kumpel mitbewohner mitbewohnerin nachbar nachbarin bekannte bekannter",
    "colleague": "chef chefin kollege kollegin vorgesetzter lehrer lehrerin vermieter vermieterin kunde kundin",
    "pet": "hund katze welpe kätzchen haustier hase hamster vogel pferd",
}
_PRON_EN = {"son": "he", "boy": "he", "husband": "he", "boyfriend": "he", "dad": "he", "father": "he", "brother": "he",
            "grandpa": "he", "grandfather": "he", "uncle": "he", "nephew": "he", "fiance": "he", "boss": "they",
            "daughter": "she", "girl": "she", "wife": "she", "girlfriend": "she", "mom": "she", "mum": "she",
            "mother": "she", "sister": "she", "grandma": "she", "grandmother": "she", "aunt": "she", "niece": "she",
            "fiancee": "she"}
_PRON_DE = {"sohn": "er", "junge": "er", "mann": "er", "freund": "er", "papa": "er", "vater": "er", "bruder": "er",
            "opa": "er", "großvater": "er", "onkel": "er", "neffe": "er", "kleiner": "er", "kumpel": "er",
            "chef": "er", "kollege": "er", "nachbar": "er", "vermieter": "er", "hund": "er", "welpe": "er",
            "tochter": "sie", "mädchen": "sie", "frau": "sie", "freundin": "sie", "mama": "sie", "mutter": "sie",
            "schwester": "sie", "oma": "sie", "großmutter": "sie", "tante": "sie", "nichte": "sie", "kleine": "sie",
            "chefin": "sie", "kollegin": "sie", "nachbarin": "sie", "katze": "sie"}

# general state words and patterns (no topics): broken things, bodies, feelings
_BROKEN_EN = re.compile(r"\b(?:does not|doesn't|do not|won't|will not|wont|isn't|is not|can't|cannot|can not) "
                        r"(?:work|start|turn on|switch on|charge|load|open|close|connect|boot|flush|drain|lock|print)\b|"
                        r"\bstopped working\b|\bkeeps? (?:crashing|freezing|breaking|dying|leaking|beeping)\b|"
                        r"\b(?:is|was|went|got) (?:dead|flat|stuck|frozen|broken|busted|cracked|smashed|soaked|wet)\b|"
                        r"\bacting up\b|\bplaying up\b|\bmaking (?:a |an |this |weird |strange |loud |horrible |funny |)(?:\w+ )?(?:noises?|"
                        r"sounds?)\b|\bout of order\b|\b(?:does not|doesn't|won't|will not) \w+ any ?more\b|\bstopped \w+ing\b|"
                        r"\bisn't \w+ing (?:properly|right|anymore)\b")
_BROKEN_DE = re.compile(r"\b(?:geht|funktioniert|läuft|springt|startet|lädt|öffnet|schließt) (?:\w+ )?(?:nicht|nicht mehr|"
                        r"gar nicht)\b|\bkaputt\w*\b|\bspinnt\b|\bstreikt\b|\bhängt sich auf\b|\b(?:ist|sind) "
                        r"(?:platt|leer|nass|gesprungen|gerissen|verstopft|undicht|defekt)\b|\bmacht (?:komische )?"
                        r"geräusche\b|\b\w+t nicht mehr\b|\bmacht (?:komische|laute|seltsame) geräusche\b")
_DAMAGE_ADJ = {"broken", "cracked", "damaged", "smashed", "shattered", "dented", "scratched", "ruined", "busted", "torn",
               "ripped", "wrecked", "faulty", "flat", "dead", "stuck", "frozen", "soaked", "burst", "leaking", "blocked",
               "clogged", "kaputt", "gesprungen", "gerissen", "verstopft", "defekt", "undicht", "platt", "nass"}
_URGENT = re.compile(r"\b(?:can't|cannot|can not) breathe\b|\bunconscious\b|\bnot breathing\b|\bchest pain\b|"
                     r"\bwon't stop bleeding\b|\bbleeding (?:a lot|heavily|badly)\b|\bseizure\b|\boverdos\w*\b|"
                     r"\bthroat (?:is )?(?:closing|swelling)\b|\bon fire\b|\bhouse is burning\b|\bsmell gas\b|"
                     r"\bkeine luft\b|\bbewusstlos\b|\batmet nicht\b|\bbrustschmerz\w*\b|\bblutet (?:stark|sehr)\b|"
                     r"\bkrampfanfall\b|\bbrennt\b.*\b(?:wohnung|haus|küche)\b|\briecht nach gas\b")
_FUTURE_EN = re.compile(r"\b(?:tomorrow|tonight|next (?:week|month|year|monday|tuesday|wednesday|thursday|friday|"
                        r"saturday|sunday|weekend)|later today|this (?:weekend|evening|afternoon)|in (?:a|two|three|"
                        r"\d+) (?:days?|weeks?|months?)|soon)\b|\b(?:going to|gonna|will|'ll|about to|planning to|"
                        r"plan to|want to|thinking (?:of|about))\b")
_FUTURE_DE = re.compile(r"\b(?:morgen|übermorgen|heute abend|nächste[nrs]? (?:woche|monat|jahr|wochenende)|bald|"
                        r"am (?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|wochenende)|in (?:einer|"
                        r"zwei|drei|\d+) (?:tagen?|wochen?|monaten?))\b|\b(?:werde|wird|will|möchte|plane|vorhabe)\b")
_ASK_EN = [
    ("what_do", r"(?:so |and |ok |okay |but )?(?:what (?:should|can|do|could|would) (?:i|we) do|what now|now what|"
                r"what do you (?:suggest|recommend|think i should do)|any (?:tips|advice|ideas)|(?:can|could) you help|"
                r"help(?: me)?|what are my options|how do i (?:fix|handle|deal with|get rid of|stop) (?:it|this|that))\b"),
    ("is_bad", r"(?:is|was) (?:it|that|this) (?:bad|serious|dangerous|normal|okay|ok|a problem|worth it|too late|"
               r"weird|rude|wrong|fine)\b|should i (?:be )?worr(?:y|ied)\b"),
    ("should", r"(?:so |and |but )?should (?:i|we)\b|do you think (?:i|we) should\b|would you\b"),
    ("how", r"(?:so |and |but )?how (?:do|can|should|could) (?:i|we|you)\b|how to\b"),
    ("when", r"(?:so |and )?(?:when|how long|how soon|how often)\b"),
    ("why", r"(?:so |and |but )?why\b"),
    ("can", r"(?:so |and |but )?(?:can|could|may) (?:i|we)\b"),
    ("opinion", r"what do you think\b|what's your opinion|how do you feel about\b|do you like\b"),
]
_ASK_DE = [
    ("what_do", r"(?:und |also |ok |okay |aber )?(?:was (?:soll|kann|muss|könnte|sollte) ich (?:jetzt |denn |da )?"
                r"(?:tun|machen)|was (?:mach|mache|tu|tue) ich (?:jetzt|da|nun)|und jetzt|was nun|hast du (?:ein paar )?"
                r"(?:tipps|ideen|rat)|(?:tipps|ideen)|kannst du mir helfen|hilfe)\b"),
    ("is_bad", r"(?:ist|war) (?:das|es) (?:schlimm|gefährlich|normal|okay|ok|ein problem|zu spät|unhöflich|falsch)\b|"
               r"muss ich mir sorgen machen\b"),
    ("should", r"(?:und |also |aber )?soll(?:te)? ich\b|würdest du\b"),
    ("how", r"(?:und |also |aber )?wie (?:kann|soll|mach|mache|krieg|bekomm)\w* ich\b"),
    ("when", r"(?:und |also )?(?:wann|wie lange|wie schnell|wie oft)\b"),
    ("why", r"(?:und |also |aber )?warum\b|wieso\b|weshalb\b"),
    ("can", r"(?:und |also |aber )?(?:kann|darf) ich\b"),
    ("opinion", r"was hältst du (?:von|davon)\b|was denkst du\b|wie findest du\b|magst du\b"),
]

_REL_END_EN = re.compile(r"\b(?:dumped|broke up|break up|breaking up|split up|divorc\w*|cheated on|cheating on|"
                         r"left me|ghost\w*|unfriended|blocked me|is mad at me|angry at me|not talking to me|"
                         r"stopped talking to me|fell out|falling out|had a (?:fight|row|argument)|argu\w+ with)\b")
_REL_END_DE = re.compile(r"\b(?:schluss gemacht|getrennt|trennung|scheidung|lassen uns scheiden|betrogen|fremdgegangen|"
                         r"verlassen|ghostet|geghostet|blockiert|ist sauer auf mich|redet nicht mehr mit mir|gestritten|"
                         r"streit (?:mit|gehabt)|zerstritten)\b")
_SILENT_EN = re.compile(r"\b(?:stopped|stop|not|isn't|is not|doesn't|does not|won't|hasn't|has not|never) "
                        r"(?:replying|responding|answering|texting|calling|talking|writing|messaging|reply|respond|answer|"
                        r"text|call|talk|write)\b|\bignor(?:es|ing|ed) me\b")
_SILENT_DE = re.compile(r"\b(?:antwortet|meldet sich|reagiert|schreibt|redet|ruft)\b.*\b(?:nicht mehr|nicht|gar nicht|"
                        r"nie)\b|\bignoriert mich\b")

_KIND_VALENCE = {"DAMAGE": -1, "INJURY": -1, "ILLNESS": -1, "LOSS": -1, "THEFT": -1, "CONFLICT": -1, "FAILURE": -1,
                 "MONEY": -1, "DELAY": -1, "WORRY": -1, "DEATH": -1, "FEEL_NEG": -1, "SUCCESS": 1, "MILESTONE": 1,
                 "ACQUIRE": 1, "FEEL_POS": 1, "PLAN": 0, "ACTIVITY": 0, "": 0}
_CONCRETE = {"DEVICE", "VEHICLE", "P-VEHICLE", "P-DEVICE", "BUILDPART", "P-BUILDING", "BUILDING", "FURNITURE",
             "P-FURNITURE", "CLOTHING", "P-CLOTHING", "CONTAINER", "TOOL", "DOCUMENT", "KEYTHING", "JEWELRY", "MONEY",
             "FOOD", "DRINK", "PLANT", "ARTIFACT"}


_LIGHT_EN = set("""do does did done doing make makes made making have has had having go goes went gone going come comes
came take takes took want wants wanted need needs needed know knows knew think thinks thought say says said tell told see
saw seen look looks looked let lets try tried keep kept put seem seems feel feels felt find found give gave thing things
stuff lot bit way time today yesterday tomorrow tonight morning night week day days year now right new old good bad great
nice little big much many more most one two three first last next other""".split())
_LIGHT_DE = set("""tun tue tust tut machen mache mach macht machst gemacht gehen geht ging gegangen kommen kommt kam
gekommen sagen sage sagt gesagt wissen weiß finden finde findet gefunden geben gibt gab gegeben sehen sieht gesehen lassen
lässt gelassen ding dinge sache sachen zeit tag tage woche jahr mal heute gestern morgen gut schlecht neu alt groß klein
viel viele mehr erst ersten letzte nächste andere""".split())
_SUBJ_EN = {"i", "we", "you", "he", "she", "they", "it", "has", "have", "had", "was", "were", "is", "are", "am", "got",
            "get", "been", "to", "will", "would", "can", "could", "just", "also", "accidentally", "finally", "who",
            "someone", "somebody", "nobody", "not", "never", "that", "which"}
_SUBJ_DE = {"ich", "wir", "du", "er", "sie", "es", "man", "hab", "habe", "hat", "haben", "bin", "ist", "sind", "war",
            "wurde", "wurden", "werde", "wird", "jemand", "niemand", "nicht", "nie", "gerade", "schon"}
_PARTICLES = {"up", "down", "out", "off", "away", "in", "on", "over", "back", "through", "apart"}
_POSS = {"my", "our", "your", "his", "her", "their", "mein", "meine", "meinen", "meinem", "meiner", "unser", "unsere",
         "unseren", "unserem", "dein", "deine", "deinen", "deinem", "sein", "seine", "seinen", "seinem", "ihr", "ihre",
         "ihren", "ihrem"}
_DETS = {"a", "an", "the", "this", "that", "some", "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
         "einem", "einer", "vom", "zum", "zur", "im", "am", "beim"}


def _role(w: str, prev: str, by: dict, lang: str, subj_before: set, prev_role: str) -> str:
    """N, V or A for one content word from its readings and the word before it."""
    if len(by) == 1:
        return {"n": "N", "v": "V", "a": "A"}[next(iter(by))]
    if prev in _POSS or prev in _DETS or prev_role == "A":
        return "N" if "n" in by else "A" if "a" in by else "V"
    if lang == "en":
        if prev in subj_before and "v" in by:
            return "V"
        if prev_role == "N" and "v" in by and re.search(r"[^s]s$", w):
            return "V"                              # "my tooth hurts", "the tap drips"
        if re.search(r"(?:ed|ing)$", w) and "v" in by:
            return "V" if not (prev in ("is", "was", "are", "were", "got", "get", "so", "very", "really", "feel",
                                        "feeling", "felt") and "a" in by) else "A"
        if prev in ("is", "am", "are", "was", "were", "so", "very", "really", "too", "totally", "completely", "feel",
                    "feeling", "felt", "look", "looks", "looked", "seem", "seems", "got", "get", "getting", "became",
                    "become", "pretty", "kinda", "quite", "super", "extremely") and "a" in by:
            return "A"
        return "N" if "n" in by else "V" if "v" in by else "A"
    if re.fullmatch(r"(?:\w*ge\w+(?:t|en)|\w+(?:iert|ert|elt))", w) and "v" in by:
        return "V"                                  # gekippt, aufgeschürft, repariert
    if prev in ("ist", "bin", "bist", "sind", "war", "so", "sehr", "total", "echt", "ganz", "voll") and "a" in by:
        return "A"
    if prev in subj_before and "v" in by:
        return "V"
    return "N" if "n" in by else "V" if "v" in by else "A"


@dataclass
class Frame:
    lang: str = "en"
    kind: str = ""
    valence: int = 0
    who: str = ""                 # me / child / partner / relative / friend / colleague / pet / other
    who_word: str = ""            # "son", "sohn"
    pron: str = ""                # he / she / they; er / sie
    obj: str = ""                 # lemma of the main thing
    obj_word: str = ""            # as written ("laptop", "handy")
    obj_det: str = ""             # the user's determiner before it ("my", "meinen")
    obj_cats: frozenset = field(default_factory=frozenset)
    who_raw: str | None = None    # the person/thing roles as read, before the defaults below (the classifier's view)
    obj_cats_raw: frozenset | None = None
    body: str = ""
    cause: str = ""
    pred: str = ""
    evidence: frozenset = field(default_factory=frozenset)
    future: bool = False
    urgent: bool = False
    negated: bool = False
    ask: str = ""                 # what a question asks, "" for statements
    rule_kind: str = ""           # the rules' decision (the classifier may overrule it)
    question: bool = False
    words: tuple = ()

    @property
    def problem(self) -> bool:
        return self.valence < 0 and bool(self.kind)

    def slots(self) -> set[str]:
        return {k for k in ("who", "obj", "body", "cause") if getattr(self, k)}


def _ask(text: str, lang: str) -> str:
    s = text.strip().lower()
    for name, rx in (_ASK_EN if lang == "en" else _ASK_DE):
        if re.match(rx, s) or (name in ("what_do", "is_bad", "opinion") and re.search(rx, s)):
            return name
    if "?" in text:
        return "yesno" if re.match(r"(?:is|are|was|do|does|did|can|could|will|would|ist|sind|war|hast|hat|kann|kannst|"
                                   r"wird|würde|gibt)\b", s) else "other"
    return ""


_PERSONAL = {"DAMAGE", "LOSS", "THEFT", "DELAY", "MONEY", "FAILURE", "ILLNESS", "INJURY", "WORRY", "SUCCESS",
             "MILESTONE", "ACQUIRE", "FEEL_POS", "FEEL_NEG", "CONFLICT", "DEATH"}
_BODILY = {"ILLNESS", "INJURY", "DEATH", "SUCCESS", "MILESTONE"}


def _settle_roles(f: Frame, words, tags, persons: dict, prons: dict, lang: str) -> None:
    """The roles as a listener fills them once the kind is known: whom it concerns (a person named without "my" —
    "Opa ist gestürzt" — for what happens to a body; otherwise the speaker, whose thing it is) and the whole a part
    belongs to, when the whole is said too ("the bumper of my car" → the car)."""
    f.who_raw, f.obj_cats_raw = f.who, f.obj_cats
    if not f.who and f.kind in _PERSONAL:
        named = next((w for w in words if w in persons), None)
        if named and f.kind in _BODILY:
            f.who, f.who_word = persons[named], named
            f.pron = prons.get(named, "they" if lang == "en" else "")
        elif not named or f.kind not in _BODILY:
            f.who = "me"
    parts = {"P-VEHICLE": "VEHICLE", "P-DEVICE": "DEVICE"}
    for pc, whole_c in parts.items():
        if pc in f.obj_cats and whole_c not in f.obj_cats:
            whole = next((e for _, e, _ in tags if e is not None and e.pos == "n" and whole_c in e.cats), None)
            if whole is not None:                  # only a whole that is said: "starter" alone may be sourdough
                f.obj, f.obj_word, f.obj_cats = whole.lemma, whole.lemma, frozenset(whole.cats)
            break


def parse(text: str, lang: str = "en", use_model: bool = True, extra: dict | None = None) -> Frame:
    """The situation frame of one message. Empty kind when nothing happened (a greeting, a bare question)."""
    from engramm.chat.facts import expand_contractions
    lx = lexicon(lang)
    raw = text.strip()
    s = expand_contractions(raw.lower()) if lang == "en" else raw.lower()
    s = s.replace("’", "'")
    words = re.findall(r"[a-zäöüß]+(?:-[a-zäöüß]+)?|\d+", s)
    f = Frame(lang=lang, words=tuple(words))
    f.ask = _ask(raw, lang)
    f.question = bool(f.ask) or raw.endswith("?")
    f.urgent = bool(_URGENT.search(s))
    f.future = bool((_FUTURE_EN if lang == "en" else _FUTURE_DE).search(s))
    f.negated = bool(re.search(r"\b(?:not|never|no longer|nobody|no one|nicht|nie|kein\w*|niemand)\b", s))
    stop = _STOP_EN if lang == "en" else _STOP_DE
    persons = {w: k for k, ws in (_PERSON_EN if lang == "en" else _PERSON_DE).items() for w in ws.split()}
    prons = _PRON_EN if lang == "en" else _PRON_DE
    first = re.search(r"\b(?:i|me|my|we|our|us|mine)\b" if lang == "en" else r"\b(?:ich|mir|mich|mein\w*|wir|uns|unser\w*)\b", s)

    # whom it happened to: "my son", "meine Tochter"; else the speaker
    poss = r"(?:my|our)" if lang == "en" else r"(?:mein|meine|meinen|meinem|meiner|unser|unsere|unseren|unserem)"
    for m in re.finditer(poss + r" (?:(?:little|best|older|younger|big|kleine[rn]?|beste[rn]?|große[rn]?|ältere[rn]?|"
                                r"jüngere[rn]?) )?([a-zäöüß-]+)", s):
        w = m.group(1)
        base = w[:-1] if lang == "en" and w.endswith("s") and w[:-1] in persons else w
        if base in persons:
            f.who, f.who_word = persons[base], base
            f.pron = prons.get(base, "they" if lang == "en" else "")
            break
    if not f.who and first:
        f.who = "me"

    # readings of the content words: a light tagger (determiner → noun, pronoun/aux → verb, -ed/-ing → verb)
    light = _LIGHT_EN if lang == "en" else _LIGHT_DE
    subj_before = _SUBJ_EN if lang == "en" else _SUBJ_DE
    tags: list[tuple[str, Entry | None, list[Entry]]] = []
    for i, w in enumerate(words):
        if w in stop or w.isdigit() or len(w) < 2 or w in light or w in persons:
            tags.append(("S", None, []))
            continue
        rs = lx.lookup(w)
        if not rs:
            tags.append(("?", None, []))
            continue
        by = {r.pos: r for r in reversed(rs)}
        prev = words[i - 1] if i else ""
        role = _role(w, prev, by, lang, subj_before, tags[-1][0] if tags else "")
        if role != "V" and "v" in by and (w in lx.forms and lang == "en" or prev in persons) and \
                not (prev in _POSS or prev in _DETS):
            role = "V"                              # "my son fell", "stung": an irregular past is a verb
        nxt2 = words[i + 2] if i + 2 < len(words) else ""
        if role == "V" and lang == "en" and i + 1 < len(words) and words[i + 1] in _PARTICLES and \
                not (nxt2 in _POSS or nxt2 in _DETS or (nxt2 and nxt2 not in stop)):
            ph = lx.get(f"{by['v'].lemma} {words[i + 1]}", "v")
            if ph is not None:
                rs = [ph] + rs                      # "threw up", "broke down", "passed away"
                by["v"] = ph
        tags.append((role, by.get({"N": "n", "V": "v", "A": "a"}[role]), rs))
    ev: set[str] = set()
    body_ev = False                               # bodily evidence from a noun, an adjective or a body verb
    best_obj: tuple[int, str, str, str, frozenset] | None = None
    pred_entry: Entry | None = None
    i = 0
    while i < len(words):
        role, e, rs = tags[i]
        if role in ("N", "A") and e is not None:
            j = i                                  # a noun phrase: modifiers + head (the last noun)
            while j + 1 < len(words) and tags[j + 1][0] in ("N", "A") and tags[j + 1][1] is not None:
                j += 1
            members = [(k, tags[k][2]) for k in range(i, j + 1)]
            head = next((k for k in range(j, i - 1, -1) if tags[k][0] == "N" and any(r.pos == "n" for r in tags[k][2])), None)
            prev = words[i - 1] if i else ""
            for k, readings in members:
                for r in readings:
                    if r.pos == "a" and (r.lemma in _DAMAGE_ADJ or words[k] in _DAMAGE_ADJ):
                        ev.add("HARM")
                    if r.pos == "a" and tags[k][0] == "A":
                        ev |= set(r.ev)
                        body_ev = body_ev or "BODY" in r.ev
            if head is not None:
                hn = next(r for r in tags[head][2] if r.pos == "n")
                group = [next((r for r in tags[k][2] if r.pos == "n"), None) for k, _ in members if tags[k][0] == "N"]
                group = [g for g in group if g is not None]
                if "BODYPART" in hn.cats and not hn.cats & {"LIQUID", "FOOD", "DRINK"} and not f.body:
                    f.body = words[head]
                elif hn.cats & {"INSECT", "ANIMAL"} and not hn.cats & {"PET"} and not f.cause:
                    f.cause = hn.lemma
                else:
                    pick = hn if hn.cats & (_CONCRETE | {"PET"}) else next(
                        (g for g in reversed(group) if g.cats & (_CONCRETE | {"PET"})), None)
                    if pick is not None:
                        score = 3 if prev in _POSS else 2 if prev in _DETS else 1
                        if best_obj is None or score > best_obj[0]:
                            if pick is hn:            # "washing machine", "car insurance": the noun compound, not just its head
                                k0 = head
                                while k0 - 1 >= i and tags[k0 - 1][0] == "N":
                                    k0 -= 1
                                wordx = " ".join(words[k0:head + 1])
                            else:
                                wordx = pick.lemma
                            best_obj = (score, pick.lemma, wordx, prev if (prev in _POSS or prev in _DETS) else "", pick.cats)
                    ev |= set(hn.ev)
                    body_ev = body_ev or ("BODY" in hn.ev and "ILLNESS" in hn.cats)
            i = j + 1
            continue
        if role == "V" and e is not None:
            v = rs[0] if rs and rs[0].pos == "v" and " " in rs[0].lemma else e
            vev = set(v.ev) or set(e.ev)
            if v.ss == "body":
                vev.add("BODY")
                body_ev = True
            if len(vev) > 4:                        # a verb of many senses: keep what fits the rest of the sentence
                vev &= {"HARM", "FLUID", "IMPACT", "LOSE", "THEFT", "BODY"} if best_obj or f.body else {"DEATH", "REL", "JOB", "WIN", "FAIL", "CONFLICT", "BODY"}
            if vev and (pred_entry is None or not pred_entry.ev):
                pred_entry = v
            ev |= vev
        i += 1
    if best_obj:
        _, f.obj, f.obj_word, f.obj_det, f.obj_cats = best_obj
    if pred_entry:
        f.pred = pred_entry.lemma
    if (_BROKEN_EN if lang == "en" else _BROKEN_DE).search(s):
        ev.add("BROKEN")
    if any(w in _DAMAGE_ADJ for w in words) and best_obj:
        ev.add("HARM")                            # "the pipe burst", "das Display ist gesprungen"
    if best_obj and best_obj[4] & {"DEVICE", "P-DEVICE", "FURNITURE", "CLOTHING", "DOCUMENT"} and any(
            r.pos == "n" and r.cats & {"LIQUID", "DRINK"} for _, _, rs in tags for r in rs[:1]):
        ev.add("FLUID")                           # coffee over the laptop, Saft aufs Sofa
    if (_REL_END_EN if lang == "en" else _REL_END_DE).search(s):
        ev.add("RELEND")
    if (_SILENT_EN if lang == "en" else _SILENT_DE).search(s) and f.who and f.who not in ("me", "pet"):
        ev.add("RELEND")
    # who moved: "my phone fell" (a thing) vs "my son fell" / "i fell" (a person)
    first_v = next((k for k, (r, e, _) in enumerate(tags) if r == "V" and e is not None and "IMPACT" in e.ev), None)
    if first_v is not None:
        before = words[:first_v]
        person_before = any(w in ("i", "we", "he", "she", "they", "ich", "wir", "er", "sie") or w in persons for w in before)
        thing_before = best_obj is not None and best_obj[2] in before
        if person_before and not (thing_before and before.index(best_obj[2]) > max(
                (before.index(w) for w in before if w in persons or w in ("i", "we", "he", "she", "they", "ich", "wir", "er", "sie")), default=-1)):
            ev.add("FALL")
    if body_ev:
        ev.add("BODYX")
    f.evidence = frozenset(ev)
    f.kind = f.rule_kind = _decide(f, s)
    if use_model:
        from engramm.understand.classify import classifier
        clf = classifier()
        if clf:
            f.kind = clf.predict(f, s, f.rule_kind, extra)   # the learned classifier has the last word
    _settle_roles(f, words, tags, persons, prons, lang)
    f.valence = _KIND_VALENCE.get(f.kind, 0)
    if f.kind in ("PLAN", "ACTIVITY", "") and ev & {"EMO"}:
        from engramm.chat.smart import experience
        e = experience(s) if lang == "en" else None
        if e:
            f.valence = -1 if e.valence == "negative" else 1
    return f


FACT = re.compile(r"(?:i|we) (?:work|live|study|stay|grew up|teach) (?:at|for|as|in|on)\b|(?:ich|wir) (?:arbeite|arbeiten|"
                  r"wohne|wohnen|studiere|lebe) (?:als|bei|in|an|im)\b|(?:i|ich) (?:love|like|hate|liebe|mag|hasse|"
                  r"esse kein\w*|am a|am an|bin ein\w*)\b|(?:my|mein\w*) (?:name|favou?rite|lieblings\w*) ")

_R = {k: re.compile(v) for k, v in {
    "birth": r"\b(?:pregnant|expecting (?:a baby|twins|our first|a child)|having a baby|schwanger|(?:bekommen|kriegen) "
             r"(?:ein|unser erstes|noch ein) (?:baby|kind)|nachwuchs)\b",
    "death": r"\b(?:died|passed away|passed on|has passed|dead|death|funeral|put (?:down|to sleep)|gestorben|verstorben|tot|"
             r"beerdigung|eingeschläfert|von uns gegangen)\b",
    "theft": r"\b(?:stole|stolen|steal\w*|robbed|robbery|burgl\w*|break-in|broke into|broken into|pickpocket\w*|mugged|"
             r"theft|thief|thieves|gestohlen|geklaut|klaut\w*|beklaut|eingebrochen|einbruch|ausgeraubt|dieb\w*|überfallen)\b",
    "conflict": r"\b(?:yell\w* at|shout\w* at|scream\w* at|insult\w*|was rude|so rude|criticiz\w*|criticis\w*|blamed me|"
                r"(?:fight|row|argument|arguing|argued) with|(?:had|having) (?:a|another|this) (?:huge |big )?(?:fight|row|argument)|"
                r"angeschrien|angebrüllt|beleidigt|angemeckert|gestritten|streit (?:mit|gehabt)|zoff)\b",
    "injury": r"\b(?:bitten|bit me|bit (?:him|her)|gebissen|stung|gestochen|scratched me|gekratzt|burn(?:ed|t) my|"
              r"verbrannt|verbrüht|cut (?:my|his|her|their)(?:self)?|geschnitten|sprain\w*|verstaucht|umgeknickt|"
              r"twisted (?:my|his|her)|broke (?:my|his|her|their) (?:arm|leg|wrist|ankle|finger|toe|nose|foot|hand|rib|"
              r"collarbone)|\w+ gebrochen|eingeklemmt|got hurt|verletzt|concussion|gehirnerschütterung)\b",
    "lossfind": r"\b(?:can not find|cannot find|could not find|can't find|lost|misplaced|left (?:my|it|them|our) \w*(?: \w+)? "
                r"(?:on|in|at)|forgot (?:my|it) \w* (?:on|in|at)|finde \w+(?: \w+)? nicht|nicht (?:mehr )?finden|verloren|"
                r"verlegt|liegen (?:ge)?lassen|vergessen (?:im|in der|am|beim|bei)|(?:im|in der|am|beim|bei) \w+ (?:vergessen|"
                r"liegen (?:ge)?lassen|liegenlassen)|ist weg|sind weg)\b",
    "exam": r"(?:exam|test|interview|audition|driving test|license|licence|course|prüfung|klausur|examen|führerschein|"
            r"vorstellungsgespräch|probezeit)",
    "pass": r"\b(?:passed|pass|aced|nailed|got through|made it|bestanden|geschafft)\b",
    "fail": r"\b(?:failed|fail|flunked|bombed|messed up|durchgefallen|vergeigt|verhauen|nicht bestanden|durch (?:die |den |das )?"
            r"\w+ gefallen)\b",
    "reject": r"\b(?:rejected|turned down|didn't get|did not get|wasn't accepted|was not accepted|got a rejection|absage|"
              r"abgelehnt|nicht bekommen|nicht genommen|nicht angenommen)\b",
    "fired": r"\b(?:fired|laid off|let go|sacked|lost my job|gekündigt|entlassen|rausgeworfen|rausgeschmissen)\b",
    "sportloss": r"\b(?:lost (?:the|our|my|a) (?:game|match|final|race|tournament|semi-?final)|(?:spiel|finale|match|turnier) "
                 r"verloren|verloren (?:im|das) (?:spiel|finale))\b",
    "delay": r"\b(?:late|delayed|delay|cancell?ed|stuck (?:at|in|on) (?:the )?(?:airport|station|traffic|motorway|highway|"
             r"train|platform|border)|missed (?:my|the|our) (?:bus|train|flight|plane|connection|appointment|ferry|"
             r"tram|ride)|stuck in traffic|traffic jam|verspätung|verspätet|ausgefallen|fällt aus|verpasst|stau|zu spät)\b",
    "money": r"\b(?:bill|bills|fine|fined|costs?|price|rent|debt|debts|afford|expensive|owe|overdraft|fees?|overdrawn|broke|"
             r"strafzettel|rechnung|miete|kosten|schulden|teuer|leisten|nachzahl\w*|gebühr\w*|mahnung|pleite|knapp bei kasse|"
             r"\w*rechnung|\w*nachzahlung|insurance|premium|went up|gone up|increase[ds]?|raised|erhöht|gestiegen|"
             r"doppelt so hoch|teurer|abzocke|ripped off)\b",
    "milestone": r"\b(?:engaged|got married|getting married|wedding|moved in together|graduat\w*|new job|got the job|got hired|"
                 r"start(?:ing|ed)? (?:a|my) new job|verlobt|geheiratet|hochzeit|zusammengezogen|abschluss|neuen job|neue "
                 r"(?:stelle|arbeit)|die stelle bekommen|den job bekommen|eingestellt|(?:bought|buying|bought our|got) "
                 r"(?:a|our|my|our first|my first) (?:house|home|flat|apartment)|first (?:apartment|flat|house|home|place)|"
                 r"keys to (?:my|our)|moved into|moving into|retir\w+|haus gekauft|wohnung gekauft|eigene wohnung|"
                 r"erste wohnung|eingezogen|rente|in rente)\b",
    "success": r"\b(?:got (?:picked|selected|chosen|accepted|shortlisted)|(?:was|were|been) (?:picked|selected|chosen|accepted)|wurden? (?:ausgewählt|angenommen|genommen)|won|win|winning|promoted|promotion|made it|got in|got accepted|was accepted|record|gewonnen|geschafft|"
               r"befördert|angenommen|bestanden|erster platz)\b",
    "acquire": r"\b(?:bought|got (?:a|an|my|me a|myself a) (?:new|brand)|gave me|received|got a new|got myself|geschenkt|"
               r"gekauft|neues|neuen|neue)\b",
    "feelpos": r"\b(?:good mood|great mood|so happy|really happy|so excited|feel(?:ing)? great|gute laune|richtig gut drauf|"
               r"super drauf|so glücklich|freu mich so)\b",
    "worry": r"\b(?:nervous|anxious|worried|worry|scared|afraid|terrified|dread\w*|panick\w*|nervös|ängstlich|angst|sorgen|"
             r"besorgt|bammel|panik|schiss)\b",
    "feelneg": r"\b(?:sad|lonely|bored|tired|exhausted|stressed|overwhelmed|depressed|down|upset|miserable|burnt out|"
               r"traurig|einsam|langweilig|gelangweilt|müde|erschöpft|gestresst|überfordert|niedergeschlagen|deprimiert|"
               r"kaputt|fertig|ausgelaugt|down)\b",
    "sick": r"\b(?:sick|ill|unwell|fever|cough\w*|flu|cold|headache|migraine|nause\w*|vomit\w*|throw\w* up|threw up|rash|"
            r"sore|pain|ache\w*|hurts?|dizzy|infection|diarrh\w*|allerg\w*|krank|fieber|husten|grippe|erkältet|erkältung|"
            r"\w*schmerz\w*|übel|kotz\w*|erbrech\w*|ausschlag|schwindel\w*|migräne|entzünd\w*|durchfall)\b",
}.items()}
# broader everyday wording per family (general vocabulary of each kind of situation, English and German)
_EXTRA = {
    "feelpos": r"\b(?:life is good|feel(?:ing)? (?:amazing|awesome|fantastic|wonderful|relaxed|content|motivated|loved|light|"
               r"free|blessed|grateful|great|good|happy|cheerful|calm|peaceful|alive|energi[sz]ed|confident)|best mood|"
               r"buzzing|good vibes|grateful|thankful|cheerful|content|chill day|loving (?:it|life)|on cloud nine|"
               r"over the moon|in a great place|so relaxed|glücklich|zufrieden|entspannt|dankbar|motiviert|beschwingt|"
               r"gut gelaunt|bester laune|happy|richtig gut|super gut|total gut|fühl mich (?:gut|super|toll|wohl|"
               r"großartig|frei|leicht|geliebt|stark)|läuft bei mir|herrlicher tag|wunderschöner tag)\b",
    "feelneg": r"\b(?:alone|lonely|empty|numb|homesick|grumpy|restless|unhappy|hopeless|worthless|meh|blah|gray day|grey day|"
               r"a bit much|too much|so done|done with everything|feel like crying|no energy|wiped out|drained|"
               r"burned out|burnt out|nothing feels|can't be bothered|in a funk|feeling low|feeling down|feel lost|"
               r"miss (?:having|my|them|him|her|home)|allein|leer|antriebslos|lustlos|schlecht drauf|mies drauf|"
               r"mies gelaunt|heimweh|frustriert|unruhig|unglücklich|hoffnungslos|keine energie|zum heulen|"
               r"möchte weinen|alles zu viel|keinen bock|null bock|ausgebrannt|vermisse)\b",
    "sick": r"\b(?:pounding|stuffy nose|runny nose|chills|aching|aches|hurts every|short of breath|pneumonia|covid|corona|"
            r"tested positive|caught (?:the|a|something)|bug going around|stomach bug|food poisoning|throat|temperature|"
            r"pink eye|itchy|swollen glands|cramps|period pain|bronchitis|sinus\w*|tonsil\w*|stomach ache|stomachache|"
            r"toothache|earache|backache|asthma|cold sore|hay ?fever|schnupfen|verschnupft|schüttelfrost|atemnot|"
            r"lungenentzündung|magen-darm|magendarm|lebensmittelvergiftung|halsweh|bauchweh|zahnweh|ohrenweh|"
            r"positiv getestet|angesteckt|kränkel\w*|erkältet|matschig|tut (?:mir )?(?:\w+ )?weh|brummschädel)\b",
    "milestone": r"\b(?:had (?:her|his|their|a|the) baby|became a (?:dad|mom|mum|father|mother|grandma|grandpa|grandparent)|"
                 r"becoming a (?:dad|mom|mum|father|mother|grandma|grandpa)|started school|first day (?:of|at) school|"
                 r"proposed|popped the question|she said yes|he said yes|first steps|maternity leave|paternity leave|"
                 r"adopted a (?:baby|child|son|daughter)|turned (?:18|21|30|40|50|60|70|80)|last day of school|"
                 r"finished (?:school|uni|university|my degree|my studies)|first job|moving in together|"
                 r"baby (?:is )?(?:born|here|arrived)|ist geboren|kam zur welt|baby bekommen|opa geworden|oma geworden|"
                 r"vater geworden|mutter geworden|papa geworden|mama geworden|eingeschult|einschulung|heiratsantrag|"
                 r"ja gesagt|erste schritte|elternzeit|mutterschutz|18 geworden|volljährig|abi (?:geschafft|bestanden)|"
                 r"abitur|ziehen zusammen|zusammenziehen|ersten job)\b",
    "acquire": r"\b(?:got (?:the|a|an|my|our|me|myself|some|new) \w+|finally got|treated myself|picked up a|knitted me|"
               r"made me a|brought me|surprised me with|got for (?:my )?(?:birthday|christmas)|for my birthday|"
               r"for christmas|adopted a (?:kitten|puppy|cat|dog|rabbit)|ordered a|arrived today|came today|tickets for|"
               r"won a (?:voucher|prize|trip|ticket)|bekommen|gekriegt|geschenkt bekommen|zum geburtstag|zu weihnachten|"
               r"gegönnt|ergattert|besorgt|bestellt und|ist angekommen|kam heute|adoptiert|abgeholt)\b",
    "success": r"\b(?:got an a|got a 1|top marks|full marks|\d+ ?(?:percent|%) on|got into|accepted at|got accepted|approved|"
               r"scholarship|praised|compliment\w*|bestseller|funded|funding round|hit my (?:\w+ )?goal|reached my goal|"
               r"finish line|personal best|pb|ran (?:my first |a )?(?:5k|10k|half|marathon)|without stopping|"
               r"bumped my salary|pay rise|raise|bonus|nailed (?:it|the)|aced|smashed it|crushed it|lost \d+ ?(?:kg|kilos?|"
               r"pounds?|lbs)|first place|1st place|gold medal|award|stipendium|zusage|angenommen worden|bewilligt|"
               r"genehmigt|gelobt|lob bekommen|bestnote|eine eins|note 1|1,0|gehaltserhöhung|beförder\w*|ziel erreicht|"
               r"durchgezogen|bestzeit|erster platz|gewonnen|abgenommen|geschafft)\b",
    "conflict": r"\b(?:bit my head off|ignor\w+ (?:me|my)|aren't talking|not talking|won't talk to me|slammed the door|"
                r"shouting match|screaming match|rude to me|humiliat\w*|took credit|confronted|called me \w+|hung up on me|"
                r"hung up|told everyone my secret|betray\w*|backstab\w*|reported me|aggressive|disrespect\w*|mocked me|"
                r"excluded me|without me|left me out|snapped at me|lashed out|falling out|fell out|beef with|not speaking|"
                r"angeschnauzt|angeblafft|ignoriert mich|ignorieren mich|reden nicht mehr|redet nicht mehr|tür geknallt|"
                r"angeschrien|bloßgestellt|lächerlich gemacht|verpetzt|angezeigt|verraten|ausgeschlossen|ohne mich|"
                r"aufgelegt|unverschämt|frech zu mir|respektlos|zickt|zoff|krach (?:mit|gehabt)|aneinandergeraten|"
                r"beleidigt|gemobbt|mobbing|lästern|lästert|nervt (?:mich|total|so|voll|echt|gerade)|nerven mich|"
                r"geht mir (?:\w+ )?auf die nerven|getting on my nerves|gets on my nerves|annoy(?:s|ing) me|so annoying|"
                r"drives me (?:crazy|nuts|mad))\b",
    "delay": r"\b(?:pushed back|postponed|rescheduled|overslept|didn't show up|never came|never showed|no-show|took forever|"
             r"had already left|already gone|roadworks|diverted|missed (?:my|the|our|a) \w+|waited (?:all day|for hours|\d+ hours?)|"
             r"moved (?:again|for the third time)|stuck in|running late|hold-up|queue|verschoben|verlegt|verschlafen|"
             r"nicht gekommen|kam nicht|kommt nicht|ewig gedauert|schon weg|abgefahren|baustelle|umleitung|"
             r"warte(?:n|t)? seit|stunden gewartet|im stau|steck\w* fest|feststecken)\b",
    "money": r"\b(?:ticket|speeding|maxed out|credit card|loan|loans|charged|charging|refund|owes me|owe me|borrow\w*|lend\w*|"
             r"thousands|hundreds|upfront|quoted|late fee|penalty|tax|taxes|bank account|overcharg\w*|"
             r"won't cover|not covered|out of pocket|savings|broke till|knöllchen|blitzer|geblitzt|kredit|kreditkarte|"
             r"darlehen|abgebucht|zweimal abgebucht|rückerstattung|schuldet mir|leihen|geliehen|tausende|vorkasse|"
             r"steuern|steuernachzahlung|mahngebühr|zahlt nicht|übernimmt nicht|selbst zahlen|dispo|konto (?:leer|im minus))\b",
    "theft": r"\b(?:snatched|swiped|nicked|took my|taken from|scam\w*|tricked|fake (?:caller|landlord|shop|seller)|hacked|"
             r"phish\w*|fraud|used my (?:credit )?card|identity|vanished with|never sent|took (?:the|our|my) money|"
             r"geklaut|gestohlen|entwendet|abgezogen|betrogen|abgezockt|gehackt|phishing|ausgetrickst|weggenommen|"
             r"aus der hand gerissen|enkeltrick|fake-shop|fakeshop|nicht geliefert)\b",
    "worry": r"\b(?:bad feeling|keep worrying|can't stop thinking|freaking out|stressing about|losing sleep over|"
             r"what if|on edge|uneasy|jittery|butterflies|mulmig|ungutes gefühl|kopfzerbrechen|grübel\w*|"
             r"mach mir sorgen|macht mir sorgen|nervt mich total|zittern)\b",
    "lossfind": r"\b(?:gone missing|went missing|is missing|are missing|disappeared|nowhere to be found|forgot (?:my|it|them|"
                r"the) \w+|left (?:it|them|my \w+) (?:behind|at home)|dropped (?:my|it)|vermisst|verschwunden|weg|"
                r"nirgends|liegen lassen|vergessen|verbummelt|verschlampt)\b",
}
for _k, _v in _EXTRA.items():
    _R[_k] = re.compile(_R[_k].pattern + "|" + _v)

_DAMAGEABLE = _CONCRETE - {"FOOD", "DRINK", "PLANT", "MONEY"}


def _decide(f: Frame, s: str) -> str:
    ev, cats = f.evidence, f.obj_cats
    thing = bool(cats & _DAMAGEABLE)
    R = _R
    if f.question and not (ev or thing or f.body or f.cause) and not R["lossfind"].search(s):
        return ""
    if re.search(r"\b(?:hungry|starving|thirsty|peckish|hungrig|hunger|durst|kohldampf)\b", s) and not R["sick"].search(s):
        return ""                                 # a need, not an illness
    if FACT.match(s):
        return ""                                 # a fact about the user, not something that happened
    if R["birth"].search(s):
        return "PLAN" if f.future and not re.search(r"\bpregnant|schwanger", s) else "MILESTONE"
    if R["death"].search(s):
        return "DAMAGE" if thing and not f.who in ("pet", "relative", "friend", "partner", "child") else "DEATH"
    if R["theft"].search(s):
        return "THEFT"
    if R["injury"].search(s) and (f.who or f.body):
        return "INJURY"
    if "RELEND" in ev or R["conflict"].search(s) or ("CONFLICT" in ev and f.who not in ("me", "")):
        return "CONFLICT"
    if R["exam"].search(s) and R["fail"].search(s):
        return "FAILURE"
    if R["exam"].search(s) and R["pass"].search(s) and not f.negated:
        return "PLAN" if f.future else "SUCCESS"
    if R["fired"].search(s) or R["reject"].search(s) or R["sportloss"].search(s):
        return "FAILURE"
    if R["lossfind"].search(s) and (thing or f.obj or re.search(r"\b(?:it|them|keys?|wallet|phone|es|sie|schlüssel)\b|"
                                                                 r"\b(?:my|her|his|our|their|mein\w*|ihr\w*|sein\w*|unser\w*) \w+", s)) \
            and not ("LOSE" in ev and cats & {"SPORT", "EVENT"}):
        return "LOSS"
    if R["delay"].search(s) and not ev & {"HARM", "BROKEN", "FLUID", "FIRE"}:
        return "DELAY"
    if "FALL" in ev and not f.question:
        return "INJURY"
    if (ev & {"HARM", "IMPACT", "FIRE", "FLUID", "BROKEN"}) and thing and not f.body and \
            not ("COOK" in ev and not ev & {"HARM", "BROKEN", "FLUID"}):
        return "DAMAGE"
    if "BROKEN" in ev:
        return "DAMAGE"
    event = R["injury"].search(s) or "IMPACT" in ev or "FALL" in ev or f.cause
    if (ev & {"HARM", "IMPACT", "BODY"}) and (f.body or f.cause) and event and not R["sick"].search(s) or \
            (f.body and f.cause):
        return "INJURY"
    sick = R["sick"].search(s) or ("BODYX" in ev and not R["worry"].search(s) and not R["feelneg"].search(s) and
                                   not R["feelpos"].search(s))
    if sick and f.who and not thing:
        return "INJURY" if f.body and event and not R["sick"].search(s) else "ILLNESS"
    if "HARM" in ev and f.who and f.who != "me" and not thing:
        return "INJURY"
    if R["money"].search(s) and ("MONEY" in ev or R["money"].search(s)) and not R["acquire"].search(s) or \
            (R["money"].search(s) and re.search(r"\b(?:can'?t|can not|cannot|kann (?:\w+ )*nicht|kaum|too|zu)\b", s)):
        return "MONEY"
    if R["milestone"].search(s):
        return "PLAN" if f.future else "MILESTONE"
    if (R["success"].search(s) or "WIN" in ev) and not f.negated and "FAIL" not in ev:
        return "SUCCESS"
    if "FAIL" in ev:
        return "FAILURE"
    if "JOB" in ev and f.negated:
        return "FAILURE"
    if R["worry"].search(s):
        return "WORRY"
    if R["feelneg"].search(s) and not f.future:
        return "FEEL_NEG"
    if f.body and f.who == "me" and not f.question:
        return "INJURY"
    if f.future and not f.question and (ev or thing or f.obj or len([w for w in f.words if len(w) > 3]) >= 2):
        return "PLAN"
    if R["acquire"].search(s) and (thing or f.obj or "BUY" in ev):
        return "ACQUIRE"
    if "BUY" in ev and thing:
        return "ACQUIRE"
    if R["feelpos"].search(s) or re.search(r"\b(?:happy|excited|proud|thrilled|relieved|glücklich|aufgeregt|stolz|"
                                           r"erleichtert)\b", s):
        return "FEEL_POS"
    if ev & {"COOK", "TRAVEL", "LEARN", "CELEB", "SLEEP", "EAT", "MOVE"} or re.search(
            r"\b(?:watched|went|visited|played|cooked|baked|read|made|tried|geschaut|war|waren|gespielt|gekocht|gebacken|"
            r"gelesen|gemacht|besucht)\b", s):
        return "PLAN" if f.future else ("ACTIVITY" if not f.question else "")
    return ""
