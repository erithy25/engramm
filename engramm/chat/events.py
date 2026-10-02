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

    def due(self, today: dt.date, known_sources: set[str]) -> Event | None:
        """The oldest past event not asked about yet whose sentence is still remembered."""
        keep = [e for e in self.events if e.source in known_sources]
        if len(keep) != len(self.events):
            self.events = keep
            self._save()
        for e in sorted(self.events, key=lambda e: e.day):
            if not e.asked and dt.date.fromisoformat(e.day) < today:
                return e
        return None

    def mark_asked(self, e: Event) -> None:
        e.asked = True
        self._save()
