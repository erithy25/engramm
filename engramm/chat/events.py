"""Memory v2: events the user announces ("I have an exam tomorrow", "my interview is on Friday").

ENGRAMM notes the event with its date (from the clock at the time it was said) and, when the user
greets it after that date, asks how it went — once. Events are kept in a small JSON file next to
the text memory (``chat_memory.events.json``); an event whose sentence was forgotten is dropped,
so "forget" still removes everything.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_WHEN = r"(?P<when>tomorrow|today|tonight|this (?:evening|afternoon|morning)|later(?: today)?|next week|on (?:" + "|".join(_DAYS) + \
        r")|(?:this|next) (?:" + "|".join(_DAYS) + r")|at \d{1,2}(?:[:.]\d{2})?(?: ?[ap]\.?m\.?)?(?! ?(?:years?|days?|weeks?|months?)\b)|" \
        r"at \d{1,2} o'?clock)"
_EVENT_WORDS = (r"exam|test|interview|appointment|meeting|presentation|job interview|date|match|game|concert|"
                r"surgery|operation|flight|trip|wedding|party|driving test|audition|deadline|first day|doctor'?s appointment|"
                r"dentist appointment|recital|race|competition|performance")
_PATTERNS = [
    re.compile(rf"\bi (?:have|'ve got|got|am having|'m having) (?:an?|my|the) (?:(?:big|important|final|math|maths|"
               rf"history|english|biology|chemistry|physics|french|german|spanish)\s+)?(?P<event>{_EVENT_WORDS})\b.*?\b{_WHEN}\b", re.I),
    re.compile(rf"\bmy (?:(?:big|important|final)\s+)?(?P<event>{_EVENT_WORDS}) is {_WHEN}\b", re.I),
    re.compile(rf"\b{_WHEN},? i (?:have|'ve got|got) (?:an?|my|the) (?P<event>{_EVENT_WORDS})\b", re.I),
]


FORESIGHT = "foresight"
FORESIGHT_DAYS = 14
# the situation kinds that have a typical forgotten next step, and that step as a question (EN, DE)
FORESIGHT_ASK = {
    "DAMAGE": ("By the way — did {x} get sorted? If it's insured, photos of the damage and the receipts make the claim "
               "much easier.",
               "Übrigens – hat sich das mit {x} geklärt? Wenn es versichert ist, helfen Fotos vom Schaden und die Belege sehr."),
    "THEFT": ("By the way — did you manage to report the theft? The police report number is usually needed for the "
              "insurance.",
              "Übrigens – konntest du den Diebstahl anzeigen? Die Nummer der Anzeige braucht meist die Versicherung."),
    "LOSS": ("Did {x} turn up again? If not, it's worth blocking any cards and asking at the lost and found.",
             "Ist {x} wieder aufgetaucht? Wenn nicht, lohnt es sich, Karten zu sperren und beim Fundbüro nachzufragen."),
    "INJURY": ("How is it doing now? If it isn't getting better after a few days, it's worth having it looked at.",
               "Wie geht es inzwischen damit? Wenn es nach ein paar Tagen nicht besser wird, lass es lieber anschauen."),
    "ILLNESS": ("Are you feeling better? If it's dragging on, it's worth seeing a doctor.",
                "Geht es dir besser? Wenn es sich hinzieht, lohnt sich ein Arztbesuch."),
    "CONFLICT": ("By the way — did things calm down after the argument?",
                 "Übrigens – hat sich das nach dem Streit wieder beruhigt?"),
}


def foresight_question(e: "Event") -> str:
    kind, obj, lang = (e.what.split("|") + ["", ""])[:3]
    en, de = FORESIGHT_ASK.get(kind, ("", ""))
    text = de if lang == "de" else en
    x = obj or ("das" if lang == "de" else "it")
    if lang == "de" and obj:
        x = obj if obj[:1].isupper() else obj.capitalize()
    return text.replace("{x}", (f"the {x}" if lang != "de" and obj else x))


@dataclass
class Event:
    what: str              # "exam"
    day: str               # ISO date of the event
    source: str            # memory id of the sentence it came from
    asked: bool = False


def event_date(when: str, today: dt.date) -> dt.date:
    w = when.lower()
    if w in ("today", "tonight", "later", "later today") or w.startswith("at ") or \
            w.startswith("this ") and w.split()[1] in ("evening", "afternoon", "morning"):
        return today
    if w == "tomorrow":
        return today + dt.timedelta(days=1)
    if w == "next week":
        return today + dt.timedelta(days=7)
    day = w.split()[-1]
    ahead = (_DAYS.index(day) - today.weekday()) % 7
    if w.startswith("next "):
        ahead += 7 if ahead == 0 else 0
    return today + dt.timedelta(days=ahead or 7)


def find_event(text: str, today: dt.date) -> tuple[str, dt.date] | None:
    for rx in _PATTERNS:
        m = rx.search(text)
        if m:
            return m.group("event").lower(), event_date(m.group("when"), today)
    return None


class EventBook:
    def __init__(self, path: Path | None):
        self.path = Path(path) if path else None
        self.events: list[Event] = []
        if self.path and self.path.exists():
            try:
                self.events = [Event(**e) for e in json.loads(self.path.read_text(encoding="utf-8"))]
            except (ValueError, TypeError):
                self.events = []

    def _save(self) -> None:
        if not self.path:
            return
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(e) for e in self.events], indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def note(self, what: str, day: dt.date, source: str) -> None:
        self.events = [e for e in self.events if not (e.what == what and e.day == day.isoformat())]
        self.events.append(Event(what, day.isoformat(), source))
        self._save()

    def foresee(self, kind: str, obj: str, lang: str, day: dt.date) -> None:
        """Thinking ahead (V4): after a mishap, the next step people usually forget is asked about on a later day.
        Only the kind of situation and the thing are kept (no sentence); it expires after FORESIGHT_DAYS and goes
        with "forget everything" (an empty memory)."""
        what = f"{kind}|{obj}|{lang}"
        self.events = [e for e in self.events if not (e.source == FORESIGHT and e.what.split("|")[0] == kind)]
        self.events.append(Event(what, day.isoformat(), FORESIGHT))
        self._save()

    def due(self, today: dt.date, known_sources: set[str]) -> Event | None:
        """The oldest past event not asked about yet whose sentence is still remembered (a foresight note: not
        older than FORESIGHT_DAYS, and only while anything at all is remembered)."""
        def alive(e: Event) -> bool:
            if e.source == FORESIGHT:
                return bool(known_sources) and (today - dt.date.fromisoformat(e.day)).days <= FORESIGHT_DAYS
            return e.source in known_sources
        keep = [e for e in self.events if alive(e)]
        if len(keep) != len(self.events):
            self.events = keep
            self._save()
        for e in sorted(self.events, key=lambda e: e.day):
            if not e.asked and dt.date.fromisoformat(e.day) < today:
                return e
        return None

    def due_foresight(self, today: dt.date, lang: str, known_sources: set[str]) -> Event | None:
        """A foresight note in this language from an earlier day, not asked about yet."""
        if not known_sources:
            return None
        for e in sorted(self.events, key=lambda e: e.day):
            if e.source == FORESIGHT and not e.asked and e.what.endswith("|" + lang):
                age = (today - dt.date.fromisoformat(e.day)).days
                if 0 < age <= FORESIGHT_DAYS:
                    return e
        return None

    def mark_asked(self, e: Event) -> None:
        e.asked = True
        self._save()
