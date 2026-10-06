"""Ideas on request (creative layer): app, product and business ideas, names, and a first plan — composed from the
topic of the conversation instead of answered with "I don't know".

Without a language model nothing is invented freely; what is composed here is a combination a founder would also go
through: who has the problem, who could solve it, and which mechanism connects them (marketplace, peer exchange,
daily practice, tool for organisations, shared knowledge), each with its features, how it earns money and the first
steps to test it. Names are built from the topic's own words (stem + ending, two stems blended). The choice among the
patterns is deterministic per message, "more" / "andere" gives the next ones, "the second one" / "die zweite" goes
into detail.
"""
from __future__ import annotations

import hashlib

from engramm.understand import _re as re

_IDEA_EN = re.compile(
    r"\b(?:(?:what|which) (?:kind of |sort of )?(?:app|apps|startup|business|product|tool|website|side hustle|project|"
    r"company|service)s? (?:can|could|should|would|do) (?:we|i|you) (?:build|make|start|create|do|launch)|"
    r"(?:give me|any|some|got any|need|have you got) (?:an? )?(?:good |cool |new |creative |fresh )?(?:ideas?|concepts?)|"
    r"ideas? (?:for|about|on) (?:an? )?|brainstorm\w*|come up with (?:an? )?(?:idea|app|concept|business)|"
    r"(?:app|business|startup|product) ideas?|let'?s build (?:an? )?(?:app|tool|startup|product)|"
    r"(?:build|make|create) (?:an? |something )(?:new )?(?:app|tool|startup|product|website)|"
    r"what (?:could|can|should) (?:we|i) (?:build|make|create|start))\b", re.I)
_IDEA_DE = re.compile(
    r"\b(?:(?:was für|welche) (?:eine? |einen )?(?:app|apps|start-?up|firma|geschäftsidee|produkt|tool|webseite|website|"
    r"idee|projekt)s? (?:können|könnten|sollen|sollten|kann|könnte|soll) (?:wir|ich)|ideen? (?:für|zu)|"
    r"geschäftsidee|start-?up-?idee|app-?idee|brainstorm\w*|lass uns (?:eine? )?(?:app|tool|start-?up|produkt) (?:bauen|machen)|"
    r"(?:hast du|gib mir|brauche) (?:eine |ein paar |paar )?(?:gute |neue |kreative )?ideen?|"
    r"was (?:können|könnten|sollen) wir (?:bauen|machen|gründen|entwickeln))\b", re.I)
_NAME = re.compile(r"\b(?:names? (?:for|ideas?)|name ideas?|(?:make|come up with|find|suggest|give me|need) (?:a |some |"
                   r"good )?names?|name (?:and|&) co|naming|wie (?:soll|könnte) .{0,25}heißen|namen? für|namensideen?|"
                   r"namensvorschl\w*|(?:neuen|einen|guten) namen)\b", re.I)
_PRODUCT = re.compile(r"\b(?:apps?|startups?|start-up|business(?:es)?|products?|tools?|websites?|compan(?:y|ies)|"
                      r"side hustle|saas|platform|services?|geschäft\w*|firma|gründ\w*|produkt\w*|webseite|plattform|"
                      r"dienst\w*|unternehmen)\b", re.I)
_MORE = re.compile(r"^(?:(?:any |some |got )?(?:more|other|different|new|else)(?: ones?| ideas?| names?)?|"
                   r"(?:noch )?(?:mehr|andere|weitere|neue)(?: ideen| namen| vorschläge)?|something else|was anderes)"
                   r"[\s?!.]*$", re.I)
_PICK = {"first": 0, "1st": 0, "one": 0, "erste": 0, "ersten": 0, "second": 1, "2nd": 1, "two": 1, "zweite": 1,
         "zweiten": 1, "third": 2, "3rd": 2, "three": 2, "dritte": 2, "dritten": 2, "1": 0, "2": 1, "3": 2}
