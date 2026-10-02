"""Everyday requests for the dialog layer (Chat v3.1), all by rules and authored lists
(data/conv/daily.yaml), no neural network:

* recommendations — "what should I eat tonight?", "recommend a sci-fi book", "I'm bored, what
  can I do?" — three suggestions at a time, never the same ones twice in a conversation, with
  "tell me about the second one" afterwards;
* advice in context — "what should I do?" right after "my boss yelled at me" gets advice about
  people at work, after "I failed my exam" advice about setbacks;
* decisions — "should I stay in or go out?", "pizza or pasta?";
* games — a quiz and riddles, with answers checked (a typo or a missing article still counts);
* words — "how do you spell necessary?", "what rhymes with moon?";
* opinions about the current topic — "is it good?" after talking about a film or a book;
* named things in what you say — "I watched Inception yesterday" → a fact about the film and a
  question back.

Everything is deterministic (SHAKE-256 of the conversation id and a counter), like the rest of
the conversation layer.
"""

from __future__ import annotations

import hashlib
import re

from engramm.chat.bot import Reply
from engramm.chat.smart import swap_person

# ---------------------------------------------------------------------------
# recognising requests
# ---------------------------------------------------------------------------

_LEAD = r"^(?:(?:hey|hi|ok|okay|so|well|um+|hmm+|engramm|please|pls)[, ]+)*(?:(?:can|could|would|will) you |please |pls )*"
_REC = [
    ("food", re.compile(_LEAD + r"(?:i'm hungry[, ]+)?(?:what (?:should|can|could|do|shall) (?:i|we) (?:eat|cook|make|have)"
                        r"(?: for (?:dinner|lunch|breakfast|supper|tonight|today))?(?: tonight| today)?|what(?:'s| is| should be) "
                        r"for (?:dinner|lunch|supper)|(?:give me |suggest |any )?(?:dinner|lunch|supper|meal|recipe|food|cooking) "
                        r"(?:ideas?|suggestions?|inspiration)|i (?:don't|do not|can't|cannot) (?:know|decide) what to (?:eat|cook|make)"
                        r"|(?:suggest|recommend)(?: me)? (?:a |an |some )?(?:meal|dinner|lunch|recipe|dish|food)|what to (?:eat|cook)"
                        r"(?: tonight| today)?)$")),
    ("book", re.compile(_LEAD + r"(?:(?:recommend|suggest)(?: me)? (?:a |an |some |any |good |great |nice )*(?:(?P<g>[a-z-]+(?: [a-z-]+)?) )?"
                        r"(?:book|books|novel|novels|read)|(?:any |good |some )?(?:(?P<g2>[a-z-]+) )?(?:book|reading|novel) "
                        r"(?:recommendations?|suggestions?|ideas?|tips?)|what (?:book|books|novel) should i read(?: next)?|"
                        r"what should i read(?: next)?|(?:give me |i need |i want )?a good book(?: to read)?)$")),
    ("movie", re.compile(_LEAD + r"(?:(?:recommend|suggest)(?: me)? (?:a |an |some |any |good |great |nice )*(?:(?P<g>[a-z-]+(?: [a-z-]+)?) )?"
                         r"(?:movie|movies|film|films)|(?:any |good |some )?(?:(?P<g2>[a-z-]+) )?(?:movie|film) "
                         r"(?:recommendations?|suggestions?|ideas?|tips?)|what (?:movie|film|movies|films) should (?:i|we) watch"
                         r"(?: tonight| today)?|what should (?:i|we) watch(?: tonight| today)?|(?:a )?good (?:movie|film) to watch)$")),
    ("series", re.compile(_LEAD + r"(?:(?:recommend|suggest)(?: me)? (?:a |an |some |any |good |great |nice )*(?:(?P<g>[a-z-]+) )?"
                          r"(?:show|shows|series|tv show|tv shows|tv series)|(?:any |good |some )?(?:show|series|tv) "
                          r"(?:recommendations?|suggestions?|ideas?)|what (?:show|series|tv show) should (?:i|we) watch|"
                          r"what should i binge(?: watch)?|(?:a )?good (?:show|series) to (?:watch|binge))$")),
    ("music", re.compile(_LEAD + r"(?:(?:recommend|suggest)(?: me)? (?:a |an |some |any |good |great |nice |new )*(?:(?P<g>[a-z-]+) )?"
                         r"(?:music|album|albums|song|songs|band|bands|artist|artists)|(?:any |good |some )?music "
                         r"(?:recommendations?|suggestions?|ideas?)|what (?:music|songs?|albums?) should i listen to|"
                         r"what should i listen to)$")),
    ("game", re.compile(_LEAD + r"(?:(?:recommend|suggest)(?: me)? (?:a |an |some |any |good |fun )*(?:(?P<g>board|video|card|party) )?"
                        r"(?:game|games)|(?:any |good |some )?(?:(?P<g2>board|video) )?game (?:recommendations?|suggestions?|ideas?)|"
                        r"what (?:game|games) should (?:i|we) play)$")),
    ("activity", re.compile(_LEAD + r"(?:(?:i'm|i am|im) (?:so |really )?bored[,.! ]+)?(?:what (?:can|should|could|shall) "
                            r"(?:i|we) do(?: today| tonight| now| this weekend| at the weekend| on the weekend| when i'm bored)?|"
                            r"(?:give me |suggest |any )?(?:ideas|things) (?:for|to do)(?: today| tonight| this weekend| when i'm bored)?|"
                            r"suggest something (?:to do|fun)|(?:any )?(?:weekend|activity) ideas|what's something fun to do|"
                            r"something to do)$")),
    ("gift", re.compile(_LEAD + r"(?:(?:give me |any |some )?(?:gift|present|birthday present|christmas present) "
                        r"(?:ideas?|suggestions?)|what (?:should|can) i (?:get|buy|give)(?: for)?(?: my| a)? (?P<who>[a-z ]+?)"
                        r"(?: for (?:their |his |her )?(?:birthday|christmas|anniversary))?|(?:recommend|suggest) a (?:gift|present)"
                        r"(?: for (?:my |a )?(?P<who2>[a-z ]+))?)$")),
    ("travel", re.compile(_LEAD + r"(?:where should (?:i|we) (?:travel|go|go on holiday|go on vacation|visit)(?: next)?|"
                          r"what should (?:i|we) (?:visit|see)(?: next)?|where (?:to|should i) go next|"
                          r"(?:any |some |give me )?(?:travel|holiday|vacation|trip) (?:ideas|destinations|recommendations|"
                          r"suggestions)|(?:recommend|suggest)(?: me)? (?:a |some )?(?:city|cities|country|countries|place|places|"
                          r"destination|destinations) to visit|where to (?:travel|go on holiday))$")),
    ("hobby", re.compile(_LEAD + r"(?:(?:any |some |give me )?(?:new )?hobby (?:ideas|suggestions)|what hobby should i "
                         r"(?:try|start|pick up|take up)|(?:recommend|suggest)(?: me)? (?:a |some )?(?:new )?hobb(?:y|ies)|"
                         r"i (?:need|want) a (?:new )?hobby)$")),
    ("sleep", re.compile(_LEAD + r"(?:how (?:can|do|should) i (?:sleep better|fall asleep(?: faster)?|get better sleep)|"
                         r"(?:any |some |give me )?(?:sleep|sleeping) (?:tips|advice)|help me (?:sleep|fall asleep)|"
                         r"tips (?:for|to) (?:sleep better|fall asleep|sleeping))$")),
    ("study", re.compile(_LEAD + r"(?:(?:any |some |give me )?(?:study|studying|learning|exam) (?:tips|advice|hacks)|"
                         r"how (?:can|do|should) i (?:study|learn)(?: better| more effectively| faster| for (?:an?|my|the) "
                         r"(?:exam|test))?|tips (?:for|on) (?:studying|learning|exams?))$")),
    ("focus", re.compile(_LEAD + r"(?:(?:any |some |give me )?(?:productivity|focus|concentration) (?:tips|advice|hacks)|"
                         r"how (?:can|do) i (?:focus|concentrate|stop procrastinating|be more productive|get more done)|"
                         r"i (?:can't|cannot) (?:focus|concentrate)|i keep procrastinating|help me (?:focus|be productive))$")),
    ("exercise", re.compile(_LEAD + r"(?:(?:any |some |give me )?(?:exercise|workout|fitness|training) (?:ideas|tips|advice)|"
                            r"how (?:can|do) i (?:get fit|exercise more|start exercising|get in shape)|"
                            r"(?:recommend|suggest)(?: me)? (?:a |an |some )?(?:exercise|exercises|workout))$")),
    ("petname", re.compile(_LEAD + r"(?:(?:give me |any |some )?(?:names|name ideas) for (?:my |a )?(?:new )?(?:dog|cat|puppy|"
                           r"kitten|pet|hamster|rabbit|bunny|bird|fish)|what should i (?:name|call) my (?:new )?(?:dog|cat|"
                           r"puppy|kitten|pet|hamster|rabbit|bunny|bird|fish)|(?:good |cute )?pet names?)$")),
]
_ACTIVITY = next(rx for kind, rx in _REC if kind == "activity")
_GENRES = {"sci-fi": "scifi", "scifi": "scifi", "science fiction": "scifi", "science-fiction": "scifi",
           "funny": "comedy", "comedy": "comedy", "comedies": "comedy", "classic": "classic", "classics": "classic",
           "fantasy": "fantasy", "non-fiction": "nonfiction", "nonfiction": "nonfiction", "non fiction": "nonfiction",
           "history": "history", "historical": "history", "animated": "animation", "animation": "animation",
           "romantic": "romance", "romance": "romance", "thriller": "thriller", "exciting": "thriller",
           "scary": "thriller", "crime": "crime", "documentary": "documentary", "fiction": "fiction",
           "dystopian": "dystopia", "family": "family", "kids": "family", "rock": "rock", "jazz": "jazz", "pop": "pop",
           "electronic": "electronic", "board": "board", "video": "video", "drama": "drama", "mystery": "mystery",
           "psychology": "psychology", "science": "science", "nature": "nature",
           "warm": "warm", "sunny": "warm", "hot": "warm", "tropical": "warm", "beach": "beach", "beaches": "beach",
           "cold": "cold", "snowy": "cold", "cheap": "cheap", "affordable": "cheap", "budget": "cheap",
           "city": "city", "cities": "city", "cultural": "culture", "culture": "culture", "hilarious": "comedy",
           "light": "comedy", "lighthearted": "comedy", "spooky": "thriller", "horror": "thriller", "sad": "drama",
           "romcom": "romance"}
