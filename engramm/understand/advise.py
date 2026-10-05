"""Advice that stays on the conversation's topic (U6): what the user asks for, answered for the problem the conversation
is about — not for a keyword in the last message, and never with a refusal or a coin flip.

The domain comes from the whole conversation (device, home, cooking, people, work or school, money, health, pet,
travel, celebration, writing); the kind of request from the last message (a dilemma "A or B?", "is that normal/okay/
worth it?", "what do I say?", "what should I do / what else can I try?", "what do you think?", a closing turn). The
texts are general advice per domain and request — no topic lists, no invented facts; health advice always ends with
when to see a doctor.

It runs after the other layers (dialog.py) and replaces only a reply that does not help: a refusal, a filler, a coin
flip, a stored sentence that does not answer, or a list of tips for a different kind of problem.
"""
from __future__ import annotations

from engramm.understand import _re as re

_DOMAINS = [
    ("device", r"\b(?:printer|wifi|wi-fi|wlan|router|laptop|computer|pc|phone|handy|smartphone|tablet|app|update|bluetooth|"
               r"screen|bildschirm|display|keyboard|tastatur|mouse|maus|tv|fernseher|console|konsole|headphones|kopfhörer|"
               r"charger|ladekabel|password|passwort|email|e-mail|account|konto|internet|drucker|software|battery|akku)\b"),
    ("home", r"\b(?:fridge|kühlschrank|freezer|washing machine|waschmaschine|dishwasher|spülmaschine|oven|ofen|heating|heizung|"
             r"boiler|tap|wasserhahn|sink|spüle|toilet|klo|shower|dusche|leak|leck|mould|mold|schimmel|window|fenster|door|tür|"
             r"drain|abfluss|clog\w*|verstopf\w*|pipe|rohr\w*|waschbecken|bathroom|badezimmer|bad|kitchen|küche|"
             r"lock|schloss|roof|dach|wall|wand|floor|boden|lamp|lampe|light|licht|plant|pflanze|garden|garten|furniture|"
             r"möbel|sofa|couch|carpet|teppich|landlord|vermieter\w*|neighbou?r|nachbar\w*|flat|apartment|wohnung|house|haus)\b"),
    ("cooking", r"\b(?:cook\w*|bak\w*|recipe|rezept|dough|teig|starter|sauerteig|sourdough|bread|brot|cake|kuchen|oven|ofen|"
                r"flour|mehl|sauce|soße|soup|suppe|dinner|abendessen|meal|essen|kochen|backen|pan|pfanne|ingredients?|zutaten)\b"),
    ("pet", r"\b(?:dog|hund|cat|katze|kater|puppy|welpe|kitten|kätzchen|hamster|rabbit|kaninchen|bird|vogel|parrot|"
            r"guinea pig|meerschweinchen|vet|tierarzt|fish tank|aquarium|pet|haustier)\b"),
    ("health", r"\b(?:pain|schmerz\w*|hurts?|weh|tut weh|sick|krank|fever|fieber|cough|husten|cold|erkält\w*|headache|"
               r"kopfschmerz\w*|stomach|bauch\w*|rash|ausschlag|itch\w*|juck\w*|sleep|schlaf\w*|tired|müde|doctor|arzt|ärztin|"
               r"dizzy|schwindel\w*|swollen|geschwollen|back|rücken|knee|knie|tooth|zahn|eye|auge)\b"),
    ("money", r"\b(?:money|geld|bill|rechnung|rent|miete|debt|schulden|bank|loan|kredit|budget|salary|gehalt|price|preis|"
              r"expensive|teuer|save|sparen|tax|steuer\w*|insurance|versicherung|refund|erstattung|subscription|abo)\b"),
    ("work", r"\b(?:work|arbeit|job|boss|chef\w*|manager|colleague|kollege\w*|kollegin|team|office|büro|meeting|project|"
             r"projekt|deadline|interview|vorstellungsgespräch|promotion|beförderung|school|schule|teacher|lehrer\w*|exam|"
             r"prüfung|klausur|homework|hausaufgaben|class|klasse|uni|university|studium|thesis|seminar)\b"),
    ("travel", r"\b(?:trip|reise|travel\w*|flight|flug|train|zug|bus|hotel|holiday|urlaub|vacation|camping|zelt\w*|"
               r"passport|reisepass|luggage|gepäck|airport|flughafen|booking|buchung)\b"),
    ("celebration", r"\b(?:party|feier|fest|birthday|geburtstag|wedding|hochzeit|anniversary|jahrestag|surprise|überraschung|"
                    r"exhibition|ausstellung|celebrat\w*|guests?|gäste)\b"),
    ("writing", r"\b(?:write|schreiben|schreib\w*|statement|speech|rede|letter|brief|essay|text|message|nachricht|email|"
                r"post|caption|card|karte|draft|entwurf)\b"),
    ("people", r"\b(?:friend|freund\w*|partner|boyfriend|girlfriend|wife|husband|mum|mom|mother|mutter|mama|dad|father|vater|"
               r"papa|sister|schwester|brother|bruder|grandma|oma|grandpa|opa|family|familie|kid|kids|son|sohn|daughter|"
               r"tochter|roommate|mitbewohner\w*|guy|girl|typ|schwiegermutter|schwiegervater|in-laws?|kollegin|nachbarin)\b"),
]