_PICK_RX = re.compile(r"\b(?:the |die |den |nummer |number |#)?(first|1st|second|2nd|third|3rd|erste|ersten|zweite|"
                      r"zweiten|dritte|dritten|[123])\b(?: one| idea| idee| version)?", re.I)
_RICH = re.compile(r"\b(?:rich|wealthy|millionaire|make (?:more )?money|earn more|financial freedom|reich|wohlhabend|"
                   r"millionär|(?:mehr )?geld verdienen|finanziell frei)\b", re.I)
_BUILD_IT = re.compile(r"^(?:(?:ok|okay|so|and|und|also) )?(?:can|could|will|would) you help me (?:build|make|create|"
                       r"start|with|plan)|^help me (?:build|make|plan|start|get)|^(?:kannst|könntest) du mir (?:helfen|"
                       r"dabei helfen)|^hilf mir|^how do i (?:start|begin|get started)|^wie fange ich an", re.I)

_STOP = set("""ok okay got have with my our your their this that what which kind sort app apps business idea ideas new
should could would build make create name names and co problem problems trouble issue thing things something want
need help please can you we lets let some any good cool really just also very about with from into like there here
hallo bitte ein eine einen einem einer mit meine meinem meinen meiner unser unsere wir was für welche können könnten
soll sollen sollte machen bauen neue neues neuen idee ideen namen name problem probleme habe hab ich und oder auch
nicht noch mal gibt geben school schule give gave giving tell show find get start erste ersten zweite dritte
first second third one two three our unser unsere eure your idea business startup company product tool website side
hustle project service app thing stuff lot way time year week today plan plans money rich reich geld""".split())
_SERVICE = re.compile(r"\b(?:walk\w*|sitt\w*|clean\w*|repair\w*|fix\w*|deliver\w*|babysit\w*|care|caring|pflege\w*|"
                      r"gassi|putz\w*|reparatur\w*|liefer\w*|betreu\w*|hüte\w*|garden\w*|garten\w*|moving|umzug\w*|"
                      r"haircut\w*|friseur\w*|massage\w*|catering|cook\w*|koch\w*|laundry|wäsche|nail\w*|photo\w*|"
                      r"foto\w*|dog|hund\w*|pet|haustier\w*|plant\w*|pflanz\w*)\b", re.I)
_EDU = re.compile(r"\b(?:tutor\w*|nachhilfe\w*|school|schule|homework|hausaufgabe\w*|exam\w*|prüfung\w*|klausur\w*|"
                  r"learn\w*|lern\w*|student\w*|schüler\w*|teacher\w*|lehrer\w*|class\w*|klasse\w*|studium|uni)\b", re.I)

# who meets whom, per field (en, de); the general case names the topic itself
_ROLES = {
    "edu": {"en": dict(users="students", providers="tutors", buyers="parents", org="schools", topic="tutoring"),
            "de": dict(users="Schüler", providers="Nachhilfelehrern", buyers="Eltern", org="Schulen", topic="Nachhilfe")},
}

