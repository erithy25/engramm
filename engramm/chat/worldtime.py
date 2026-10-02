"""The time in another city ("what time is it in Tokyo?") without a time-zone database.

The app ships no tz database (Windows has none, and ``tzdata`` is not bundled), so this module keeps
the standard UTC offsets of well-known cities and countries and the four daylight-saving rules that
matter for them: the EU (last Sunday of March to last Sunday of October, 01:00 UTC), the US and
Canada (second Sunday of March to first Sunday of November, 02:00 local), south-east Australia (first
Sunday of October to first Sunday of April) and New Zealand (last Sunday of September to first Sunday
of April). Everything else has no daylight saving time today.
"""
from __future__ import annotations

import datetime as dt

# name → (standard offset in hours, DST rule or None, shown name)
_PLACES: dict[str, tuple[float, str | None, str]] = {}


def _add(names: str, offset: float, rule: str | None, shown: str | None = None) -> None:
    for n in names.split("|"):
        _PLACES[n] = (offset, rule, shown or " ".join(w[:1].upper() + w[1:] for w in n.split()))


_add("london|uk|united kingdom|england|britain|great britain|scotland|edinburgh|manchester|dublin|ireland|"
     "lisbon|portugal|wales|belfast", 0, "eu")
_add("paris|france|berlin|germany|munich|hamburg|frankfurt|cologne|madrid|spain|barcelona|rome|italy|milan|"
     "amsterdam|netherlands|brussels|belgium|vienna|austria|zurich|geneva|switzerland|prague|czech republic|"
     "warsaw|poland|budapest|hungary|stockholm|sweden|oslo|norway|copenhagen|denmark|venice|florence|naples|"
     "belgrade|serbia|zagreb|croatia|luxembourg", 1, "eu")
_add("athens|greece|helsinki|finland|kyiv|kiev|ukraine|bucharest|romania|sofia|bulgaria|riga|vilnius|tallinn", 2, "eu")
_add("cairo|egypt|johannesburg|cape town|south africa|jerusalem|tel aviv|israel", 2, None)
_add("istanbul|turkey|moscow|russia|riyadh|saudi arabia|nairobi|kenya|doha|qatar", 3, None)
_add("dubai|abu dhabi|united arab emirates|uae", 4, None)
_add("tehran|iran", 3.5, None)
_add("karachi|pakistan", 5, None)
_add("delhi|new delhi|mumbai|bangalore|india|kolkata|chennai", 5.5, None)
_add("kathmandu|nepal", 5.75, None)
_add("dhaka|bangladesh", 6, None)
_add("bangkok|thailand|jakarta|indonesia|hanoi|ho chi minh city|vietnam", 7, None)
_add("beijing|shanghai|china|hong kong|singapore|taipei|taiwan|manila|philippines|kuala lumpur|malaysia|perth|bali", 8, None)
_add("tokyo|japan|osaka|kyoto|seoul|south korea|korea", 9, None)
_add("brisbane", 10, None)
_add("sydney|melbourne|canberra|australia", 10, "au")
_add("adelaide", 9.5, "au")
_add("auckland|wellington|new zealand", 12, "nz")
_add("new york|new york city|nyc|washington|boston|miami|atlanta|toronto|montreal|philadelphia|detroit", -5, "us")
_add("chicago|houston|dallas|mexico city|winnipeg|new orleans", -6, "us")
_add("mexico", -6, None)
_add("denver|calgary|salt lake city", -7, "us")
_add("phoenix", -7, None)
_add("los angeles|la|san francisco|seattle|las vegas|vancouver|san diego|portland|california", -8, "us")
_add("anchorage|alaska", -9, "us")
_add("honolulu|hawaii", -10, None)
_add("sao paulo|são paulo|rio de janeiro|rio|brazil|buenos aires|argentina", -3, None)
_add("lima|peru|bogota|bogotá|colombia", -5, None)
_PLACES["mexico city"] = (-6, None, "Mexico City")              # Mexico dropped daylight saving time in 2022
_PLACES["la"] = (-8, "us", "Los Angeles")
_PLACES["nyc"] = (-5, "us", "New York")
_PLACES["uae"] = (4, None, "the UAE")
_PLACES["uk"] = (0, "eu", "the UK")
# German names ("wie spät ist es in Tokio?")
for _de, _en in (("tokio", "tokyo"), ("rom", "rome"), ("wien", "vienna"), ("prag", "prague"), ("peking", "beijing"),
                 ("kopenhagen", "copenhagen"), ("lissabon", "lisbon"), ("warschau", "warsaw"), ("moskau", "moscow"),
                 ("mailand", "milan"), ("venedig", "venice"), ("florenz", "florence"), ("neapel", "naples"),
                 ("athen", "athens"), ("brüssel", "brussels"), ("zürich", "zurich"), ("genf", "geneva"),
                 ("kairo", "cairo"), ("neu-delhi", "new delhi"), ("singapur", "singapore"), ("seoul", "seoul"),
                 ("deutschland", "germany"), ("frankreich", "france"), ("spanien", "spain"), ("italien", "italy"),
                 ("england", "england"), ("japan", "japan"), ("china", "china"), ("indien", "india"),
                 ("australien", "australia"), ("brasilien", "brazil"), ("türkei", "turkey"), ("griechenland", "greece"),
                 ("österreich", "austria"), ("schweiz", "switzerland"), ("niederlande", "netherlands"),
                 ("dänemark", "denmark"), ("schweden", "sweden"), ("norwegen", "norway"), ("polen", "poland"),
                 ("russland", "russia"), ("thailand", "thailand"), ("mexiko", "mexico"), ("kanada", "toronto")):
    if _en in _PLACES and _de not in _PLACES:
        _PLACES[_de] = (_PLACES[_en][0], _PLACES[_en][1], _de[:1].upper() + _de[1:])