_ADVICE = {  # domain → (EN steps, DE steps)
    "general": (["Start with the simplest possible cause and rule it out.",
                 "Change one thing at a time, so you can see what helps.",
                 "Write down what you've tried — it helps you or anyone you ask for help.",
                 "If it's still stuck after that, ask someone who deals with this regularly."],
                ["Mit der einfachsten möglichen Ursache anfangen und sie ausschließen.",
                 "Immer nur eine Sache ändern, dann siehst du, was hilft.",
                 "Aufschreiben, was du schon probiert hast – das hilft dir oder jedem, den du fragst.",
                 "Wenn es danach noch hakt, jemanden fragen, der sich damit regelmäßig auskennt."]),
    "pet_training": (["Stay calm and consistent — reward the behaviour you want right away, ignore the rest.",
                      "Practise in short sessions (5–10 minutes) every day rather than long ones.",
                      "Stop or turn around the moment it pulls or misbehaves, and only go on when it's calm.",
                      "A trainer or a puppy class helps a lot if you're stuck."],
                     ["Ruhig und konsequent bleiben – gewünschtes Verhalten sofort belohnen, den Rest ignorieren.",
                      "Lieber täglich kurz üben (5–10 Minuten) als selten lange.",
                      "Sofort stehen bleiben oder umdrehen, wenn er zieht oder Unsinn macht, und erst weitergehen, wenn er ruhig ist.",
                      "Eine Hundeschule oder ein Trainer hilft sehr, wenn du nicht weiterkommst."]),
    "device": (["Restart both the device and the router, then try again.",
                "Remove the connection (forget the network / unpair it) and set it up fresh.",
                "Check for updates — the app, the driver or the firmware often fixes exactly this.",
                "Try another way in between: a cable, another device, or the manufacturer's support page."],
               ["Gerät und Router neu starten, dann nochmal probieren.",
                "Die Verbindung entfernen (Netzwerk vergessen / Kopplung löschen) und neu einrichten.",
                "Nach Updates schauen – App, Treiber oder Firmware beheben oft genau das.",
                "Übergangsweise einen anderen Weg nehmen: Kabel, anderes Gerät oder die Hilfeseite des Herstellers."]),
    "home": (["Check the obvious first: power, fuse, settings, and whether anything is blocked or loose.",
              "Look up the model's manual — most have a troubleshooting page for exactly this.",
              "Take a photo or a short video of the problem; it helps a repair person or your landlord.",
              "If it's rented, tell your landlord early and in writing; otherwise get a quote before deciding to replace."],
             ["Erst das Naheliegende prüfen: Strom, Sicherung, Einstellungen, und ob etwas verstopft oder locker ist.",
              "In die Anleitung des Modells schauen – die meisten haben eine Fehlerseite genau dafür.",
              "Ein Foto oder kurzes Video vom Problem machen; das hilft dem Handwerker oder dem Vermieter.",
              "Bei einer Mietwohnung früh und schriftlich Bescheid geben; sonst vor dem Neukauf einen Kostenvoranschlag holen."]),
    "cooking": (["Check the basics of the recipe: amounts, temperature and timing — small changes matter a lot.",
                 "Warmth helps most doughs and starters; a cold kitchen slows everything down.",
                 "Change one thing at a time, so you can tell what made the difference.",
                 "Give it a little more time before you give up on it."],
                ["Die Grundlagen des Rezepts prüfen: Mengen, Temperatur, Zeit – kleine Änderungen machen viel aus.",
                 "Wärme hilft den meisten Teigen und Ansätzen; in einer kalten Küche dauert alles länger.",
                 "Immer nur eine Sache ändern, dann siehst du, was den Unterschied macht.",
                 "Etwas mehr Zeit geben, bevor du aufgibst."]),
    "pet": (["Watch whether it's eating, drinking and behaving normally.",
             "Keep it calm and away from anything it might have eaten or chewed.",
             "Call the vet if it lasts more than a day, gets worse, or something seems really off — they'd rather hear from you early."],
            ["Beobachten, ob es frisst, trinkt und sich normal verhält.",
             "Ruhig halten und von allem fernhalten, was es gefressen oder angeknabbert haben könnte.",
             "Den Tierarzt anrufen, wenn es länger als einen Tag dauert, schlimmer wird oder dir etwas komisch vorkommt."]),
    "health": (["Rest, drink enough, and give it a day or two.",
                "A pharmacist can tell you what helps with the symptoms.",
                "See a doctor if it gets worse, doesn't improve within a few days, or comes with high fever, strong pain or trouble breathing."],
               ["Ausruhen, genug trinken und ein, zwei Tage abwarten.",
                "In der Apotheke bekommst du Rat, was gegen die Beschwerden hilft.",
                "Zum Arzt, wenn es schlimmer wird, nach ein paar Tagen nicht besser ist oder hohes Fieber, starke Schmerzen oder Atemnot dazukommen."]),
    "money": (["Write down exactly what's owed and by when — it's less scary on paper.",
               "Ask early about instalments or a later date; most companies agree if you ask before it's due.",
               "Check the bill or contract for mistakes before you pay.",
               "Free debt or budget counselling can help if it gets too much."],
              ["Genau aufschreiben, was bis wann fällig ist – auf Papier wirkt es kleiner.",
               "Früh nach Raten oder Aufschub fragen; die meisten stimmen zu, wenn man vor der Frist fragt.",
               "Rechnung oder Vertrag vor dem Bezahlen auf Fehler prüfen.",
               "Eine kostenlose Schuldner- oder Budgetberatung hilft, wenn es zu viel wird."]),
    "work": (["Talk to the person directly and calmly, in private, before it grows.",
              "Describe what happened and what you need, without blaming — \"I\" sentences work best.",
              "Write down the facts (dates, what was said) in case you need them later.",
              "If talking doesn't help, go to your manager, teacher or HR as the next step."],
             ["Erst direkt und ruhig unter vier Augen mit der Person sprechen, bevor es größer wird.",
              "Sagen, was passiert ist und was du brauchst, ohne Vorwürfe – Ich-Botschaften funktionieren am besten.",
              "Die Fakten notieren (Daten, was gesagt wurde), falls du sie später brauchst.",
              "Wenn Reden nicht hilft: als nächsten Schritt Vorgesetzte, Lehrkraft oder Personalabteilung einschalten."]),
    "travel": (["Check your options: the next connection, rebooking, or another route.",
                "Keep tickets and receipts — delays and cancellations often mean compensation.",
                "Make a short checklist so nothing important is forgotten."],
               ["Optionen prüfen: nächste Verbindung, umbuchen oder ein anderer Weg.",
                "Tickets und Belege aufheben – bei Verspätung oder Ausfall gibt es oft eine Entschädigung.",
                "Eine kurze Checkliste machen, damit nichts Wichtiges fehlt."]),
    "celebration": (["Think about what the guest of honour enjoys most — that matters more than size.",
                     "Keep the plan simple: a place, a time, the people who matter.",
                     "Split the jobs (food, invitations, decoration) so it doesn't all land on you."],
                    ["Überleg, was die Hauptperson am meisten mag – das zählt mehr als die Größe.",
                     "Den Plan einfach halten: ein Ort, eine Zeit, die Menschen, die wichtig sind.",
                     "Aufgaben verteilen (Essen, Einladungen, Deko), damit nicht alles an dir hängt."]),
    "writing": (["Start with one sentence about what it is and why it matters to you.",
                 "Then two or three concrete details — they make it yours.",
                 "Keep it short and honest; read it out loud once and cut what sounds stiff."],
                ["Mit einem Satz anfangen: worum es geht und warum es dir wichtig ist.",
                 "Dann zwei, drei konkrete Details – die machen es persönlich.",
                 "Kurz und ehrlich bleiben; einmal laut lesen und streichen, was steif klingt."]),
    "people": (["Talk to them directly and calmly — in private, not in front of others.",
                "Say how it affects you rather than what they did wrong.",
                "Give them a chance to explain; there may be something you don't know.",
                "If it doesn't get better, it's okay to take some distance."],
               ["Direkt und ruhig mit der Person sprechen – unter vier Augen, nicht vor anderen.",
                "Sagen, wie es dir damit geht, statt was sie falsch gemacht hat.",
                "Ihr die Chance geben, es zu erklären; vielleicht weißt du etwas nicht.",
                "Wenn es nicht besser wird, ist Abstand völlig okay."]),
}
_ESCALATE = r"\b(?:manager|boss|hr|chef\w*|personalabteilung|police|polizei|lawyer|anwalt|landlord|vermieter\w*|complain\w*|beschwer\w*)\b"
_DIRECT = r"\b(?:say something|talk|tell|ask|speak|mention|sprech\w*|ansprech\w*|sag\w*|frag\w*|red\w*)\b"
_SOFT = r"\b(?:personal|honest|small|smaller|simple|simpler|direct|try|first|wait|calm|kleiner|persönlich\w*|ehrlich|einfach\w*|" \
        r"warten|ruhig|erstmal|zuerst)\b"