_ADVICE = re.compile(_LEAD + r"(?:so )?(?:what (?:should|can|could|do you think|would you suggest|would you recommend) i "
                     r"(?:do|say|try)(?: (?:about|with) (?P<about>.+?))?(?: now| then| next)?|what would you do(?: in my (?:place|shoes))?|"
                     r"i (?:don't|do not|dont) know (?:if|whether|what) (?:i should|to) (?:say|do|tell|talk)\b"
                     r"(?! (?:with myself|today|now|rn|right now|tonight)$).*|"
                     r"(?:i'm|i am|im) not sure (?:if|whether|what) (?:i should|to) (?:say|do|tell|talk)\b"
                     r"(?! (?:with myself|today|now|rn|right now|tonight)$).*|"
                     r"should i (?:say something|say anything|tell (?:him|her|them|my \w+)|talk to (?:him|her|them|my \w+)|"
                     r"confront (?:him|her|them)|speak up)\b.*|"
                     r"(?:any |some |got any |do you have any )?(?:advice|tips|suggestions)(?: for me)?(?: (?:on|about|for) (?P<about2>.+))?|"
                     r"give me (?:some |an? )?(?:advice|tip|tips)(?: (?:on|about|for) (?P<about3>.+))?|"
                     r"how (?:do|should|can|does) (?:i|people|you|one|someone|we) (?:deal|cope) with (?P<about4>.+)|help me (?:with this|out|deal with (?P<about5>.+))|"
                     r"what (?:now|next)|how do i handle (?P<about6>.+)|i (?:don't|do not|dont) know what to do(?! (?:with myself|today|now|rn|right now|tonight))|i'm not sure what to do|"
                     r"what am i supposed to do|i need (?:some )?advice|(?:so )?what do you think(?: about (?:it|that))?|"
                     r"should i(?: do it)?|is that a good idea|what do you think i should (?:do|say)"
                     r"(?: (?:about|with) (?P<about7>.+?))?|what do i do(?: now| about (?P<about8>.+))?)$")
_DECIDE = [re.compile(_LEAD + r"(?:should (?:i|we)|do (?:i|we)|would you|what's better[,:]?|which is better[,:]?|"
                      r"help me (?:decide|choose|pick)[,:]?) (?P<a>[^?]{2,40}?) or (?P<b>[^?]{2,40}?)$"),
           re.compile(_LEAD + r"(?:help me )?(?:decide|choose|pick) between (?P<a>[^?]{2,40}?) and (?P<b>[^?]{2,40}?)$"),
           re.compile(r"^(?P<a>[a-z][a-z' ]{1,20}) or (?P<b>[a-z][a-z' ]{1,20})$")]
_QUIZ = re.compile(_LEAD + r"(?:let's |let us |can we |wanna |want to |i want to |i'd like to )?(?:play |do |have |take )?"
                   r"(?:a |some )?(?:quiz|trivia|pub quiz)(?: me| game| question| questions)?|quiz me|test (?:me|my knowledge)|"
                   r"ask me (?:a |some )?(?:trivia|quiz|general knowledge) questions?$")