def _nth_sunday(year: int, month: int, n: int) -> dt.date:
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(6 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_sunday(year: int, month: int) -> dt.date:
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def _dst(rule: str | None, utc: dt.datetime, offset: float) -> bool:
    if rule is None:
        return False
    y = utc.year
    if rule == "eu":
        start = dt.datetime.combine(_last_sunday(y, 3), dt.time(1), dt.timezone.utc)
        end = dt.datetime.combine(_last_sunday(y, 10), dt.time(1), dt.timezone.utc)
        return start <= utc < end
    local = utc + dt.timedelta(hours=offset)                    # standard local time
    if rule == "us":
        start = dt.datetime.combine(_nth_sunday(y, 3, 2), dt.time(2), dt.timezone.utc)
        end = dt.datetime.combine(_nth_sunday(y, 11, 1), dt.time(1), dt.timezone.utc)
        return start <= local < end
    if rule == "au":                                            # southern summer: October to April
        end = dt.datetime.combine(_nth_sunday(y, 4, 1), dt.time(2), dt.timezone.utc)
        start = dt.datetime.combine(_nth_sunday(y, 10, 1), dt.time(2), dt.timezone.utc)
        return local < end or local >= start
    if rule == "nz":
        end = dt.datetime.combine(_nth_sunday(y, 4, 1), dt.time(2), dt.timezone.utc)
        start = dt.datetime.combine(_last_sunday(y, 9), dt.time(2), dt.timezone.utc)
        return local < end or local >= start
    return False


def time_in(place: str, utc: dt.datetime | None = None) -> tuple[str, dt.datetime] | None:
    """(shown name, local time) for a known city or country, else None."""
    key = " ".join(place.lower().strip(" ?.!").split())
    key = key[4:] if key.startswith("the ") else key
    hit = _PLACES.get(key)
    if hit is None:
        return None
    offset, rule, shown = hit
    now = utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    hours = offset + (1 if _dst(rule, now, offset) else 0)
    return shown, now + dt.timedelta(hours=hours)


def utc_offset(place: str, utc: dt.datetime | None = None) -> tuple[str, float, bool] | None:
    """(shown name, hours from UTC right now, whether summer time applies) for a known place, else None."""
    key = " ".join(place.lower().strip(" ?.!").split())
    key = key[4:] if key.startswith("the ") else key
    hit = _PLACES.get(key)
    if hit is None:
        return None
    offset, rule, shown = hit
    now = utc or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    summer = _dst(rule, now, offset)
    return shown, offset + (1 if summer else 0), summer


def utc_label(hours: float) -> str:
    """5.5 → "UTC+5:30", -3 → "UTC−3", 0 → "UTC+0"."""
    sign = "+" if hours >= 0 else "−"
    h = abs(hours)
    whole = int(h)
    mins = int(round((h - whole) * 60))
    return f"UTC{sign}{whole}" + (f":{mins:02d}" if mins else "")
