"""Questions about named things, answered from the fact bank.

A question is matched against patterns ("When was X born?", "What is the capital of X?",
"Who wrote X?" …). Each pattern names the properties that answer it, the kinds of entity it
is about, and the sentence the answer goes into. X is linked to an entity by its title, its
title without "(…)" or a redirect ("USA" → United States), preferring the expected kind of
entity, then exact titles, then popularity. Values are rendered for people: dates as
"14 March 1879", areas in km², rivers in km, several values joined with "and".

Only a clear case answers: the pattern matches the whole question, X links, and the entity has
the fact. Everything else returns ``None`` and the reading pipeline takes over. The data is a
snapshot (DBpedia, December 2022): answers about office holders or populations say so.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from engramm.kb.store import Entity, Fact, FactBank

PERSON = ("Person", "Scientist", "Writer", "Artist", "Politician", "Athlete", "Royalty", "Philosopher",
          "MusicalArtist", "Actor", "OfficeHolder", "Painter", "Monarch", "Saint", "Cleric", "Architect",
          "Engineer", "Astronaut", "Economist", "Journalist", "Model", "Poet", "Comedian", "Chef",
          "SoccerPlayer", "BasketballPlayer", "TennisPlayer", "BaseballPlayer", "President", "PrimeMinister",
          "Governor", "Mayor", "Senator", "Congressman", "MemberOfParliament", "Judge", "Criminal", "Noble",
          "Pope", "Presenter", "ScreenWriter", "Singer", "Composer", "Philosopher", "Religious", "Ambassador",
          "Cardinal", "Bishop", "FictionalCharacter", "Egyptologist", "Historian", "Linguist", "Psychologist",
          "Photographer", "Inventor", "Explorer", "Entomologist", "Medician", "Physician", "Racer")
PLACE = ("Country", "City", "Town", "Village", "Settlement", "Place", "PopulatedPlace", "AdministrativeRegion",
         "Region", "State", "Island", "Continent", "Mountain", "River", "Lake", "Sea", "Volcano", "Capital",
         "CityDistrict", "Province", "Territory", "Location", "Park", "Building", "Stadium", "Bridge", "Castle",
         "Museum", "Tower", "HistoricPlace", "ProtectedArea", "Airport", "University", "School")
WORK = ("Book", "Novel", "Film", "Album", "Single", "Song", "Painting", "Artwork", "Play", "Musical",
        "TelevisionShow", "VideoGame", "Software", "Work", "WrittenWork", "Poem", "Opera", "Comic",
        "ComicStrip", "Magazine", "Newspaper", "Website", "Artwork", "MusicalWork", "Sculpture")
ORG = ("Company", "Organisation", "Organization", "Band", "SportsTeam", "SoccerClub", "PoliticalParty",
       "University", "School", "Airline", "RecordLabel", "Publisher", "Non-ProfitOrganisation", "Broadcaster",
       "TelevisionStation", "Newspaper", "Museum", "Brewery", "Winery", "BusCompany", "Bank")
SNAPSHOT = "(as of my data)"
_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"]


@dataclass(frozen=True)
class Rule:
    patterns: tuple[str, ...]
    props: tuple[str, ...]
    kinds: tuple[str, ...]          # entity types preferred for X (empty: any)
    template: str                   # {E} entity, {v} value(s)
    render: str = "auto"            # auto | area | length | height | population | age
    snapshot: bool = False


def _r(patterns, props, kinds, template, render="auto", snapshot=False) -> Rule:
    return Rule(tuple(patterns), tuple(props.split()), tuple(kinds), template, render, snapshot)


E = r"(?P<e>.+?)"
RULES = [
    # people
    _r([rf"when (?:was|is) {E} born", rf"what (?:is|was) {E}'s (?:date of birth|birth ?date|birthday)",
        rf"what (?:is|was) the (?:date of birth|birth ?date|birthday) of {E}", rf"when is {E}'s birthday",
        rf"what year was {E} born( in)?", rf"in what year was {E} born"],
       "birthDate birthYear", PERSON, "{E} was born {v}."),
    _r([rf"where (?:was|is) {E} born", rf"what (?:is|was) {E}'s (?:birthplace|place of birth)",
        rf"what (?:is|was) the (?:birthplace|place of birth) of {E}", rf"what city was {E} born in",
        rf"in (?:what|which) (?:city|country|town) was {E} born"],
       "birthPlace", PERSON, "{E} was born in {v}."),
    _r([rf"when did {E} die", rf"when did {E} pass away", rf"what (?:is|was) {E}'s date of death",
        rf"when was {E}'s death", rf"what year did {E} die( in)?", rf"in what year did {E} die"],
       "deathDate deathYear", PERSON, "{E} died {v}."),
    _r([rf"where did {E} die", rf"what (?:is|was) {E}'s place of death", rf"where did {E} pass away"],
       "deathPlace", PERSON, "{E} died in {v}."),
    _r([rf"how did {E} die", rf"what (?:was|is) {E}'s cause of death", rf"what killed {E}"],
       "deathCause", PERSON, "{E} died of {v}."),
    _r([rf"where (?:is|was) {E} buried", rf"where (?:is|was) {E}'s grave", rf"where (?:is|was) {E} laid to rest"],
       "restingPlace", PERSON, "{E} is buried in {v}."),
    _r([rf"how old (?:is|was) {E}", rf"what (?:is|was) {E}'s age", rf"how old did {E} get",
        rf"(?:at )?what age did {E} die", rf"how old was {E} when (?:he|she|they) died"],
       "birthDate deathDate", PERSON, "{v}", render="age"),
    _r([rf"who (?:is|was|were) {E}'s (?:wife|husband|spouse|partner)", rf"who (?:is|was) {E} married to",
        rf"who did {E} marry", rf"who (?:is|was) the (?:wife|husband|spouse) of {E}"],
       "spouse", PERSON, "{E} was married to {v}."),
    _r([rf"who (?:is|was|were|are) {E}'s (?:parents|father|mother|dad|mom|mum)",
        rf"who (?:is|was|were|are) the (?:parents|father|mother) of {E}"],
       "parent", PERSON, "{E}'s parents: {v}."),
    _r([rf"who (?:is|was|were|are) {E}'s (?:children|kids|son|daughter|sons|daughters)",
        rf"(?:does|did) {E} have (?:any )?(?:children|kids)", rf"who (?:are|were) the children of {E}"],
       "child", PERSON, "{E}'s children include {v}."),
    _r([rf"what (?:is|was) {E}'s (?:job|occupation|profession)", rf"what (?:does|did) {E} do(?: for a living)?",
        rf"what (?:is|was) the (?:job|occupation|profession) of {E}"],
       "occupation", PERSON, "{E}: {v}."),
    _r([rf"what (?:is|was) {E}'s nationality", rf"what nationality (?:is|was) {E}",
        rf"where (?:is|was) {E} from"],
       "nationality citizenship birthPlace", PERSON, "{E}: {v}."),
    _r([rf"where did {E} (?:study|go to (?:university|college|school))", rf"what (?:university|college) did {E} "
        rf"(?:attend|go to)", rf"which university did {E} attend"],
       "almaMater education", PERSON, "{E} studied at {v}."),
    _r([rf"what (?:is|was) {E} (?:known|famous) for", rf"why (?:is|was) {E} famous"],
       "knownFor notableWork", PERSON, "{E} is known for {v}."),
    _r([rf"what (?:party|political party) (?:is|was|does|did) {E}(?: belong to| in| a member of| represent)?"],
       "party", PERSON, "{E}'s party: {v}."),
    _r([rf"what (?:team|club) (?:does|did) {E} play for", rf"(?:which|what) team (?:is|was) {E} (?:on|in)"],
       "team", PERSON, "{E} played for {v}."),
    _r([rf"what (?:instrument|instruments) (?:does|did) {E} play"], "instrument", PERSON, "{E} played {v}."),
    # places
    _r([rf"what(?:'s| is| was) the capital(?: city)? of {E}", rf"what(?:'s| is| was) {E}'s capital(?: city)?",
        rf"(?:which|what) city is the capital of {E}", rf"what is the capital city of {E}",
        rf"(?:name|tell me) the capital of {E}"],
       "capital", ("Country", "State", "AdministrativeRegion", "Region", "PopulatedPlace", "Place"),
       "The capital of {E} is {v}."),
    _r([rf"what(?:'s| is) the (?:largest|biggest) city (?:in|of) {E}"], "largestCity",
       ("Country", "State", "AdministrativeRegion", "Place"), "The largest city in {E} is {v}."),
    _r([rf"what (?:is|are) the (?:official |main )?languages? (?:of|in|spoken in) {E}",
        rf"what languages? (?:is|are|do (?:they|people)) (?:spoken|speak) in {E}", rf"what do people speak in {E}",
        rf"which languages? (?:is|are) spoken in {E}"],
       "officialLanguage language", ("Country", "State", "Place", "PopulatedPlace"), "In {E}, people speak {v}."),
    _r([rf"what(?:'s| is) the currency (?:of|in|used in) {E}", rf"what currency (?:does|do) {E} use",
        rf"what money (?:does|do) {E} use", rf"what is {E}'s currency"],
       "currency", ("Country", "State", "Place"), "The currency of {E} is the {v}."),
    _r([rf"what(?:'s| is) the population of {E}", rf"how many people live in {E}",
        rf"how many (?:inhabitants|residents|people) (?:does|do) {E} have", rf"how (?:big|large) is the population of {E}",
        rf"what is {E}'s population"],
       "populationTotal", PLACE, "{E} has a population of {v} " + SNAPSHOT + ".", render="population",
       snapshot=True),
    _r([rf"what(?:'s| is) the area of {E}", rf"how (?:big|large) is {E}", rf"what(?:'s| is) the size of {E}",
        rf"how many square (?:kilometres|kilometers|miles) is {E}"],
       "areaTotal", ("Country", "State", "City", "Island", "Lake", "Region", "AdministrativeRegion", "Place",
                     "PopulatedPlace", "Settlement", "Continent", "Sea"), "{E} covers {v}.", render="area"),
    _r([rf"how (?:tall|high) is {E}", rf"what(?:'s| is) the (?:height|elevation|altitude) of {E}",
        rf"how (?:tall|high) (?:was|are|were) {E}"],
       "elevation maximumElevation height", ("Mountain", "Volcano", "Building", "Tower", "Place", "Person",
                                             "Skyscraper", "Bridge"), "{E} is {v} high.", render="height"),
    _r([rf"how long is {E}", rf"what(?:'s| is) the length of {E}"],
       "length", ("River", "Bridge", "Canal", "Road", "Tunnel", "Place"), "{E} is {v} long.", render="length"),
    _r([rf"(?:what|which) country is {E} in", rf"in (?:what|which) country is {E}", rf"what country does {E} belong to"],
       "country", PLACE, "{E} is in {v}."),
    _r([rf"(?:what|which) continent is {E} (?:in|on)", rf"on (?:what|which) continent is {E}"],
       "continent", PLACE, "{E} is in {v}."),
    _r([rf"where is {E}(?: located)?", rf"where (?:can i find|is the location of) {E}"],
       "location locatedInArea country state city", PLACE + ORG, "{E} is in {v}."),
    _r([rf"(?:what|which) mountain range is {E} (?:in|part of)"], "mountainRange", ("Mountain", "Volcano"),
       "{E} is in the {v}."),
    _r([rf"where does (?:the )?{E} (?:river )?(?:flow into|end|empty)", rf"what(?:'s| is) the mouth of {E}"],
       "riverMouth", ("River",), "{E} flows into {v}."),
    _r([rf"who(?:'s| is) (?:the )?(?:current )?(?:president|head of state) of {E}", rf"who(?:'s| is) {E}'s president"],
       "headOfState president leader leaderName", ("Country", "Place"),
       "The head of state of {E} is {v} " + SNAPSHOT + ".", snapshot=True),
    _r([rf"who(?:'s| is) (?:the )?(?:current )?(?:prime minister|chancellor|premier|head of government) of {E}",
        rf"who(?:'s| is) {E}'s (?:prime minister|chancellor)"],
       "headOfGovernment primeMinister leader leaderName", ("Country", "State"),
       "The head of government of {E} is {v} " + SNAPSHOT + ".", snapshot=True),
    _r([rf"who(?:'s| is) (?:the )?(?:current )?(?:king|queen|monarch) of {E}"], "headOfState monarch", ("Country",),
       "The head of state of {E} is {v} " + SNAPSHOT + ".", snapshot=True),
    _r([rf"who(?:'s| is) (?:the )?(?:current )?mayor of {E}"], "headOfGovernment mayor leaderName leader",
       ("City", "Town", "Settlement", "Place"), "The mayor of {E} is {v} " + SNAPSHOT + ".", snapshot=True),
    _r([rf"who(?:'s| is) (?:the )?(?:current )?(?:leader|ruler) of {E}", rf"who (?:leads|runs|rules|governs) {E}"],
       "headOfGovernment headOfState leaderName leader president primeMinister monarch",
       ("Country", "State", "City", "Place"), "The leader of {E} is {v} " + SNAPSHOT + ".", snapshot=True),
    # events
    _r([rf"when did {E} (?:end|finish|stop)", rf"when was the end of {E}", rf"what year did {E} end"],
       "endDate", ("MilitaryConflict", "Event", None), "{E} ended {v}."),
    _r([rf"when did {E} (?:start|begin|break out)", rf"when was the (?:start|beginning) of {E}",
        rf"what year did {E} (?:start|begin)"],
       "startDate", ("MilitaryConflict", "Event", None), "{E} began {v}."),
    _r([rf"when (?:was|did) {E}(?: happen| take place)?", rf"when did {E} happen", rf"what year was {E}"],
       "date startDate", ("MilitaryConflict", "Event", None), "{E} took place {v}."),
    _r([rf"what(?:'s| is) the (?:national )?anthem of {E}", rf"what(?:'s| is) {E}'s (?:national )?anthem"],
       "anthem", ("Country",), "The anthem of {E} is {v}."),
    _r([rf"what(?:'s| is) the (?:national )?motto of {E}", rf"what(?:'s| is) {E}'s motto"],
       "motto", ("Country", "State", "Organisation", "University"), "The motto of {E} is “{v}”."),
    _r([rf"what time ?zone is {E} in", rf"what(?:'s| is) the time ?zone of {E}"], "timeZone", PLACE,
       "{E} is in {v}."),
    # works
    _r([rf"who wrote {E}", rf"who (?:is|was) the (?:author|writer) of {E}", rf"who (?:was|is) {E} (?:written|authored) by",
        rf"who (?:penned|authored) {E}"],
       "author writer", WORK, "{E} was written by {v}."),
    _r([rf"who directed {E}", rf"who (?:is|was) the director of {E}", rf"who (?:was|is) {E} directed by"],
       "director", ("Film", "TelevisionShow", "Play", "Musical", "Work"), "{E} was directed by {v}."),
    _r([rf"who (?:painted|drew|sculpted) {E}", rf"who (?:is|was) the (?:painter|artist) of {E}"],
       "artist author creator", ("Painting", "Artwork", "Sculpture", "Work"), "{E} was made by {v}."),
    _r([rf"who (?:composed|wrote the music (?:for|of)) {E}", rf"who (?:is|was) the composer of {E}"],
       "composer musicComposer", ("Film", "Opera", "Musical", "Work", "MusicalWork", "Song", "Album"),
       "{E} was composed by {v}."),
    _r([rf"who (?:sang|sings|performed|performs|recorded|released) {E}", rf"who (?:is|was) the (?:singer|artist) of {E}",
        rf"(?:which|what) (?:band|artist|singer) (?:sang|sings|performed|recorded|released) {E}"],
       "artist musicalArtist", ("Album", "Single", "Song", "MusicalWork"), "{E} is by {v}."),
    _r([rf"who (?:starred|stars|acted|plays|played) in {E}", rf"who (?:is|was) in the cast of {E}",
        rf"who (?:are|were) the (?:actors|stars) (?:in|of) {E}"],
       "starring", ("Film", "TelevisionShow"), "{E} stars {v}."),
    _r([rf"who produced {E}", rf"who (?:is|was) the producer of {E}"], "producer", WORK, "{E} was produced by {v}."),
    _r([rf"when (?:was|were|did) {E} (?:released|come out|published|first published|premiered?)",
        rf"what year (?:was|did) {E} (?:released|come out|published)", rf"when did {E} come out"],
       "releaseDate publicationDate", WORK, "{E} came out {v}."),
    _r([rf"who published {E}", rf"who (?:is|was) the publisher of {E}"], "publisher", WORK,
       "{E} was published by {v}."),
    _r([rf"who (?:developed|made|created) {E}", rf"who (?:is|was) the developer of {E}"],
       "developer creator author manufacturer", ("VideoGame", "Software", "Work", "Automobile", "Device",
                                                 "TelevisionShow", "FictionalCharacter"), "{E} was made by {v}."),
    _r([rf"(?:what|which) genre (?:is|was) {E}", rf"what(?:'s| is) the genre of {E}", rf"what kind of music (?:is|does) {E}"],
       "genre", WORK + ("Band", "MusicalArtist"), "{E}: {v}."),
    _r([rf"how many pages (?:does|did) {E} have", rf"how long is the book {E}"], "numberOfPages", ("Book", "Novel"),
       "{E} has {v} pages."),
    _r([rf"how many episodes (?:does|did) {E} have"], "numberOfEpisodes", ("TelevisionShow",), "{E} has {v} episodes."),
    _r([rf"how long is the (?:film|movie) {E}", rf"what(?:'s| is) the (?:runtime|running time|length) of {E}"],
       "runtime", ("Film",), "{E} runs {v}.", render="runtime"),
    # buildings, inventions, discoveries
    _r([rf"who (?:designed|built|architected) {E}", rf"who (?:is|was) the architect of {E}"],
       "architect designer builder", ("Building", "Bridge", "Tower", "Stadium", "Castle", "Place", "HistoricPlace",
                                      "Skyscraper", "Church", "Museum"), "{E} was designed by {v}."),
    _r([rf"when (?:was|were) {E} (?:built|completed|finished|opened|constructed)"],
       "completionDate openingDate", ("Building", "Bridge", "Tower", "Stadium", "Place", "Skyscraper", "Museum"),
       "{E} was completed {v}."),
    _r([rf"who invented {E}", rf"who (?:is|was) the inventor of {E}"],
       "inventor discoverer", (), "{E} was invented by {v}."),
    _r([rf"who discovered {E}", rf"who (?:is|was) the discoverer of {E}"],
       "inventor discoverer", (), "{E} was discovered by {v}."),
    # organisations
    _r([rf"who (?:founded|started|established|created|set up) {E}", rf"who (?:is|was|are|were) the founders? of {E}",
        rf"who (?:was|is) {E} founded by"],
       "founder foundedBy", ORG + ("Company",), "{E} was founded by {v}."),
    _r([rf"when (?:was|were) {E} (?:founded|established|formed|started|created|set up)",
        rf"what year (?:was|were) {E} (?:founded|established|formed)", rf"when did {E} (?:start|begin)"],
       "foundingDate foundingYear formationDate", ORG + PLACE, "{E} was founded {v}."),
    _r([rf"where (?:is|are) {E} (?:headquartered|based)", rf"where (?:is|are) the headquarters? of {E}",
        rf"where is {E}'s (?:headquarters|hq|head office)"],
       "headquarter location", ORG + ("Company",), "{E} is based in {v}."),
    _r([rf"who (?:is|was) the (?:ceo|boss|chief executive|head|chairman|president) of {E}", rf"who runs {E}"],
       "keyPerson", ORG + ("Company",), "Key people at {E} include {v} " + SNAPSHOT + ".", snapshot=True),
    _r([rf"how many (?:employees|people|staff) (?:does|do) {E} (?:have|employ)", rf"how many people work (?:at|for) {E}"],
       "numberOfEmployees", ORG + ("Company",), "{E} has about {v} employees " + SNAPSHOT + ".", snapshot=True),
    _r([rf"who owns {E}", rf"who (?:is|was) the owner of {E}", rf"what(?:'s| is) the parent company of {E}"],
       "owner parentCompany", ORG + ("Company",) + WORK, "{E} is owned by {v}."),
    _r([rf"what (?:does|did) {E} (?:make|produce|sell)", rf"what products? (?:does|did) {E} (?:make|sell)"],
       "product industry", ORG + ("Company",), "{E}: {v}."),
    _r([rf"who (?:are|were) the members of {E}", rf"who (?:is|was) in (?:the band )?{E}"],
       "bandMember formerBandMember", ("Band",), "{E}'s members include {v}."),
]
_COMPILED = [(rule, [re.compile(p, re.I) for p in rule.patterns]) for rule in RULES]


@dataclass
class KBAnswer:
    entity: Entity
    prop: str
    values: list[str]
    text: str
    evidence: str
    snapshot: bool


def _clean_question(q: str) -> str:
    q = q.strip().replace("’", "'")
    q = re.sub(r"[\s?!.]+$", "", q)
    q = re.sub(r"^(?:(?:and|so|but|ok|okay|well|hey|also|then)[,]?\s+)+", "", q, flags=re.I)
    q = re.sub(r"^(?:do you know|can you tell me|could you tell me|tell me|i wonder|any idea|please tell me)\s*,?\s*",
               "", q, flags=re.I)
    return re.sub(r"\s+", " ", q)


def _fmt_date(value: str, dtype: str) -> tuple[str, str]:
    """(phrase, bare): "1879-03-14" → ("on 14 March 1879", "14 March 1879"); "1879" → ("in 1879", …)."""
    m = re.fullmatch(r"(-?)(\d{1,4})-(\d{2})-(\d{2})", value)
    if m:
        neg, y, mo, d = m.groups()
        year = f"{int(y)} BC" if neg else str(int(y))
        if mo == "01" and d == "01" and dtype in ("gYear",):
            return f"in {year}", year
        bare = f"{int(d)} {_MONTHS[int(mo) - 1]} {year}"
        return f"on {bare}", bare
    m = re.fullmatch(r"(-?)(\d{1,4})(?:-(\d{2}))?", value)
    if m:
        neg, y, mo = m.groups()
        year = f"{int(y)} BC" if neg else str(int(y))
        if mo:
            bare = f"{_MONTHS[int(mo) - 1]} {year}"
            return f"in {bare}", bare
        return f"in {year}", year
    return value, value


def _num(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _fmt_number(x: float, digits: int = 0) -> str:
    if digits == 0 or float(x).is_integer():
        return f"{int(round(x)):,}"
    return f"{x:,.{digits}f}".rstrip("0").rstrip(".")


def _join(items: list[str]) -> str:
    items = list(dict.fromkeys(i for i in items if i))
    if len(items) <= 1:
        return items[0] if items else ""
    if len(items) > 4:
        items = items[:4]
        return ", ".join(items[:-1]) + " and " + items[-1] + " (among others)"
    return ", ".join(items[:-1]) + " and " + items[-1]


class KGQA:
    def __init__(self, bank: FactBank, today: dt.date | None = None):
        self.kb = bank
        self.today = today

    def _candidates(self, phrase: str, kinds: tuple[str, ...], props: tuple[str, ...]) -> list[Entity]:
        """Entities the phrase may name, best first: those that have an answering fact, of the
        expected kind, then by popularity (an exact title counts like ten times the popularity)."""
        tries = [phrase]
        if re.match(r"^the\s+", phrase, re.I):
            tries.append(re.sub(r"^the\s+", "", phrase, flags=re.I))
        else:
            tries.append("The " + phrase)
        seen: dict[int, tuple[Entity, int]] = {}
        for t in tries:
            for e, k in self.kb.link(t, limit=12):
                if e.id not in seen or k < seen[e.id][1]:
                    seen[e.id] = (e, k)
        scored = []
        for e, k in seen.values():
            has = bool(self.kb.facts(e.id, props))
            typed = not kinds or e.type in kinds
            weight = (e.popularity + 1) * (10 if k == 0 else 1)
            scored.append((has, typed, weight, -e.id, e))
        scored.sort(key=lambda x: x[:4], reverse=True)
        return [x[4] for x in scored if x[0] and (x[1] or x[4].type is None)]

    def _pick_entity(self, phrase: str, kinds: tuple[str, ...], props: tuple[str, ...] = ()) -> Entity | None:
        c = self._candidates(phrase, kinds, props)
        return c[0] if c else None

    def _value(self, f: Fact) -> str:
        if f.value_entity is not None or f.dtype == "entity":
            v = re.sub(r"\s*\([^)]*\)$", "", f.value)
            if f.prop in ("officialLanguage", "language"):
                v = re.sub(r" language$", "", v)
            if f.value_entity is not None:
                e = self.kb.entity(f.value_entity)
                if e is not None:
                    v = _with_article(v, e.type)
            return v
        return f.value.strip().rstrip(".") if f.dtype == "string" else f.value

    def answer(self, question: str) -> KBAnswer | None:
        q = _clean_question(question)
        for rule, rxs in _COMPILED:
            for rx in rxs:
                m = rx.fullmatch(q)
                if not m:
                    continue
                phrase = m.group("e").strip(" ,\"'“”")
                if not phrase or len(phrase.split()) > 8 or re.fullmatch(r"(?:i|me|my|you|he|she|it|they|this|that)",
                                                                        phrase, re.I):
                    continue
                ent = self._pick_entity(phrase, rule.kinds, rule.props)
                if ent is None:
                    continue
                facts = self.kb.facts(ent.id, rule.props)
                if not facts:
                    continue
                out = self._render(rule, ent, facts)
                if out is not None:
                    return out
        return None

    def _render(self, rule: Rule, ent: Entity, facts: list[Fact]) -> KBAnswer | None:
        by_prop: dict[str, list[Fact]] = {}
        for f in facts:
            by_prop.setdefault(f.prop, []).append(f)
        name = _with_article(ent.name, ent.type)
        if rule.render == "age":
            born = by_prop.get("birthDate")
            if not born:
                return None
            b = _parse_date(born[0].value)
            died = by_prop.get("deathDate")
            if b is None:
                return None
            if died:
                d = _parse_date(died[0].value)
                if d is None:
                    return None
                age = d.year - b.year - ((d.month, d.day) < (b.month, b.day))
                text = f"{name} died at the age of {age} ({_fmt_date(born[0].value, 'date')[1]} – " \
                       f"{_fmt_date(died[0].value, 'date')[1]})."
                vals = [str(age)]
            else:
                today = self.today or dt.date.today()
                age = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
                if age > 120:
                    return None
                text = f"{name} was born on {_fmt_date(born[0].value, 'date')[1]}, so {name} is {age} years old."
                vals = [str(age)]
            return KBAnswer(ent, "age", vals, text, f"{name}: born {born[0].value}", False)
        prop = next(p for p in rule.props if p in by_prop)
        fs = by_prop[prop]
        vals: list[str] = []
        if rule.render == "population":
            n = _num(fs[0].value)
            if n is None:
                return None
            vals = [_fmt_number(n)]
        elif rule.render == "area":
            n = _num(fs[0].value)
            if n is None:
                return None
            km2 = n / 1e6
            vals = [f"{_fmt_number(km2, 0 if km2 >= 100 else 1)} km² ({_fmt_number(km2 / 2.589988, 0 if km2 >= 100 else 1)}"
                    f" sq mi)"]
        elif rule.render == "length":
            n = _num(fs[0].value)
            if n is None:
                return None
            vals = [f"{_fmt_number(n / 1000, 0 if n >= 100000 else 1)} km" if n >= 1000 else f"{_fmt_number(n)} m"]
        elif rule.render == "height":
            n = _num(fs[0].value)
            if n is None:
                return None
            vals = [f"{_fmt_number(n, 0 if n >= 100 else 2)} m ({_fmt_number(n * 3.28084)} ft)"]
        elif rule.render == "runtime":
            n = _num(fs[0].value)
            if n is None:
                return None
            vals = [f"{round(n / 60)} minutes" if n > 400 else f"{round(n)} minutes"]
        else:
            phrase_dates = bool(re.search(r"(?:born|died|came out|founded|completed|ended|began|took place) \{v\}",
                                          rule.template))
            for f in fs:
                if f.dtype in ("date", "gYear", "gYearMonth"):
                    phrase, bare = _fmt_date(f.value, f.dtype)
                    vals.append(phrase if phrase_dates else bare)
                else:
                    v = self._value(f)
                    if f.dtype in ("nonNegativeInteger", "integer", "positiveInteger") and _num(v) is not None:
                        v = _fmt_number(float(v))
                    vals.append(v)
            if phrase_dates and len(vals) > 1:
                vals = vals[:1]                   # one date (birthDate before birthYear)
        vals = [v for v in vals if v]
        own = [v for v in vals if ent.name.lower() in v.lower() and v.lower() != ent.name.lower()]
        if own and len(own) < len(vals):
            vals = [v for v in vals if v not in own]
        if not vals:
            return None
        text = rule.template.replace("{E}", name).replace("{v}", _join(vals))
        text = text[:1].upper() + text[1:]
        evidence = f"{ent.title} — {prop}: " + "; ".join(f.value for f in fs[:4])
        return KBAnswer(ent, prop, vals, text, evidence, rule.snapshot)


_THE_TYPES = frozenset(("River", "Sea", "Ocean", "Desert", "MountainRange", "Canal", "Strait", "Building", "Tower",
                        "Bridge", "Skyscraper", "Painting", "Artwork", "Castle", "Museum", "Stadium", "Monument",
                        "HistoricBuilding", "Delta", "Bay", "Gulf", "Channel", "Lighthouse", "Dam", "Palace"))
_THE_NAMES = re.compile(r"^(?:united\b|czech republic|netherlands|philippines|bahamas|gambia|maldives|"
                        r"dominican republic|central african republic|democratic republic|republic of|kingdom of|"
                        r"soviet union|european union|marshall islands|solomon islands|comoros|seychelles|"
                        r"vatican city|holy see)", re.I)


def _with_article(name: str, etype: str | None) -> str:
    """"Nile" → "the Nile", "United States" → "the United States", "Eiffel Tower" → "the Eiffel Tower"."""
    if re.match(r"^(?:the|a|an|lake|mount|mt\.?|river|saint|st\.?)\b", name, re.I):
        return name
    if (etype in _THE_TYPES and not re.match(r"^[A-Z][a-z]+'s\b", name)) or (etype == "Country" and
                                                                         _THE_NAMES.match(name)):
        return "the " + name
    return name


def _parse_date(v: str) -> dt.date | None:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if not m:
        return None
    try:
        return dt.date(*map(int, m.groups()))
    except ValueError:
        return None