_HARD = r"\b(?:delete|quit|cancel|ignore|replace|buy (?:a )?new|throw|break up|leave|löschen|kündig\w*|absagen|ignorier\w*|" \
        r"neu kaufen|wegwerfen|schluss machen)\b"


def domain(text: str, min_hits: int = 1) -> str:
    low = text.lower()
    scores = [(len(set(re.findall(rx, low))), -i, name) for i, (name, rx) in enumerate(_DOMAINS)]
    best = max(scores)
    return best[2] if best[0] >= min_hits else ""


def _said(st) -> str:
    return " ".join((st.uses.get("u_notes") or {}).get("_said", []))


def request(low: str) -> str | None:
    """The kind of help asked for, or None."""
    if re.search(r"^(?:ok(?:ay)?|alright|cool|fair|great|perfect|got it|sounds good|good idea|thanks?|thank you|ty|lol ok|lol|"
                 r"ok(?:ay)? cool|okay then|alles klar|ok(?:ay)? danke|danke|super|gut|passt|klingt gut|mach ich|gute idee|stimmt|"
                 r"true|right|yeah|ja|haha|huh|ah|aha|makes sense|macht sinn|verstehe)\b", low) and \
            not re.search(r"\?\s*$", low) and len(low.split()) <= 14:
        return "close"
    if re.search(r"\bor\b|\boder\b", low) and re.search(r"\?\s*$", low) and re.search(
            r"\b(?:should i|shall i|do i|would you|is it|is that|should it|should we|would it|soll ich|sollte ich|soll (?:es|das)|"
            r"sollten wir|ist (?:es|das)|lieber|better|besser)\b", low):
        return "choice"
    if re.search(r"\b(?:is (?:it|that|this) (?:normal|ok|okay|bad|rude|weird|worth|dead|safe|fine|too much|a problem)|"
                 r"is it even worth|should i (?:be )?worr\w*|ist (?:das|es) (?:normal|schlimm|okay|ok|unhöflich|komisch|"
                 r"tot|kaputt|zu viel|ein problem)|lohnt (?:sich|es sich)|muss ich mir sorgen)\b", low):
        return "judge"
    if re.search(r"\b(?:what (?:do|should|could|would) i (?:even )?(?:say|write|text|tell)|how (?:do|would|should|can) i (?:even )?"
                 r"(?:start|say|tell|bring (?:it|this) up|ask|approach|word|apologi[sz]e)|how to (?:start|say|tell|ask)|"
                 r"what to say|was (?:soll|sag|schreib)\w* ich|wie (?:sag|sprech|fang|frag|formulier)\w* ich|wie bring ich)\b", low):
        return "say"
    if re.search(r"\bhow long (?:does|will|would|did) (?:that|it|this|something like that|sowas) (?:take|last)\b|"
                 r"\bwie lange (?:dauert|braucht|geht) (?:das|sowas|es|so was)\b", low):
        return "howlong"
    if re.search(r"\b(?:what (?:do you|d you) think|what'?s your (?:opinion|take)|thoughts\?|good idea\?|was (?:meinst|denkst|"
                 r"hältst) du|findest du)\b", low):
        return "opinion"
    if re.search(r"\b(?:what (?:should|can|could) i do|what do i do (?:now|about|with|if|when|next|here|then|first)|what (?:else )?(?:can|could|should) i try|what now|and now|any (?:tips|"
                 r"advice|ideas)|how do i (?:fix|handle|deal|stop|get|make|clean|remove|keep|find|know|cope|sort)|how can i|"
                 r"what (?:should|can) i (?:use|get|buy|try)|help|i (?:don'?t|dont) know (?:what|how|whether|if)|no idea (?:what|how)|"
                 r"was (?:soll|kann|könnte) ich (?:tun|machen|noch)|was jetzt|und jetzt|hast du (?:tipps|einen tipp|ne idee)|"
                 r"wie (?:krieg|bekomm|mach|werd|schaff|halt)\w* ich|keine ahnung,? (?:was|wie|ob)|ich weiß nicht,? (?:was|wie|ob)|"
                 r"soll ich)\b", low):
        return "do"
    if re.search(r"^should i\b|\bshould i\b.*\?\s*$|^would (?:it|that) (?:work|help)|^soll(?:te)? ich\b|"
                 r"\bhow (?:do|can|should|would) i (?:best )?\w+|\bwie \w+e ich\b.*\?|\bwie (?:geht|funktioniert) das\b", low):
        return "do"
    return None