_SERVICE_PATTERNS = [
    {"key": "match",
     "en": ("{Name}: book a trusted {provider_one} for {topic} in two taps — verified profiles, reviews, live tracking "
            "and payment in the app.", ["Verified profiles with reviews", "Booking in two taps, live status",
                                       "Payment and tips in the app"], "15–20 % commission per booking"),
     "de": ("{Name}: in zwei Klicks eine vertrauenswürdige Person für {topic} buchen – geprüfte Profile, Bewertungen, "
            "Live-Status und Bezahlung in der App.", ["Geprüfte Profile mit Bewertungen", "Buchung in zwei Klicks, Live-Status",
                                                      "Bezahlung und Trinkgeld in der App"], "15–20 % Provision pro Buchung")},
    {"key": "subscription",
     "en": ("{Name}: {topic} on a fixed weekly plan with the same person every time — no searching, no rebooking.",
            ["Weekly plan you set once", "Always the same trusted person, with a stand-in",
             "Pause or skip with one tap"], "monthly subscription per plan"),
     "de": ("{Name}: {topic} im festen Wochenplan, immer mit derselben Person – kein Suchen, kein Neubuchen.",
            ["Wochenplan einmal festlegen", "Immer dieselbe Vertrauensperson, mit Vertretung", "Pausieren mit einem Tipp"],
            "Monatsabo pro Plan")},
    {"key": "group",
     "en": ("{Name}: neighbours bundle {topic} — one person does it for several households on the same street, "
            "cheaper for everyone.", ["Map of who nearby wants the same", "Shared slots and fair cost split",
                                       "Group chat per street"], "small fee per bundled booking"),
     "de": ("{Name}: Nachbarn bündeln {topic} – eine Person übernimmt es für mehrere Haushalte in derselben Straße, "
            "günstiger für alle.", ["Karte, wer in der Nähe dasselbe will", "Gemeinsame Termine und faire Kostenteilung",
                                    "Gruppenchat pro Straße"], "kleine Gebühr pro gebündelter Buchung")},
    {"key": "pro",
     "en": ("{Name}: the app for people who offer {topic} — clients, routes, schedule and invoices in one place.",
            ["Client list with notes", "Route and schedule planner", "One-tap invoices and reminders"],
            "subscription for providers, about 10–20 € a month"),
     "de": ("{Name}: die App für Leute, die {topic} anbieten – Kunden, Routen, Termine und Rechnungen an einem Ort.",
            ["Kundenliste mit Notizen", "Routen- und Terminplaner", "Rechnungen und Erinnerungen per Tipp"],
            "Abo für Anbieter, etwa 10–20 € im Monat")},
]

_PATTERNS = [
    {"key": "match",
     "en": ("{Name}: a marketplace that matches {users} with vetted {providers} — profiles, reviews, booking and payment "
            "in one place.", ["Profiles with subjects, prices and reviews", "Calendar booking and reminders",
                              "In-app payment and simple invoices for {buyers}"], "10–15 % commission per session"),
     "de": ("{Name}: ein Marktplatz, der {users} mit geprüften {providers} zusammenbringt – Profile, Bewertungen, "
            "Buchung und Bezahlung an einem Ort.", ["Profile mit Fächern, Preisen und Bewertungen",
                                                    "Terminbuchung mit Erinnerungen",
                                                    "Bezahlung in der App, einfache Rechnungen für {buyers}"],
            "10–15 % Provision pro Termin")},
    {"key": "peer",
     "en": ("{Name}: {users} who are good at something help others and earn credits they can spend on help "
            "themselves.", ["Skill profiles and a credit balance", "Short video or chat sessions",
                            "Leaderboard and certificates for helpers"], "free for users, paid premium or sponsorship by {org}"),
     "de": ("{Name}: {users}, die etwas gut können, helfen anderen und verdienen Punkte, die sie selbst gegen Hilfe "
            "eintauschen.", ["Fähigkeitsprofile und Punktekonto", "Kurze Video- oder Chat-Sitzungen",
                             "Bestenliste und Zertifikate für Helfer"], "kostenlos für Nutzer, Premium oder gesponsert von {org}")},
    {"key": "practice",
     "en": ("{Name}: turns {topic} into 10-minute daily missions with streaks; {buyers} see progress at a glance.",
            ["Daily missions adapted to weak spots", "Streaks, levels and small rewards",
             "Weekly progress report for {buyers}"], "subscription, about 5–10 € a month"),
     "de": ("{Name}: macht aus {topic} tägliche 10-Minuten-Missionen mit Serien; {buyers} sehen den Fortschritt auf "
            "einen Blick.", ["Tägliche Missionen, angepasst an Schwächen", "Serien, Level und kleine Belohnungen",
                             "Wöchentlicher Fortschrittsbericht für {buyers}"], "Abo, etwa 5–10 € im Monat")},
    {"key": "org",
     "en": ("{Name}: the organiser for {org} — who needs {topic}, who offers it, when and where, with attendance and "
            "materials.", ["Needs and availability in one overview", "Automatic schedule and room plan",
                           "Attendance, notes and shared materials"], "licence per {org_one}, e.g. 50–200 € a month"),
     "de": ("{Name}: das Organisationstool für {org} – wer {topic} braucht, wer sie anbietet, wann und wo, mit "
            "Anwesenheit und Material.", ["Bedarf und Verfügbarkeit in einer Übersicht", "Automatischer Stunden- und Raumplan",
                                          "Anwesenheit, Notizen und geteiltes Material"], "Lizenz pro {org_one}, z. B. 50–200 € im Monat")},
    {"key": "community",
     "en": ("{Name}: a question-and-answer space for {topic} where the best explanations rise to the top and good "
            "helpers become bookable.", ["Questions with photo upload", "Voting and verified answers",
                                         "Book the best helpers for a live session"], "free answers, paid live sessions and ads-free premium"),
     "de": ("{Name}: ein Frage-Antwort-Ort für {topic}, an dem die besten Erklärungen nach oben wandern und gute "
            "Helfer buchbar werden.", ["Fragen mit Foto-Upload", "Bewertungen und geprüfte Antworten",
                                       "Die besten Helfer live buchen"], "Antworten kostenlos, bezahlte Live-Sitzungen und Premium ohne Werbung")},
]

