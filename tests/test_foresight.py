"""Thinking ahead (V4): a mishap is followed up with its usual forgotten next step on a later day."""
import datetime as dt

from engramm.chat.events import FORESIGHT_DAYS, EventBook, foresight_question


def test_foresight_due_language_and_expiry(tmp_path):
    book = EventBook(tmp_path / "e.json")
    d0 = dt.date(2026, 10, 1)
    book.foresee("DAMAGE", "ceiling", "en", d0)
    book.foresee("THEFT", "fahrrad", "de", d0)
    known = {"m1"}
    assert book.due_foresight(d0, "en", known) is None                       # not on the same day
    e = book.due_foresight(d0 + dt.timedelta(days=1), "en", known)
    assert e and "the ceiling" in foresight_question(e) and "photos" in foresight_question(e)
    g = book.due_foresight(d0 + dt.timedelta(days=1), "de", known)
    assert g and "Diebstahl" in foresight_question(g)
    assert book.due_foresight(d0 + dt.timedelta(days=FORESIGHT_DAYS + 1), "en", known) is None   # expired
    assert book.due_foresight(d0 + dt.timedelta(days=1), "en", set()) is None   # memory forgotten: nothing left
    book.mark_asked(e)
    assert EventBook(tmp_path / "e.json").due_foresight(d0 + dt.timedelta(days=1), "en", known) is None   # once


def test_foresight_replaces_same_kind(tmp_path):
    book = EventBook(tmp_path / "e.json")
    book.foresee("LOSS", "keys", "en", dt.date(2026, 10, 1))
    book.foresee("LOSS", "wallet", "en", dt.date(2026, 10, 2))
    assert [e.what for e in book.events] == ["LOSS|wallet|en"]