_WEAK = re.compile(r"^(?:i don'?t know|you haven'?t told|i'?m not sure how to answer|das weiß ich|das kann ich auf deutsch|"
                   r"da muss ich passen|das habe ich nicht|das verstehe ich|sorry, who|nice! which one|who do you mean|"
                   r"wen meinst du|got it\.?$|okay, i see\.?$|ah, okay\.?|mm-hm|alles klar\.?$|okay, verstehe|let me pick|"
                   r"tough call|ich würfel|lass mich wählen|oh, interesting|interessant|opinions aren'?t|"
                   r"noted, thanks|got it — i'?ll remember|got it, you|i can help with|right\? 😄|"
                   r"oh nice, congrats|that's not among|that'?s outside|i don't have practical tips|ich würde abwägen|"
                   r"wenn es sich für dich richtig anfühlt|was hält dich zurück|if it feels right|what'?s holding you back|"
                   r"weigh it up|hm, da komme ich nicht|i don't know, sorry)", re.I)


def weak(reply: str, kind: str) -> bool:
    r = (reply or "").strip()
    return kind in ("unknown", "nothing") or not r or bool(_WEAK.search(r))


def off_topic(reply: str, convo: str) -> bool:
    """A tip list for a different kind of problem: the list's own domain differs from the conversation's, and it shares
    (almost) no content word with it."""
    if "•" not in reply:
        return False
    rd, cd = domain(reply, 2), domain(convo, 2)
    if not rd or not cd or rd == cd:
        return False
    stop = {"that", "this", "with", "your", "you", "the", "and", "for", "it's", "just", "what", "have", "from", "they",
            "them", "then", "when", "into", "about", "dass", "das", "die", "der", "und", "mit", "für", "ist", "nicht",
            "machen", "könntest", "etwas", "einen", "eine", "noch", "could", "would", "things", "thing", "something",
            "there", "where", "which", "their", "these", "those", "other", "anything", "einfach", "immer", "wieder"}
    rw = {w[:5] for w in re.findall(r"[a-zäöüß]{5,}", reply.lower()) if w not in stop}
    cw = {w[:5] for w in re.findall(r"[a-zäöüß]{5,}", convo.lower()) if w not in stop}
    if len(rw & cw) > 0:
        return False
    rx = dict(_DOMAINS)[rd]                       # the conversation must not touch the list's own domain at all
    return not re.search(rx, convo.lower())