_SUFFIXES = ["ly", "io", "ify", "loop", "hub", "mate", "nest", "spark", "base", "flow", "go", "up"]
_PREFIXES = ["Go", "Up", "My", "Open", "Bright", "Easy"]


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def _topic_words(text: str, lang: str = "en") -> list[str]:
    """The topic: the words after "about / for / with / für / mit / zu" first, then the other nouns the lexicon knows."""
    low = text.lower()
    from engramm.understand.lex import lexicon
    lx = lexicon(lang)
    def noun(w: str) -> bool:
        return w not in _STOP and (any(e.pos == "n" for e in lx.lookup(w)) or w.endswith(("ing", "ung", "hilfe")))
    out: list[str] = []
    for m in re.finditer(r"\b(?:about|for|with|around|on|für|mit|zu|zum|zur|über|rund um)\s+(?:my |our |the |a |an |"
                         r"meine[mnr]? |unsere[mnr]? |der |die |das |dem |den |einer? |einem )?([a-zäöüß-]+(?:\s+[a-zäöüß-]+)?)",
                         low):
        for w in m.group(1).split():
            if len(w) >= 3 and noun(w) and w not in out:
                out.append(w)
    for w in re.findall(r"[a-zäöüß][a-zäöüß-]{2,}", low):
        if len(w) >= 3 and noun(w) and w not in out:
            out.append(w)
    return out


def _stem(w: str) -> str:
    w = re.sub(r"(?:ing|ung|ungen|en|er|s)$", "", w) if len(w) > 6 else w
    return w.rstrip("-")


def _split(w: str) -> list[str]:
    """A long German compound in its parts ("pflanzenpflege" → pflanzen, pflege), when both are nouns the lexicon knows."""
    if len(w) < 10:
        return [w]
    from engramm.understand.lex import lexicon
    lx = lexicon("de")
    for k in range(len(w) - 4, 3, -1):
        a, b = w[:k], w[k:]
        if any(e.pos == "n" for e in lx.lookup(b)) and (any(e.pos == "n" for e in lx.lookup(a)) or
                                                        any(e.pos == "n" for e in lx.lookup(a.rstrip("ns")))):
            return [a, b]
    return [w]


def _pronounceable(w: str) -> bool:
    lw = w.lower()
    return (4 <= len(lw) <= 11 and re.search(r"[aeiouyäöü]", lw[-4:]) is not None and
            not re.search(r"[bcdfghjklmnpqrstvwxzß]{4}", lw) and not lw.endswith(("yly", "ylo")) and not re.search(r"([a-z])\1\1", lw))