_RIDDLE = re.compile(_LEAD + r"(?:tell me |give me |do you (?:know|have) |got |ask me )?(?:a |another |any |some )?riddles?"
                     r"(?: for me)?|riddle me(?: this)?$")
_SPELL = re.compile(_LEAD + r"(?:how (?:do you|do i|does one|to) spell|spell|what's the (?:correct |right )?spelling of|"
                    r"how is (?P<w2>[a-z']+) spelled) ?(?P<w>[a-z']+)?$")
_RHYME = re.compile(_LEAD + r"(?:what (?:rhymes|words rhyme|word rhymes|can rhyme) with|(?:give me )?(?:a |some )?rhymes? (?:for|with)|"
                    r"words? that rhymes? with) (?P<w>[a-z']+)$")
_OPINION_IT = re.compile(_LEAD + r"(?:is (?:it|that|this|that one|this one) (?:any )?(?:good|worth (?:it|reading|watching|seeing|"
                         r"visiting|listening to|a try))|(?:should|would) (?:i|you) (?:read|watch|see|visit|try|play|listen to) "
                         r"(?:it|that|this)|(?:do|did) you like (?:it|that|this)|what do you think (?:of|about) (?:it|that|this)|"
                         r"is (?:it|that) worth it|any good|how good is (?:it|that))$")
_ORDINAL = {"first": 0, "1st": 0, "one": 0, "second": 1, "2nd": 1, "two": 1, "third": 2, "3rd": 2, "three": 2, "last": -1}
_LIST_PICK = re.compile(_LEAD + r"(?:tell me (?:more )?about|more about|what about|what's|what is|i like|i'll take|let's go with|"
                        r"i choose|i pick|sounds good[,:]?|ooh|oh)? ?(?:the )?(?P<n>first|1st|second|2nd|third|3rd|last) "
                        r"(?:one|option|idea|suggestion|book|film|movie|show|album|game|place)?$")
_GAME_STOP = re.compile(r"^(?:stop|quit|enough|end|no more|i'm done|im done|that's enough|let's stop|exit|cancel)\b")
_GIVE_UP = re.compile(r"^(?:i give up|give up|i don't know|i dont know|idk|no idea|tell me|what is it|what's the answer|"
                      r"pass|skip|reveal|show me|i have no idea|dunno|no clue)\b")
_HINT = re.compile(r"^(?:hint|give me a hint|a hint|clue|give me a clue|can i have a hint)\b")
_ARTICLE = re.compile(r"^(?:a|an|the|it's|it is|is it|maybe|i think|i guess|um+|uh+)\s+")


def _key(*parts) -> bytes:
    return hashlib.shake_256("\x00".join(str(p) for p in parts).encode()).digest(8)


def _order(n: int, *seed) -> list[int]:
    return sorted(range(n), key=lambda i: _key(*seed, i))


def _norm_answer(s: str) -> str:
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = " ".join(s.split())
    for _ in range(3):
        s = _ARTICLE.sub("", s)
    return s.strip()