def advise(st, msg: str, lang: str, reply: str, kind: str) -> str | None:
    low = msg.lower().strip()
    req = request(low)
    if req is None:
        return None
    convo = _said(st) + " " + low
    de = lang == "de"
    if req == "close":
        r = (reply or "").strip()
        probe = re.search(r"(?:how'?s that going|how are you feeling|what'?s on your mind|how old is it|is it switched off|"
                          r"was beschäftigt dich|wie geht'?s dir damit|wie fühlst du dich|erzähl ruhig|tell me more|"
                          r"what happened|was ist passiert|go on|oh\?|erzähl weiter)\??\.?\s*$", r, re.I)
        if weak(r, kind) or probe or _STORE_ACK.search(r):
            return _close(low, de)
        return None
    if not (weak(reply, kind) or off_topic(reply or "", convo) or re.match(r"(?:let me pick|tough call)", (reply or "").lower())):
        return None
    dom = domain(convo)
    if req == "choice":
        return _choice(low, dom, de)
    if req == "judge":
        return _judge(low, dom, de)
    if req == "say":
        return _say(low, dom, de)
    if req == "opinion":
        return _opinion(low, dom, de)
    if req == "howlong":
        return _howlong(dom, convo, de)
    return _steps(dom, de, convo)


def _howlong(dom: str, convo: str, de: bool) -> str:
    if dom == "pet" or re.search(r"\b(?:train\w*|leash|leine|erzieh\w*)\b", convo):
        return ("Mit täglichem, kurzem Üben merkst du meist nach ein bis drei Wochen eine deutliche Besserung – richtig sitzen "
                "tut es oft nach ein, zwei Monaten." if de else
                "With short daily practice you usually see a clear difference within one to three weeks — for it to really "
                "stick, give it a month or two.")
    if dom == "health":
        return ("Meist ein paar Tage bis eine Woche. Dauert es länger oder wird es schlimmer, lass es ärztlich anschauen."
                if de else "Usually a few days to a week. If it takes longer or gets worse, have a doctor look at it.")
    if dom == "cooking":
        return ("Das hängt stark von Temperatur und Menge ab – im Zweifel lieber etwas mehr Zeit geben und zwischendurch prüfen."
                if de else "That depends a lot on temperature and amount — when in doubt, give it a bit more time and check in between.")
    return ("Das ist unterschiedlich – plan lieber etwas mehr Zeit ein, als du denkst, dann bist du auf der sicheren Seite."
            if de else "It varies — plan a bit more time than you think, then you're on the safe side.")


def _steps(dom: str, de: bool, convo: str = "") -> str | None:
    if dom == "pet" and re.search(r"\b(?:pull\w*|bark\w*|bit(?:es|ing)|chew\w*|scratch\w*|jump\w*|leash|lead|train\w*|zieht|"
                                  r"ziehen|bellt|bellen|beißt|kratzt|springt|leine|erzieh\w*|training|kommando)\b", convo):
        dom = "pet_training"
    if dom not in _ADVICE:
        dom = "general"
    steps = _ADVICE[dom][1 if de else 0]
    head = "Das würde ich versuchen:" if de else "Here's what I'd try:"
    return head + "\n\n" + "\n".join(f"• {s}" for s in steps)


def _options(low: str) -> list[str]:
    q = re.sub(r"^(?:and |so |but |ok |und |also |aber )?(?:should i|shall i|do i|would you|is it better to|should it be|"
               r"should we|would it be better to|soll ich|sollte ich|soll es|sollten wir|ist es besser,?)\s+", "", low.rstrip("?! ."))
    parts = re.split(r",?\s+(?:or|oder)\s+", q, maxsplit=1)
    return [p.strip() for p in parts] if len(parts) == 2 else []