def names(topic_words: list[str], seed: int, n: int = 4) -> list[str]:
    """Made-up names from the topic's own words: stem + ending, prefix + stem, two stems joined, two stems blended at
    a vowel; only pronounceable ones."""
    parts: list[str] = []
    for w in topic_words:
        parts += _split(w)
    stems = list(dict.fromkeys(_stem(w) for w in parts if len(w) >= 3))[:3] or ["idea"]
    cands: list[str] = []
    for s_ in stems:
        cands += [(s_[:-1] if s_.endswith("y") and suf[0] in "aeiou" else s_) + suf for suf in _SUFFIXES]
        cands += [pre.lower() + s_ for pre in _PREFIXES]
    if len(stems) > 1:
        a, b = stems[0], stems[1]
        cands += [a + b, b + a]
        for x, y in ((a, b), (b, a)):
            cut = next((k for k in range(len(x) - 1, 1, -1) if x[k] in "aeiouäöü"), None)
            if cut is not None:
                cands.append(x[:cut + 1] + y[1:] if y[0] not in "aeiouäöü" else x[:cut] + y)
    good = [c for c in dict.fromkeys(cands) if _pronounceable(c)]
    if not good:
        good = [stems[0] + "ly"]
    out: list[str] = []
    for i in range(len(good)):
        c = good[(seed + i * 7) % len(good)]
        c = c[:1].upper() + c[1:]
        if c not in out:
            out.append(c)
        if len(out) >= n:
            break
    return out


def _roles(text: str, lang: str, words: list[str]) -> dict:
    if _EDU.search(text):
        r = dict(_ROLES["edu"][lang], kind="edu")
    elif _SERVICE.search(" ".join(words[:3])):
        t = " ".join(words[:2]) if len(words) > 1 and _SERVICE.search(words[1]) else words[0]
        tt = t if lang == "en" else t[:1].upper() + t[1:]
        r = dict(users="customers" if lang == "en" else "Kunden", providers="providers" if lang == "en" else "Anbietern",
                 buyers="customers" if lang == "en" else "Kunden", org="clubs and companies" if lang == "en" else
                 "Vereine und Firmen", topic=tt, provider_one="helper" if lang == "en" else "Person", kind="service")
    else:
        t = words[0] if words else ("das Thema" if lang == "de" else "it")
        if lang == "de":
            r = dict(users="Leute, die Hilfe bei " + t.capitalize() + " brauchen", providers="Leuten, die das anbieten",
                     buyers="Kunden", org="Vereine und Firmen", topic=t.capitalize(), provider_one="Person", kind="general")
        else:
            r = dict(users="people who need help with " + t, providers="people who offer it", buyers="customers",
                     org="clubs and companies", topic=t, provider_one="helper", kind="general")
    r["org_one"] = {"Schulen": "Schule", "schools": "school"}.get(r["org"], "organisation" if lang == "en" else "Organisation")
    return r


def _set(roles: dict) -> list[dict]:
    """The patterns that fit the kind of topic: learning, a service someone does for you, or anything else."""
    if roles.get("kind") == "service":
        return _SERVICE_PATTERNS
    if roles.get("kind") == "edu":
        return _PATTERNS
    return [_SERVICE_PATTERNS[0], _PATTERNS[4], _SERVICE_PATTERNS[3], _PATTERNS[3], _SERVICE_PATTERNS[1]]


def _render(lang: str, idx: list[int], roles: dict, nm: list[str], with_names: bool) -> str:
    de = lang == "de"
    lines = ["Hier sind drei Ideen, die zu deinem Thema passen:" if de else "Here are three ideas that fit your topic:", ""]
    for j, i in enumerate(idx):
        p = _set(roles)[i][lang]
        name = nm[j] if j < len(nm) else f"Idee {j + 1}"
        fmt = {**roles, "Name": f"**{name}**"}
        lines.append(f"{j + 1}. " + p[0].format(**fmt))
        lines.append(("   Funktionen: " if de else "   Features: ") + "; ".join(x.format(**fmt) for x in p[1]))
        lines.append(("   Geld: " if de else "   Money: ") + p[2].format(**fmt))
    if with_names and len(nm) > len(idx):
        lines += ["", ("Weitere Namen: " if de else "More names: ") + ", ".join(nm[len(idx):]) +
                  (" (vorher Domain und Marke prüfen)." if de else " (check the domain and trademark first).")]
    lines += ["", ("So würde ich starten: diese Woche mit 10 Leuten aus der Zielgruppe über das Problem reden, dann eine "
                   "Landingpage mit Warteliste, dann die kleinste Version mit nur einer Funktion. Welche Idee gefällt dir "
                   "am besten – 1, 2 oder 3?") if de else
              ("How I'd start: talk to 10 people from the target group about the problem this week, then a landing page "
               "with a waitlist, then the smallest version with just one feature. Which one do you like best — 1, 2 or 3?")]
    return "\n".join(lines)