def _edit1(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) <= 1 or (len(diff) == 2 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    if len(a) > len(b):
        a, b = b, a
    for i in range(len(b)):
        if a == b[:i] + b[i + 1:]:
            return True
    return False


def answer_matches(given: str, answer: str, also: str = "") -> bool:
    g = _norm_answer(given)
    if not g:
        return False
    options = [_norm_answer(answer)] + [_norm_answer(x) for x in also.split("|") if x.strip()]
    for o in options:
        if not o:
            continue
        if g == o or (len(o) >= 4 and (f" {o} " in f" {g} ")):
            return True
        if len(o) >= 5 and _edit1(g, o):
            return True
        if len(o) >= 5 and any(_edit1(w, o) for w in g.split()):
            return True
    return False


def _join_list(xs: list[str]) -> str:
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + " or " + xs[-1]


_GENRE_WORDS = {"scifi": "science-fiction", "fantasy": "fantasy", "comedy": "comedy", "drama": "drama",
                "thriller": "thriller", "classic": "classic", "romance": "romance", "crime": "crime",
                "animation": "animated", "horror": "horror", "dystopia": "dystopian", "mystery": "mystery"}
_ERRANDS = frozenset("gym doctor dentist shop store office park beach movies cinema supermarket bank pub bar "
                     "library mall hospital".split())
_KIND_NOUN = {"book": "book", "books": "book", "movie": "film", "movies": "film", "film": "film", "show": "series",
              "shows": "series", "series": "series", "music": "pick", "game": "game", "games": "game",
              "podcast": "podcast", "podcasts": "podcast"}


_REC_NOUN = {"music": "music", "song": "music", "songs": "music", "album": "music", "albums": "music",
             "band": "music", "bands": "music", "artist": "music", "artists": "music", "book": "book",
             "books": "book", "novel": "book", "novels": "book", "read": "book", "movie": "movie", "movies": "movie",
             "film": "movie", "films": "movie", "show": "series", "shows": "series", "series": "series",
             "game": "game", "games": "game", "gift": "gift", "gifts": "gift", "present": "gift",
             "presents": "gift", "place": "travel", "places": "travel", "destination": "travel",
             "destinations": "travel", "hobby": "hobby", "hobbies": "hobby", "dish": "food", "recipe": "food",
             "recipes": "food", "meal": "food", "food": "food"}
_REC_FILLER = frozenset("a an some any good great nice new kind type sort of kinds types to the few".split())
_REC_ANY = re.compile(
    _LEAD + r"(?:what|which)(?: kind| kinds| type| types| sort)?(?: of)? (?P<n>[a-z\- ]{2,40}?) (?:do|would|can|could) you "
    r"(?:recommend|suggest)(?: (?:to )?me)?(?: to (?:listen to|read|watch|play))?$|"
    r"(?:recommend|suggest)(?: (?:to )?me)? (?:a |an |some |any )?(?:good |great |nice |new )?(?P<n2>[a-z\- ]{2,40}?)"
    r"(?: to (?:listen to|read|watch|play))?$|"
    r"(?:any|got any|do you have any|give me some|i need some|i want some) (?:good )?(?P<n3>[a-z\- ]{2,40}?) "
    r"(?:recommendations?|suggestions?|recs|ideas)$")
_REC_VERB = re.compile(_LEAD + r"what (?:should|can|could|do you think) i (?P<v>read|watch|listen to|play)(?: next| now| tonight)?$")
_REC_VERB_KIND = {"read": "book", "watch": "movie", "listen to": "music", "play": "game"}


_OPINION_ABOUT = re.compile(
    _LEAD + r"(?:what do you think (?:about|of)|how do you feel about|what are your thoughts on|thoughts on|"
    r"what(?:'s| is) your (?:opinion|take|view) (?:on|of|about)|your opinion on|do you have an opinion on|"
    r"how do you like|is (?P<y>.+?) (?:good|bad|overrated|underrated) in your opinion|"
    r"(?:are you|r u) (?:a fan of|into)) (?P<x>.+?)$")


class Everyday:
    def __init__(self, assistant):
        self.a = assistant
        self.d = assistant.bank.daily

    # -- picking ------------------------------------------------------------------------------

    def pick(self, st, key: str, options: list[str], **fmt) -> str:
        return self.a._pick(st, f"daily:{key}", options, **fmt)

    # -- recommendations ----------------------------------------------------------------------

    def _recommend_kind(self, norm: str) -> tuple[str, str | None, str | None] | None:
        for kind, rx in _REC:
            m = rx.match(norm)
            if m:
                g = None
                gd = m.groupdict()
                for k in ("g", "g2"):
                    if gd.get(k):
                        g = gd[k]
                who = gd.get("who") or gd.get("who2")
                return kind, g, who
        # the general forms: "what kind of music do you recommend", "can you recommend some good books",
        # "any podcast recommendations?", "what should I read next"
        m = _REC_ANY.match(norm)
        if m:
            noun = (m.group("n") or m.group("n2") or m.group("n3") or "").strip()
            words_ = noun.split()
            for w in reversed(words_):
                kind = _REC_NOUN.get(w)
                if kind:
                    genre = " ".join(x for x in words_ if x != w and x not in _REC_FILLER) or None
                    return kind, genre, None
        m = _REC_VERB.match(norm)
        if m:
            return _REC_VERB_KIND[m.group("v")], None, None
        return None

    def recommend(self, st, msg: str, kind: str, genre: str | None = None, more: bool = False,
                  lang: str = "en") -> Reply:
        spec = self.d["recommend"][kind]
        de = (self.a.bank.de or {}).get("daily", {}).get("rec", {}) if lang == "de" else None
        items = spec["items"]
        tag = _GENRES.get((genre or "").strip()) if genre else None
        pool = list(range(len(items)))
        if tag:
            tagged = [i for i in pool if tag in (items[i].get("tags", "") if isinstance(items[i], dict) else "").split()]
            if tagged:
                pool = tagged
        order = [pool[i] for i in _order(len(pool), st.conversation, "rec", kind, tag)]
        seen = set(st.uses.get(f"rec_seen:{kind}", []))
        fresh = [i for i in order if i not in seen]
        if not fresh:
            seen, fresh = set(), order               # all shown: start again from the top
        chosen = fresh[:3]
        st.uses[f"rec_seen:{kind}"] = sorted(seen | set(chosen))
        shown = len(seen)
        texts, titles = [], []
        for i in chosen:
            it = items[i]
            if isinstance(it, dict):
                text = it.get("de") if de is not None and it.get("de") else it["x"]
                if de is not None and not it.get("de"):
                    text = text.replace(" by ", " von ").replace(" from Pixar", " von Pixar").replace(
                        ", a German mystery series", ", eine deutsche Mystery-Serie").replace(
                        " (the US version)", " (die US-Version)").replace(" with David Attenborough", " mit David Attenborough")
                texts.append(text)
                titles.append(it.get("title"))
            else:
                texts.append(it)
                titles.append(None)
        st.last_list = {"kind": kind, "titles": titles, "texts": texts, "turn": st.turn, "genre": tag}
        st.last_action = {"kind": f"rec:{kind}", "genre": genre, "turn": st.turn, "lang": lang}
        intro = spec.get("intro")
        if isinstance(intro, list):                   # several openings: never the same one twice in a row
            intro = self.pick(st, f"rec_intro:{kind}", intro)
        intro = intro or self.pick(st, "rec_intro", self.d["recommend"]["intro"])
        if more:
            intro = "A few more:"
        body = "\n".join(f"• {t[:1].upper() + t[1:]}" for t in texts)
        if any(titles) and not more:
            outro = self.pick(st, "rec_outro", self.d["recommend"]["outro"])
        else:
            outro = spec.get("outro") if not more else "Want even more?"
        if de is not None:
            k = de.get(kind, {})
            intro = de["more"] if more else k.get("intro", de["intro"])
            outro = de["outro"] if any(titles) and not more else k.get("outro", de["outro"])
        if len(fresh) > len(chosen):
            st.offer = {"kind": "ideas", "rec": kind, "genre": genre, "turn": st.turn}
        return Reply(msg, "smalltalk", f"{intro}\n\n{body}\n\n{outro}", via="everyday")

    def pick_from_list(self, st, msg: str, norm: str) -> Reply | None:
        ll = getattr(st, "last_list", None)
        if not ll or st.turn - ll.get("turn", -99) > 4:
            return None
        m = _LIST_PICK.match(norm)
        idx = None
        if m:
            idx = _ORDINAL.get(m.group("n"))
        else:
            # "tell me about Dune" when Dune was in the list: the about path handles it by itself
            return None
        titles = ll.get("titles") or []
        texts = ll.get("texts") or []
        if idx is None or not texts:
            return None
        i = idx if idx >= 0 else len(texts) - 1
        if i >= len(texts):
            return None
        title = titles[i] if i < len(titles) else None
        if title:
            bare = re.sub(r"\s*\([^)]*\)$", "", title)
            for cand in dict.fromkeys((title, bare)):
                found = self.a.about.find(cand)
                if found is not None:
                    return self.a._about_reply(st, msg, found, "tell")
            shelf = self.a._atlas_about(st, msg, title)          # the shelf, when it is switched on
            if shelf is not None:
                return shelf
            fact = self._list_fact(bare, ll.get("kind"))
            if fact:
                st.topic = {"title": title, "name": bare, "turn": st.turn}
                return Reply(msg, "smalltalk", self.pick(st, "rec:pick_fact", self.d["recommend"]["pick_fact"],
                                                         x=texts[i], fact=fact), via="everyday")
        genre = _GENRE_WORDS.get(ll.get("genre") or "", "")
        return Reply(msg, "smalltalk", self.pick(st, "rec:pick_plain", self.d["recommend"]["pick_plain"],
                                                 x=texts[i], noun=(genre + " " if genre else "") + _KIND_NOUN.get(
                                                     ll.get("kind") or "", "pick")), via="everyday")

    def _list_fact(self, name: str, kind: str | None) -> str | None:
        """One fact about a recommended work from the fact bank (genre, author, director …)."""
        kg = self.a.kgqa
        if kg is None:
            return None
        for ent, k in kg.kb.link(name, limit=3):
            group = self._ENTITY_KIND.get(ent.type or "")
            if group is None:
                continue
            fact = self._entity_fact(ent, group)
            if fact:
                return fact
        return None

    # -- advice -------------------------------------------------------------------------------

    def _advice_group(self, text: str, exp: dict | None) -> str:
        t = (text or "").lower()
        if re.search(r"\b(?:died|passed away|funeral|grief|grieving|lost my (?:mom|mum|dad|mother|father|grandma|"
                     r"grandpa|grandmother|grandfather|brother|sister|friend|dog|cat|pet|husband|wife|partner))\b", t):
            return "grief"
        if re.search(r"\b(?:broke up|break ?up|breaking up|dumped|divorce|divorced|cheated|left me|my ex)\b", t):
            return "heartbreak"
        if re.search(r"\b(?:boss|manager|colleague|coworker|co-worker|supervisor|team|client|customer|hr|office)\b", t):
            return "work_people"
        if re.search(r"\b(?:teacher|friend|friends|mom|mum|dad|mother|father|parents|brother|sister|partner|boyfriend|"
                     r"girlfriend|husband|wife|neighbou?r|roommate|flatmate|him|her|them|people|family)\b", t):
            return "people"
        if re.search(r"\b(?:quit|quitting|resign|resigning|leave my job|leaving my job|new job|change jobs?|"
                     r"switch(?:ing)? jobs?|career)\b", t):
            return "career"
        if re.search(r"\b(?:failed|fail|flunked|rejected|rejection|lost|fired|didn't get|did not get|mistake|messed up)\b", t):
            return "failure"
        if re.search(r"\b(?:stress|stressed|stressful|anxious|anxiety|worried|nervous|overwhelmed|overwhelming|panic|"
                     r"pressure|deadline|deadlines|too much)\b", t):
            return "stress"
        if re.search(r"\b(?:tired|exhausted|exhausting|long day|long week|no sleep|sleep|drained|burnt out|burned out)\b", t):
            return "tired"
        if re.search(r"\b(?:sad|lonely|down|depressed|unhappy|miserable|cry|crying|cried|heartbroken)\b", t):
            return "sad"
        if exp and exp.get("person"):
            return "people"
        return "generic"

    def advice(self, st, msg: str, about: str | None) -> Reply:
        exp = st.last_exp if st.last_exp and st.turn - st.last_exp.get("turn", -99) <= 4 else None
        context = about or (exp or {}).get("text")
        if not context and not exp:
            return Reply(msg, "smalltalk", self.pick(st, "advice_none", self.d["advice"]["none"]), via="everyday")
        group = self._advice_group(context or "", exp)
        text = self.pick(st, f"advice:{group}", self.d["advice"][group])
        return Reply(msg, "smalltalk", text, via="everyday")

    # -- decisions ----------------------------------------------------------------------------

    def decide(self, st, msg: str, a: str, b: str) -> Reply | None:
        a, b = a.strip(" ,"), b.strip(" ,")
        if not a or not b or a == b or len(a.split()) > 7 or len(b.split()) > 7:
            return None
        a, b = swap_person(a), swap_person(b)
        x = (a, b)[int.from_bytes(_key(st.conversation, "decide", a, b), "little") % 2]
        return Reply(msg, "smalltalk", self.pick(st, "decide", self.d["decide"], x=x), via="everyday")

    # -- games --------------------------------------------------------------------------------

    def _game_item(self, st, game: str) -> tuple[int, dict]:
        items = self.d[game]["items"]
        n = st.uses.get(f"{game}:n", 0)
        st.uses[f"{game}:n"] = n + 1
        order = _order(len(items), st.conversation, game)
        i = order[n % len(items)]
        return i, items[i]

    def start_quiz(self, st, msg: str, first: bool = True) -> Reply:
        i, it = self._game_item(st, "quiz")
        lead = self.pick(st, "quiz_intro" if first else "quiz_next",
                         self.d["quiz"]["intro"] if first else self.d["quiz"]["next"])
        st.last_action = {"kind": "quiz", "turn": st.turn}
        st.game = {"kind": "quiz", "i": i, "turn": st.turn, "tries": 0,
                   "score": (st.game or {}).get("score", 0) if not first else 0,
                   "asked": (st.game or {}).get("asked", 0) + 1 if not first else 1}
        return Reply(msg, "smalltalk", f"{lead} {it['q']}", via="quiz")

    def start_riddle(self, st, msg: str) -> Reply:
        i, it = self._game_item(st, "riddle")
        lead = self.pick(st, "riddle_intro", self.d["riddle"]["intro"])
        st.last_action = {"kind": "riddle", "turn": st.turn}
        st.game = {"kind": "riddle", "i": i, "turn": st.turn, "tries": 0}
        return Reply(msg, "smalltalk", f"{lead} {it['q']}", via="riddle")

    def game_answer(self, st, msg: str, norm: str) -> Reply | None:
        g = getattr(st, "game", None)
        if not g or st.turn - g.get("turn", -99) > 1:
            return None
        kind = g["kind"]
        spec = self.d[kind]
        it = spec["items"][g["i"]]
        s = norm.strip(" .!?")
        if _GAME_STOP.match(s):
            st.game = None
            if kind == "quiz" and g.get("asked"):
                return Reply(msg, "smalltalk", f"Okay, quiz over! You got {g.get('score', 0)} out of {g['asked']}. "
                                               "That was fun.", via="quiz")
            return Reply(msg, "smalltalk", "Okay, no more riddles for now!", via="riddle")
        if kind == "riddle" and _HINT.match(s):
            g["turn"] = st.turn
            ans = re.sub(r"^(?:a|an|the|your)\s+", "", it["a"])
            return Reply(msg, "smalltalk", f"Hint: it starts with “{ans[0].upper()}” and has {len(ans)} letters.",
                         via="riddle")
        if _GIVE_UP.match(s):
            st.game = None
            key = "giveup" if kind == "quiz" else "reveal"
            text = self.pick(st, f"{kind}_{key}", spec[key], x=it["a"])
            st.offer = {"kind": "again", "game": kind, "turn": st.turn}
            if kind == "quiz":
                g2 = dict(g)
                st.game_score = (g2.get("score", 0), g2.get("asked", 0))
            return Reply(msg, "smalltalk", f"{text} {spec['again']}", via=kind)
        if answer_matches(msg, it["a"], it.get("also", "")):
            st.game = None
            text = self.pick(st, f"{kind}_right", spec["right"])
            if kind == "quiz":
                st.game_score = (g.get("score", 0) + 1, g.get("asked", 1))
                score = f" {spec['score'].replace('{x}', str(st.game_score[0]) + ' out of ' + str(st.game_score[1]))}" \
                    if st.game_score[1] > 1 else ""
                text += score
            st.offer = {"kind": "again", "game": kind, "turn": st.turn}
            return Reply(msg, "smalltalk", f"{text} {spec['again']}", via=kind)
        # a question or a request instead of an answer: leave the game
        from engramm.chat.bot import message_type
        if message_type(msg) == "question" and len(s.split()) > 3:
            st.game = None
            return None
        if kind == "quiz":
            st.game = None
            st.game_score = (g.get("score", 0), g.get("asked", 1))
            text = self.pick(st, "quiz_wrong", spec["wrong"], x=it["a"])
            st.offer = {"kind": "again", "game": kind, "turn": st.turn}
            return Reply(msg, "smalltalk", f"{text} {spec['again']}", via="quiz")
        g["tries"] = g.get("tries", 0) + 1
        g["turn"] = st.turn
        if g["tries"] >= 3:
            st.game = None
            st.offer = {"kind": "again", "game": kind, "turn": st.turn}
            return Reply(msg, "smalltalk", self.pick(st, "riddle_reveal", spec["reveal"], x=it["a"]) + " " + spec["again"],
                         via="riddle")
        return Reply(msg, "smalltalk", self.pick(st, "riddle_wrong", spec["wrong"]), via="riddle")

    # -- words --------------------------------------------------------------------------------

    def spell(self, st, msg: str, word: str) -> Reply:
        w = word.lower().strip("'")
        sp = self.a.speller
        known = (sp is not None and sp.known(w)) or self._known_word(w)
        if known:
            return Reply(msg, "tool", f"{'-'.join(w.upper())} — “{w}”.", via="everyday")
        fixed = sp.fix_word(w) if sp is not None else w
        if fixed and fixed.lower() != w:
            fx = fixed.lower()
            return Reply(msg, "tool", f"I think you mean “{fx}”: {'-'.join(fx.upper())}.", via="everyday")
        return Reply(msg, "unknown", self.pick(st, "spell_unknown", self.d["spell"]["unknown"]), via="everyday")

    def _known_word(self, w: str) -> bool:
        from engramm.chat.smart import letters
        lt = letters()
        return bool(lt and w in lt.words)

    def rhyme(self, st, msg: str, word: str) -> Reply:
        from engramm.chat.smart import letters
        w = word.lower().strip("'")
        lt = letters()
        m = re.search(r"[aeiouy]+[^aeiouy]*$", w)
        if lt is None or not m or len(w) < 2:
            return Reply(msg, "unknown", self.pick(st, "rhyme_none", self.d["rhyme"]["none"], title=w), via="everyday")
        rime = m.group(0)
        if len(rime) < 2:
            rime = w[-2:]
        out = []
        for cand in lt.words:                      # most frequent first
            if cand == w or len(cand) < 2 or not cand.isalpha() or cand.endswith(w) or w.endswith(cand):
                continue
            cm = re.search(r"[aeiouy]+[^aeiouy]*$", cand)
            sp = self.a.speller
            if sp is not None and sp.capital.get(cand, 0.0) > 0.3:
                continue                            # mostly written with a capital: a name, not a word
            if cm and cm.group(0) == rime and len(cand) <= len(w) + 4:
                out.append(cand)
            if len(out) == 6:
                break
        if not out:
            return Reply(msg, "unknown", self.pick(st, "rhyme_none", self.d["rhyme"]["none"], title=w), via="everyday")
        return Reply(msg, "tool", self.pick(st, "rhyme_found", self.d["rhyme"]["found"], title=w, x=", ".join(out)),
                     via="everyday")

    # -- opinions about the current topic -----------------------------------------------------

    def opinion_it(self, st, msg: str) -> Reply:
        topic = st.topic.get("title") if st.topic and st.turn - st.topic.get("turn", -99) <= 4 else None
        if not topic:
            return Reply(msg, "smalltalk", self.pick(st, "opinion_none", self.d["opinion"]["none"]), via="everyday")
        found = self.a.about.find(topic, n=2)
        if found is None:
            return Reply(msg, "smalltalk", f"I can't judge {topic} myself — I don't have taste of my own. What did you think?",
                         via="everyday")
        fact = found.sentences[0]
        text = self.pick(st, "opinion_topic", self.d["opinion"]["topic"], x=fact)
        return Reply(msg, "about", text, evidence=fact, source=found.source, via="about", confidence=1.0)

    # -- the dispatcher -----------------------------------------------------------------------

    def compare(self, st, msg: str, s: str) -> Reply | None:
        if self.a.kgqa is None:
            return None
        if getattr(self, "_comparer", None) is None:
            from engramm.kb.compare import Comparer
            self._comparer = Comparer(self.a.kgqa)
        try:
            c = self._comparer.answer(s)
        except Exception:                     # a damaged fact bank must not break the chat
            return None
        if c is None:
            if self._comparer.is_request(s) and not re.search(r"\bor\b", s):
                return Reply(msg, "unknown", "I can only compare things my fact bank has numbers or facts for — "
                                             "like countries, cities, people, companies or mountains. Try “compare "
                                             "France and Germany” or “who is older, Einstein or Newton?”.",
                             via="kb")
            return None
        a, b = c.entities
        src_a = {"kind": "kb", "source": "dbpedia", "key": a.title}
        src_b = {"kind": "kb", "source": "dbpedia", "key": b.title}
        st.last_fact = {"evidence": c.evidence, "source": src_a, "answer": None, "question": msg, "sure": True}
        return Reply(msg, "answer", c.text, evidence=c.evidence, source=src_a, confidence=1.0, via="kb",
                     alternatives=[{"text": b.title, "source": src_b}])

    def opinion_about(self, st, msg: str, topic: str) -> Reply:
        """"What do you think about pineapple on pizza?": no opinion of its own, but a reaction that
        fits — a fact when it knows the thing, and the question back."""
        topic = re.sub(r"^(?:the|a|an)\s+", "", topic).strip(" ?.!")
        st.topic = {"title": topic, "name": topic, "turn": st.turn}
        found = None
        for cand in dict.fromkeys((topic, topic.title())):
            found = self.a.about.find(cand, n=1)
            if found is not None and found.sentences:
                break
            found = None
        if found is not None:
            fact = found.sentences[0].strip()
            text = self.pick(st, "opinion:fact", self.d["opinion"]["fact"], topic=topic, x=fact)
            return Reply(msg, "smalltalk", text, evidence=fact, source=found.source if hasattr(found, "source") else None,
                         via="everyday")
        return Reply(msg, "smalltalk", self.pick(st, "opinion:open", self.d["opinion"]["open"], topic=topic),
                     via="everyday")

    def request(self, st, msg: str, norm: str) -> Reply | None:
        s = norm.strip(" .!?")
        r = self.pick_from_list(st, msg, s)
        if r is not None:
            return r
        r = self.compare(st, msg, s)
        if r is not None:
            return r
        m = _ADVICE.match(s)
        exp = st.last_exp if st.last_exp and st.turn - st.last_exp.get("turn", -99) <= 4 else None
        if m:
            about = next((m.group(k) for k in ("about", "about2", "about3", "about4", "about5", "about6", "about7",
                                               "about8") if m.group(k)), None)
            if about and re.fullmatch(r"(?:it|this|that|them|him|her|life)", about):
                about = None
            # "what should I do?" after a moment is a request for advice; on its own, ideas for something to do;
            # "what do you think?" / "should I?" only right after a moment or a plan
            bare_opinion = re.match(r"^(?:so )?(?:what do you think|should i|is that a good idea)", s)
            if bare_opinion and not exp:
                pass
            elif about or exp or not _ACTIVITY.match(s):
                return self.advice(st, msg, about)
        hit = self._recommend_kind(s)
        if hit is not None:
            return self.recommend(st, msg, hit[0], hit[1])
        m = _OPINION_ABOUT.match(s)
        if m:
            return self.opinion_about(st, msg, m.group("x").strip())
        if _QUIZ.match(s):
            return self.start_quiz(st, msg)
        if _RIDDLE.match(s):
            return self.start_riddle(st, msg)
        m = _SPELL.match(s)
        if m and (m.group("w") or m.group("w2")) and not re.match(r"^spell (?:check|out|it)$", s):
            return self.spell(st, msg, m.group("w") or m.group("w2"))
        m = _RHYME.match(s)
        if m:
            return self.rhyme(st, msg, m.group("w"))
        if _OPINION_IT.match(s):
            return self.opinion_it(st, msg)
        for rx in _DECIDE:
            m = rx.match(s)
            if m:
                r = self.decide(st, msg, m.group("a"), m.group("b"))
                if r is not None:
                    return r
        return None

    # -- offers -------------------------------------------------------------------------------

    def take_offer(self, st, msg: str, norm: str, offer: dict, answer: str) -> Reply | None:
        kind = offer["kind"]
        s = norm.strip(" .!?")
        if answer == "no":
            return Reply(msg, "smalltalk", self.pick(st, "offer_no", self.d["offers"]["no"]), via="smalltalk")
        if kind in ("joke", "fact", "joke_or_fact"):
            want = "fact" if (kind == "fact" or re.search(r"\bfact\b", s)) else "joke"
            if kind == "joke_or_fact" and not re.search(r"\b(?:fact|joke)\b", s):
                want = "joke" if st.uses.get("joke", 0) <= st.uses.get("fact", 0) else "fact"
            from engramm.chat.acts import Unit
            return self.a._action(st, "fun_fact" if want == "fact" else "joke", Unit("intent", msg))
        if kind == "ideas" and offer.get("rec"):
            return self.recommend(st, msg, offer["rec"], offer.get("genre"), more=True)
        if kind == "more":
            return self.a._more(st, msg)
        if kind == "again":
            if offer.get("game") == "quiz":
                return self.start_quiz(st, msg, first=False)
            if offer.get("game") == "riddle":
                return self.start_riddle(st, msg)
            return None
        if kind == "listen":
            return Reply(msg, "smalltalk", self.pick(st, "offer_listen", self.d["offers"]["listen"]), via="smalltalk")
        if kind == "quiz":
            return self.start_quiz(st, msg)
        if kind == "riddle":
            return self.start_riddle(st, msg)
        return None

    # -- moments ------------------------------------------------------------------------------

    def moment(self, st, exp, text: str) -> str:
        if exp.topic and exp.person:
            shape = "person"
        elif exp.topic:
            shape = "thing"
        elif exp.timeword:
            shape = "time"
        else:
            shape = "plain"
        st.last_exp = {"valence": exp.valence, "topic": exp.topic, "person": exp.person, "text": text, "turn": st.turn}
        return self.pick(st, f"moment:{exp.valence}:{shape}", self.d["experience"][exp.valence][shape],
                         topic=exp.topic or "", timeword=exp.timeword or "day")

    # -- named things in a statement ----------------------------------------------------------

    _ENTITY_KIND = {"Film": "Film", "TelevisionShow": "Film", "Book": "Book", "Novel": "Book", "Manga": "Book",
                    "City": "Place", "Country": "Place", "Town": "Place", "Settlement": "Place", "Island": "Place",
                    "Mountain": "Place", "River": "Place", "AdministrativeRegion": "Place",
                    "Person": "Person", "Writer": "Person", "Scientist": "Person", "Politician": "Person",
                    "Philosopher": "Person", "Artist": "Person", "Royalty": "Person",
                    "MusicalArtist": "Music", "Band": "Music", "Album": "Music", "VideoGame": "Thing",
                    "Company": "Thing", "Food": "Thing", "Software": "Thing", "SoccerClub": "Thing"}
    _FACT_PROPS = {"Film": ("director", "releaseDate"), "Book": ("author",), "Place": ("country", "populationTotal"),
                   "Person": ("occupation", "knownFor", "birthDate"), "Music": ("genre", "bandMember"),
                   "Thing": ("industry", "developer", "foundingYear", "country")}

    def entity_reaction(self, st, text: str) -> tuple[str, dict, str] | None:
        """(reply, source, fact) for the best-known named thing in a statement, or None."""
        kg = self.a.kgqa
        if kg is None:
            return None
        spans = re.findall(r"\b[A-Z][\w'’\-.]*(?:\s+(?:of|the|and|de|von|van|da|del|la|le)?\s*[A-Z][\w'’\-.]*)*", text)
        first = text.split()[0] if text.split() else ""
        for span in sorted(set(spans), key=len, reverse=True):
            span = span.strip(" .")
            if span == first and len(span.split()) == 1 and span.lower() in ("i", "my", "the", "we", "today", "yesterday"):
                continue
            if span in ("I", "I'm", "I've", "I'd", "OK", "Ok"):
                continue
            for ent, kind in kg.kb.link(span, limit=4):
                if kind != 0 and ent.popularity < 10:
                    continue
                group = self._ENTITY_KIND.get(ent.type or "")
                if group is None:
                    continue
                fact = self._entity_fact(ent, group)
                if not fact:
                    continue
                tmpl = self._entity_text(st, text, group, ent.name, fact)
                src = {"kind": "kb", "source": "dbpedia", "key": ent.title}
                st.topic = {"title": ent.title, "name": ent.name, "type": ent.type, "turn": st.turn}
                self.a.bot.context.update({"mention": ent.name, "answer": None, "atype": None})
                return tmpl, src, fact
            found = self._about_descriptor(span)
            if found is not None:
                group, fact, ab = found
                tmpl = self._entity_text(st, text, group, ab.title, fact)
                st.topic = {"title": ab.title, "name": ab.title, "type": group, "turn": st.turn}
                self.a.bot.context.update({"mention": re.sub(r"\s*\([^)]*\)$", "", ab.title), "answer": None,
                                           "atype": None})
                return tmpl, ab.source, fact
        return None

    _VERB_ASK = [("visited", r"\b(?:went to|visited|been to|was in|were in|traveled to|travelled to|flew to|"
                             r"stayed in|spent \w+ in|got back from|came back from|holiday in|vacation in|trip to)\b"),
                 ("met", r"\b(?:met|saw|spoke to|talked to|ran into|bumped into)\b"),
                 ("watched", r"\b(?:watched|watching|seen|saw)\b"),
                 ("reading", r"\b(?:am reading|i'm reading|im reading|currently reading|started reading)\b"),
                 ("read", r"\b(?:read|finished)\b"),
                 ("listening", r"\b(?:listening to|listen to|listened to|concert)\b"),
                 ("playing", r"\b(?:playing|played|play)\b"),
                 ("like", r"\b(?:love|like|adore|enjoy|obsessed with|fan of|favou?rite)\b")]

    _ACTIVITY = re.compile(
        r"^(?i:(?:(?:so|well|oh|btw|today|yesterday)[, ]+)?i(?:'ve| have)? (?:just |finally |recently |also )?"
        r"(?P<v>watched|saw|read|finished|played|visited|went to|listened to|tried|started|am reading|'m reading|"
        r"have been reading|binged|rewatched|reread) (?:the (?:movie|film|book|show|series|game|album) )?)"
        r"(?P<x>[A-Z0-9][\w'’:&.\-]*(?: [A-Za-z0-9][\w'’:&.\-]*){0,6}?)"
        r"(?: (?:yesterday|today|tonight|last \w+|this \w+|again|on \w+|for the \w+ time|with \w+|all \w+|over the \w+))*[.!]*$")

    def activity_title(self, text: str) -> str | None:
        """The title in "I watched/read/played/visited <Title> …", or None."""
        m = self._ACTIVITY.match(text.strip())
        if not m:
            return None
        title = m.group("x").strip(" .!")
        low = title.lower()
        if low in ("it", "that", "this", "them", "him", "her", "tv", "a", "an") or \
                (low.startswith("the ") and low[4:] in _ERRANDS):
            return None
        return title

    def activity_reaction(self, st, text: str) -> str | None:
        """"I watched Inception yesterday" when nothing is known about Inception: a fitting
        question, as a person would ask — not "Noted, I'll remember that"."""
        title = self.activity_title(text)
        if title is None:
            return None
        verb = self._ACTIVITY.match(text.strip()).group("v").lower().replace("'m reading", "am reading")
        kind = {"watched": "watched", "saw": "watched", "binged": "watched", "rewatched": "watched", "read": "read",
                "finished": "read", "reread": "read", "played": "playing", "visited": "visited", "went to": "visited",
                "listened to": "listening", "am reading": "reading", "have been reading": "reading",
                "started": "reading", "tried": "like"}.get(verb, "Thing")
        lead = self.pick(st, "entity:lead_plain", self.d["entity"]["lead_plain"], title=title)
        asks = self.d["entity"]["ask"]
        ask = self.pick(st, f"entity:ask:{kind}", asks.get(kind) or asks["Thing"])
        st.topic = {"title": title, "name": title, "turn": st.turn}
        return f"{lead} {ask}"

    def _entity_text(self, st, text: str, group: str, title: str, fact: str) -> str:
        low = text.lower()
        verb = next((k for k, rx in self._VERB_ASK if re.search(rx, low)), None)
        if verb == "met" and group not in ("Person", "Music"):
            verb = "watched" if group == "Film" else None
        if verb == "watched" and group not in ("Film", "Thing"):
            verb = "met" if group in ("Person", "Music") else None
        if verb == "visited" and group != "Place":
            verb = None
        lead = self.pick(st, "entity:lead", self.d["entity"]["lead"], title=title, fact=fact)
        asks = self.d["entity"]["ask"]
        ask = self.pick(st, f"entity:ask:{verb or group}", asks.get(verb or group) or asks["Thing"])
        return f"{lead} {ask}"

    _DESC_GROUPS = [("Film", r"\b(?:film|movie|documentary|sitcom|television series|tv series|miniseries|anime)\b"),
                    ("Book", r"\b(?:novel|book|novella|memoir|poem|play|comic|manga)\b"),
                    ("Music", r"\b(?:band|album|song|single|rapper|singer|duo|group)\b"),
                    ("Place", r"\b(?:city|town|village|country|capital|island|region|state|province|mountain|lake|"
                              r"river|municipality|district)\b"),
                    ("Person", r"\b(?:actor|actress|writer|author|politician|footballer|player|scientist|artist|"
                               r"painter|composer|director|businessman|businesswoman|entrepreneur|philosopher|"
                               r"comedian|youtuber|athlete)\b")]

    def _about_descriptor(self, span: str):
        """"Inception" → ("Film", "It's a 2010 science fiction action film written and directed by
        Christopher Nolan.", About) from the first sentence of its article."""
        if len(span) < 3:
            return None
        ab = self.a.about.find(span, n=1)
        if ab is None or not ab.sentences:
            return None
        first = ab.sentences[0]
        m = re.search(r"\b(?:is|was|are|were) (?P<d>(?:an?|the) [^.;:]{3,140}?)(?:[,;.(]|$)", first)
        if not m:
            return None
        desc = m.group("d").strip()
        words = desc.split()
        if len(words) > 16:
            desc = " ".join(words[:16])
            desc = re.sub(r"\s+(?:and|or|of|by|in|on|with|for|the|a|an)$", "", desc)
        group = next((g for g, rx in self._DESC_GROUPS if re.search(rx, desc, re.I)), "Thing")
        pron = "It's" if re.match(r"^(?:is|are)\b", m.group(0)) else "It was"
        if group == "Person":
            pron = "That's" if re.match(r"^(?:is|are)\b", m.group(0)) else "That was"
        return group, f"{pron} {desc}.", ab

    def _entity_fact(self, ent, group: str) -> str | None:
        kb = self.a.kgqa.kb
        facts = kb.facts(ent.id, self._FACT_PROPS[group])
        vals: dict[str, list[str]] = {}
        for f in facts:
            v = re.sub(r"\s*\([^)]*\)$", "", f.value or "").strip()
            if v:
                vals.setdefault(f.prop, []).append(v)
        name = ent.name
        if group == "Film" and vals.get("director"):
            year = (vals.get("releaseDate") or [""])[0][:4]
            yr = f" in {year}" if re.fullmatch(r"\d{4}", year or "") else ""
            pron = "It was" if ent.type == "Film" else "It's"
            return f"{pron} directed by {_join(vals['director'][:2])}{yr}." if ent.type == "Film" else None
        if group == "Book" and vals.get("author"):
            return f"It was written by {_join(vals['author'][:2])}."
        if group == "Place" and vals.get("country") and vals["country"][0] != name:
            return f"It's in {vals['country'][0]}."
        if group == "Person":
            if vals.get("occupation"):
                occ = [o for o in vals["occupation"] if len(o) < 40][:2]
                if occ:
                    return f"{name.split()[-1] if ' ' in name else name} is known as {_with_a(_join(occ).lower())}."
            if vals.get("knownFor"):
                return f"{name} is known for {_join(vals['knownFor'][:2])}."
        if group == "Music" and vals.get("genre"):
            return f"That's {_join([g.lower() for g in vals['genre'][:2]])}, right?"
        if group == "Thing" and vals.get("developer"):
            return f"It was made by {_join(vals['developer'][:2])}."
        if group == "Thing" and vals.get("industry") and vals.get("foundingYear"):
            return f"It's a {vals['industry'][0].lower()} company, founded in {vals['foundingYear'][0]}."
        return None


def _join(xs: list[str]) -> str:
    xs = list(dict.fromkeys(xs))
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1]


def _with_a(phrase: str) -> str:
    return ("an " if phrase[:1] in "aeiou" else "a ") + phrase