def _choice(low: str, dom: str, de: bool) -> str:
    opts = _options(low)
    if len(opts) != 2:
        return _steps(dom, de) or ("Beides kann passen – ich würde mit dem anfangen, was sich leichter rückgängig machen lässt."
                                   if de else "Both can work — I'd start with whichever is easier to undo.")
    a, b = opts
    pick, why = None, ""
    for x, y in ((a, b), (b, a)):
        if re.search(_DIRECT, x) and re.search(_ESCALATE, y):
            pick, why = x, ("erst direkt reden ist fairer, und eskalieren kannst du danach immer noch" if de else
                            "talking directly first is fairer, and you can still escalate if it doesn't help")
            break
        if re.search(_SOFT, x) and not re.search(_SOFT, y):
            pick, why = x, ("das ist der kleinere, persönlichere Schritt" if de else "it's the smaller, more personal step")
            break
        if re.search(_HARD, y) and not re.search(_HARD, x):
            pick, why = x, ("das lässt sich leichter rückgängig machen" if de else "it's easier to undo")
            break
    if pick is None and re.search(r"\b(?:normal|okay|ok|fine|harmless|harmlos)\b", a + " " + b):
        return _judge(low, dom, de)
    if pick is None:
        pick, why = a, ("das lässt sich leichter ausprobieren und notfalls ändern" if de else "it's easier to try and change later")
    pick = re.sub(r"^(?:to |zu )", "", pick)
    pick = re.sub(r"\b(?:my|mein\w*)\b", "deine" if de else "your", pick)
    if de:
        return f"Ich würde zu „{pick}“ tendieren – {why}."
    return f"I'd lean towards “{pick}” — {why}."


def _judge(low: str, dom: str, de: bool) -> str:
    if re.search(r"\b(?:worth (?:it|repairing|fixing)|lohnt (?:sich|es sich)|reparatur lohnt)\b", low) and \
            not re.search(r"\b(?:repair\w*|fix\w*|broken|kaputt|reparier\w*|defekt)\b", low + " " + dom):
        return ("Rechne es einmal durch: die Gesamtkosten über die ganze Laufzeit gegen die günstigste Alternative. Wenn du das "
                "Neue nicht wirklich brauchst, lohnt es sich meistens nicht." if de else
                "Do the maths once: the total cost over the whole term against the cheapest alternative. If you don't really "
                "need the new thing, it usually isn't worth it.")
    if re.search(r"\b(?:worth (?:it|repairing|fixing)|lohnt (?:sich|es sich)|reparatur lohnt)\b", low):
        return ("Als Faustregel: Kostet die Reparatur mehr als etwa die Hälfte eines neuen Geräts, ist Ersetzen meist "
                "sinnvoller – sonst lohnt sich die Reparatur. Ein Kostenvoranschlag klärt das schnell." if de else
                "Rule of thumb: if the repair costs more than about half the price of a new one, replacing usually makes more "
                "sense — otherwise repairing is worth it. A quote settles it quickly.")
    if dom == "health":
        return ("Oft ist das harmlos und geht von selbst weg. Zum Arzt solltest du, wenn es schlimmer wird, länger als ein paar "
                "Tage anhält oder starke Schmerzen, hohes Fieber oder Atemnot dazukommen." if de else
                "Often it's harmless and passes on its own. See a doctor if it gets worse, lasts more than a few days, or comes "
                "with strong pain, high fever or trouble breathing.")
    if dom in ("home", "device"):
        return ("Ein bisschen davon ist oft normal, gerade bei älteren Geräten. Warnzeichen sind: wird plötzlich lauter oder "
                "anders, riecht verbrannt, wird heiß oder funktioniert nicht mehr richtig. Bei einem älteren Gerät lohnt sich "
                "ein Kostenvoranschlag, bevor du entscheidest, ob Reparatur oder Neukauf." if de else
                "A bit of that is often normal, especially with older devices. Warning signs: it suddenly gets louder or "
                "different, smells burnt, gets hot, or stops working properly. For an older one, get a repair quote before "
                "deciding between repairing and replacing.")
    if dom == "cooking":
        return ("Meistens ist es nicht verloren – oft braucht es nur mehr Wärme oder Zeit. Erst wenn es schimmelt oder richtig "
                "unangenehm riecht, würde ich neu anfangen." if de else
                "Usually it's not lost — it often just needs more warmth or time. Only if there's mould or a really bad smell "
                "would I start over.")
    if dom == "pet":
        return ("Einmal ist meistens kein Grund zur Sorge. Wenn es wiederkommt, das Tier schlapp wirkt oder nicht frisst, ruf "
                "den Tierarzt an." if de else
                "Once is usually nothing to worry about. If it keeps happening, or your pet seems weak or won't eat, call the vet.")
    if dom in ("people", "work"):
        return ("Das ist völlig verständlich – vielen ginge es da genauso. Wichtig ist, wie du dich dabei fühlst; wenn es dich "
                "beschäftigt, lohnt sich ein ruhiges, ehrliches Gespräch." if de else
                "That's completely understandable — lots of people would feel the same. What matters is how it sits with you; "
                "if it keeps bugging you, a calm, honest conversation is worth it.")
    return ("Meistens ist das kein großes Problem. Wenn es dich weiter beschäftigt oder schlimmer wird, würde ich es klären."
            if de else "Most of the time it's not a big deal. If it keeps bothering you or gets worse, I'd look into it.")