def _detail(lang: str, i: int, roles: dict, name: str) -> str:
    de = lang == "de"
    pat = _set(roles)[i]
    p = pat[lang]
    fmt = {**roles, "Name": f"**{name}**"}
    steps = (["Woche 1: 10 Gespräche mit der Zielgruppe – was nervt sie heute, was zahlen sie bisher?",
              "Woche 2: Klick-Prototyp (z. B. Figma) und Landingpage mit Warteliste; Ziel: 50 Anmeldungen.",
              f"Woche 3–6: kleinste Version nur mit „{p[1][0].format(**fmt)}“; 5 echte Nutzer begleiten.",
              f"Danach: Preis testen ({p[2].format(**fmt)}) und erst dann weitere Funktionen bauen."] if de else
             ["Week 1: 10 conversations with the target group — what annoys them today, what do they pay now?",
              "Week 2: click prototype (e.g. Figma) and a landing page with a waitlist; goal: 50 sign-ups.",
              f"Weeks 3–6: smallest version with only \"{p[1][0].format(**fmt)}\"; walk 5 real users through it.",
              f"Then: test the price ({p[2].format(**fmt)}) and only then build more features."])
    head = (f"Gute Wahl. {p[0].format(**fmt)}\n\nPlan:" if de else f"Good pick. {p[0].format(**fmt)}\n\nPlan:")
    risk = ("Größtes Risiko: genug Anbieter und Nutzer gleichzeitig zu gewinnen – starte deshalb an einem Ort oder in "
            + ("einer Schule." if roles.get("kind") == "edu" else "einem Viertel.") if de and pat["key"] in ("match", "peer", "community", "group") else
            "Größtes Risiko: dass es nach zwei Wochen keiner mehr nutzt – miss deshalb von Anfang an, wer wiederkommt." if de else
            ("Biggest risk: getting enough providers and users at the same time — so start in one town or one "
             + ("school." if roles.get("kind") == "edu" else "neighbourhood."))
            if pat["key"] in ("match", "peer", "community", "group") else
            "Biggest risk: nobody uses it after two weeks — so measure from day one who comes back.")
    return head + "\n" + "\n".join(f"• {s}" for s in steps) + "\n\n" + risk


def _rich_plan(lang: str) -> str:
    if lang == "de":
        return ("Gern – Reichtum entsteht fast immer über drei Hebel:\n\n"
                "• Mehr verdienen: eine gefragte Fähigkeit ausbauen oder etwas Eigenes aufbauen, das ohne deine Zeit skaliert.\n"
                "• Weniger ausgeben, als du verdienst: feste Sparquote, am besten automatisch am Monatsanfang.\n"
                "• Früh investieren: breit gestreut und langfristig, damit der Zinseszins arbeitet.\n\n"
                "Ein konkreter Start: Notiere diese Woche Einnahmen und Ausgaben, leg 10–20 % automatisch zur Seite und überleg, "
                "welches Problem du für andere lösen könntest – daraus entsteht oft das eigene Projekt. "
                "Kein Anlagerat im Einzelfall; bei größeren Summen lohnt eine unabhängige Beratung. "
                "Womit fängst du an – Job, Ersparnisse oder eine eigene Idee?")
    return ("Sure — wealth almost always comes from three levers:\n\n"
            "• Earn more: build a skill that's in demand, or build something of your own that scales without your time.\n"
            "• Spend less than you earn: a fixed savings rate, ideally automatic at the start of the month.\n"
            "• Invest early: broadly diversified and long-term, so compounding does the work.\n\n"
            "A concrete start: track income and spending this week, put 10–20 % aside automatically, and think about which "
            "problem you could solve for other people — that's often where your own project comes from. "
            "Not individual investment advice; for larger sums an independent adviser is worth it. "
            "Where are you starting from — a job, savings, or an idea of your own?")


def respond(st, msg: str, lang: str) -> str | None:
    """A reply for an explicit request for ideas, names or a plan; None when the message is something else."""
    low = msg.strip().lower()
    de = lang == "de"
    said = (st.uses.get("u_notes") or {}).get("_said", []) if st is not None else []
    convo = " ".join(said[-6:]) + " " + low
    last = st.uses.get("u_ideas") if st is not None else None
    if isinstance(last, dict) and st.turn - last.get("turn", -99) <= 4:
        m = _PICK_RX.search(low)
        if m and len(low.split()) <= 8 and not _IDEA_EN.search(low) and not _IDEA_DE.search(low):
            k = _PICK[m.group(1).lower()]
            if k < len(last["idx"]):
                last["turn"] = st.turn
                return _detail(lang, last["idx"][k], last["roles"], last["names"][k])
        if _MORE.match(low):
            seed = last["seed"] + 3
            n = len(_set(last["roles"]))
            idx = [(seed + j) % n for j in range(3)]
            nm = names(last["words"], seed + 11, 5)
            last.update(seed=seed, idx=idx, names=nm, turn=st.turn)
            return _render(lang, idx, last["roles"], nm, True)
    asks_idea = bool((_IDEA_DE if de else _IDEA_EN).search(low) or _IDEA_EN.search(low)) and bool(_PRODUCT.search(low))
    asks_name = bool(_NAME.search(low)) and (bool(_PRODUCT.search(convo)) or not re.search(
        r"\b(?:dog|puppy|cat|kitten|pet|hamster|rabbit|bird|fish|baby|child|son|daughter|boy|girl|hund\w*|welpe\w*|"
        r"katze\w*|kater|haustier\w*|kaninchen|vogel|baby|kind|sohn|tochter|junge|mädchen)\b", convo))
    if asks_idea or asks_name:
        words = _topic_words(low, lang) or _topic_words(convo, lang)
        if _EDU.search(convo):
            words = [w for w in words if _EDU.search(w)] + [w for w in words if not _EDU.search(w)]
        seed = _seed(low)
        roles = _roles(convo, lang, words)
        nm = names(words or [roles["topic"].lower()], seed, 5)
        if asks_name and not asks_idea:
            if st is not None:
                st.uses["u_ideas"] = {"seed": seed, "idx": [], "names": nm, "words": words, "roles": roles,
                                      "turn": st.turn}
            return ((f"Ein paar Namensideen: {', '.join(nm)}. Kurz, gut auszusprechen und aus deinem Thema gebaut – "
                     "prüf vorher Domain und Marke. Soll ich in eine bestimmte Richtung gehen (verspielt, seriös, englisch)?")
                    if de else
                    (f"A few name ideas: {', '.join(nm)}. Short, easy to say and built from your topic — check the domain "
                     "and trademark first. Want a particular direction (playful, serious, German-sounding)?"))
        idx = [(seed + j) % len(_set(roles)) for j in range(3)]
        if 0 not in idx:
            idx[0] = 0                                  # the marketplace is the obvious first candidate
        if st is not None:
            st.uses["u_ideas"] = {"seed": seed, "idx": idx, "names": nm, "words": words, "roles": roles, "turn": st.turn}
        return _render(lang, idx, roles, nm, asks_name or True)
    if _BUILD_IT.search(low) and _RICH.search(convo):
        return _rich_plan(lang)
    if re.search(r"\b(?:how (?:do|can) i (?:get|become) (?:rich|wealthy)|wie werde ich reich)\b", low):
        return _rich_plan(lang)
    return None