def _say(low: str, dom: str, de: bool) -> str:
    if de:
        return ("Halt es kurz und freundlich, unter vier Augen – zum Beispiel: „Hey, hast du kurz eine Minute? Ist mir ein "
                "bisschen unangenehm, aber ich wollte etwas ansprechen, bevor es mich weiter beschäftigt …“ Dann sagst du in "
                "einem Satz, was dich stört, und schlägst eine Lösung vor. Ich-Botschaften wirken weniger wie ein Vorwurf.")
    return ("Keep it short and friendly, and in private — something like: “Hey, got a minute? This is a bit awkward, but I "
            "wanted to mention something before it bugs me more…” Then say in one sentence what's bothering you and suggest "
            "a fix. “I” sentences sound much less like blame.")


def _opinion(low: str, dom: str, de: bool) -> str:
    m = re.search(r"\b(?:maybe|perhaps|vielleicht|eher)\s+(.{3,60}?)(?:\s+then|\s+dann)?\s*[?.!]", low + "?")
    if m:
        idea = m.group(1).strip()
        return (f"Klingt für mich vernünftig – {idea} passt gut zu dem, was du erzählt hast." if de else
                f"Sounds sensible to me — {idea} fits what you've told me.")
    return ("Ich finde, das klingt gut durchdacht. Wenn es sich für dich richtig anfühlt, würde ich es so machen." if de else
            "I think that sounds well thought through. If it feels right to you, I'd go for it.")


def _close(low: str, de: bool) -> str:
    if re.search(r"\b(?:thanks?|thank you|ty|danke)\b", low):
        return "Gern! Viel Erfolg damit. 🙂" if de else "You're welcome — good luck with it! 🙂"
    if re.search(r"\b(?:i'?ll|i will|gonna|going to|let me|ich (?:werde|mach\w*|probier\w*|versuch\w*)|mach ich)\b", low):
        return "Klingt nach einem guten Plan – sag gern Bescheid, wie es lief!" if de else \
            "Sounds like a good plan — let me know how it goes!"
    return "Freut mich! 😊" if de else "Glad to hear it! 😊"


_STORE_ACK = re.compile(r"^(?:noted, thanks for telling me about|got it — i'?ll remember that about)", re.I)
_POSITIVE = {"SUCCESS", "MILESTONE", "ACQUIRE", "FEEL_POS"}
_NEGATIVE = {"DAMAGE", "INJURY", "ILLNESS", "LOSS", "THEFT", "CONFLICT", "FAILURE", "MONEY", "DELAY", "WORRY", "DEATH",
             "FEEL_NEG"}


def react(st, msg: str, lang: str, reply: str) -> str | None:
    """A memory confirmation ("Noted, thanks for telling me about your grandfather.") on a message that tells news
    becomes a reaction to the news; a stable fact ("my name is …", "i live in …") keeps its confirmation."""
    if not _STORE_ACK.search((reply or "").strip()):
        return None
    low = msg.lower().strip()
    if re.match(r"^(?:my name|i'?m called|call me|i live|i'?m from|i work as|my (?:favou?rite|birthday)|ich heiße|ich wohne|"
                r"ich komme aus|ich arbeite als|mein (?:lieblings|geburtstag))", low):
        return None
    from engramm.understand.frames import parse
    f = parse(msg, lang)
    de = lang == "de"
    if (f.kind in _POSITIVE and f.rule_kind in _POSITIVE) or re.search(r"\b(?:turns? \d+|got (?:picked|chosen|accepted|the job)|won|passed|engaged|pregnant|"
                                        r"wird \d+|bestanden|gewonnen|angenommen)\b|!{1,}", low) and f.kind not in _NEGATIVE:
        return "Oh wie schön! 🎉 Erzähl, wie fühlt sich das an?" if de else "Oh, that's lovely news! 🎉 How does it feel?"
    if re.match(r"^(?:no|nein|wait|warte|sorry|actually|eigentlich)\b", low):
        return "Ah, verstehe – danke für die Klarstellung!" if de else "Ah, got it — thanks for clarifying!"
    if f.rule_kind in _NEGATIVE and _BAD.search(low):
        return "Oh nein, das tut mir leid. Was ist passiert?" if de else "Oh no, I'm sorry to hear that. What happened?"
    if re.search(r"\b(?:started|keeps?|always|never|stopped|again|won'?t|refuses|suddenly|lately|angefangen|ständig|immer|"
                 r"nie|nicht mehr|wieder|plötzlich|neuerdings|seit)\b", low):
        return "Hm, das ist blöd. Seit wann geht das so?" if de else "Hm, that's not great. How long has that been going on?"
    return None


_JOY = re.compile(r"^(?:toll zu hören|das klingt (?:richtig )?gut|herrlich|wie schön|oh,? schön|haha,? wie schön|klingt spannend|"
                  r"oh,? wie schön|das freut mich|super!|wunderbar|oh nice,? congrats|congrat\w*|that'?s (?:great|wonderful|"
                  r"awesome|amazing)|love that|awesome|yay|ooh, i like the sound|how exciting|oh,? that'?s lovely)", re.I)
_SORRY = re.compile(r"^(?:oh no|oh nein|oh je|that sounds (?:really )?(?:hard|rough|tough)|i'?m sorry|das tut mir leid|"
                    r"oh,? das tut|that doesn'?t sound good|das klingt nicht gut|ugh)", re.I)
_BAD = re.compile(r"\b(?:broken|kaputt|leak\w*|verstopft|langsam|slow|komisch|weird|stinkt|smells?|riecht|nervt|annoying|"
                  r"problem|ugh|stress\w*|bringt nix|doesn'?t work|not working|won'?t|can'?t|funktioniert nicht|geht nicht|"
                  r"weh|hurts?|pain|schmerz\w*|sick|krank|lost|verloren|late|zu spät|failed|durchgefallen|worried|sorge\w*|"
                  r"angst|anxious|nervous|nervös|sad|traurig|annoy\w*|ärger\w*|streit|fight|argument|refuses|weigert|"
                  r"verschimmelt|mould|mold|kalt|cold|loud|laut|noise|lärm|smell|gestank|peinlich|embarrass\w*|awkward|"
                  r"pleite|teuer|expensive|bill|rechnung|nicht so begeistert|hates?|hasst|meldet sich nicht|ghost\w*|"
                  r"ignor\w*|left me|verlassen|vermiss\w*|miss (?:him|her|them))\b", re.I)
_GOOD = re.compile(r"\b(?:won|gewonnen|passed|bestanden|got (?:the job|picked|selected|accepted|in(?:to)?|engaged)|promoted|befördert|"
                   r"engaged|verlobt|pregnant|schwanger|finally|endlich|yay|juhu|hooray|excited|happy|glücklich|"
                   r"proud|stolz|best|great news|gute nachrichten|celebrat\w*|feier\w*|freue? mich|freut mich|freu dich)\b|"
                   r"🎉|😁|🥳|!!", re.I)


_GOOD_ADJ = re.compile(r"\b(?:amazing|awesome|wonderful|fantastic|loved it|incredible|großartig|genial|wunderbar|"
                       r"fantastisch)\b", re.I)


def valence_fix(st, msg: str, lang: str, reply: str) -> str | None:
    """Joy on a problem, or sympathy on good news, is replaced by a reaction of the right colour."""
    r = (reply or "").strip()
    low = msg.lower()
    de = lang == "de"
    bad, good = bool(_BAD.search(low)), bool(_GOOD.search(low))
    sit = st.uses.get("u_sit") if isinstance(st.uses.get("u_sit"), dict) else None
    sit_bad = bool(sit and sit.get("kind") in _NEGATIVE and st.turn - sit.get("turn", -99) <= 2)
    if _JOY.search(r) and (bad or (sit_bad and not good)) and not good and not _GOOD_ADJ.search(low):
        if re.search(r"\?\s*$", low):
            return None
        opts = (["Hm, das klingt nervig. Was hast du schon probiert?", "Oh je, das ist ärgerlich.", "Mist, das auch noch.",
                 "Das klingt echt lästig."] if de else
                ["Hm, that sounds annoying. What have you tried so far?", "Ugh, that's frustrating.", "Oh no, that too.",
                 "That sounds really annoying."])
        recent = set(getattr(st, "recent", []) or [])
        return next((o for o in opts if o not in recent), opts[-1])
    if _SORRY.search(r) and good and not bad:
        return "Oh, das ist ja toll! 🎉 Erzähl mehr!" if de else "Oh, that's great news! 🎉 Tell me more!"
    return None


_EN_WORDS = re.compile(r"\b(?:the|that|you|your|sound|like|what|how|nice|really|tell me|i'?m|it'?s|good|great)\b", re.I)
_DE_WORDS = re.compile(r"\b(?:das|du|ich|und|nicht|ist|wie|schön|klingt|mir|dir|gern|was|ja|nein)\b", re.I)


def language_fix(st, msg: str, lang: str, reply: str) -> str | None:
    """A German conversation gets a German reply: a short English line there is replaced."""
    if lang != "de" or not reply or len(reply) > 200:
        return None
    if len(_EN_WORDS.findall(reply)) >= 2 and not _DE_WORDS.search(reply):
        low = msg.lower()
        if _GOOD.search(low) or re.search(r"[😭😍🥹🎉😁]", msg):
            return "Wow, wie toll! 🎉"
        if _BAD.search(low):
            return "Oh je, das klingt nicht schön."
        return "Ah, okay – erzähl ruhig weiter."
    return None
