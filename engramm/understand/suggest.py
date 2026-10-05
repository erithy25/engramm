"""Suggestions that respect what the user said (U5): dishes, gifts, activities, films and short personal texts.

The conversation notes (engramm/understand/infer.py) and the last messages give the constraints — diet and allergies,
likes and dislikes, a budget, where the user lives, who the suggestion is for and what they are into, the occasion.
The catalogues below are small, general lists with tags; a suggestion is a filtered, ranked pick from them, never a
guess about the user. A forbidden ingredient is not even named (no "nut-free …"), so a reply never puts it in front of
someone who must avoid it.
"""
from __future__ import annotations

import re
import zlib

# -- catalogues ----------------------------------------------------------------------------------------------------
# (english, german, tags)
DISHES = [
    ("a vegetable stir-fry with rice", "ein Gemüse-Pfannengericht mit Reis", "veg vegan cheap dinner quick"),
    ("a chickpea and spinach curry with rice", "ein Kichererbsen-Spinat-Curry mit Reis", "veg vegan cheap dinner spicy"),
    ("a lentil soup with crusty bread", "eine Linsensuppe mit Brot", "veg vegan cheap dinner gluten"),
    ("pasta with tomato sauce and fresh basil", "Pasta mit Tomatensoße und frischem Basilikum", "veg vegan cheap dinner gluten quick"),
    ("a bean chili with rice", "ein Bohnen-Chili mit Reis", "veg vegan cheap dinner spicy"),
    ("a baked potato with beans and salad", "eine Ofenkartoffel mit Bohnen und Salat", "veg vegan cheap dinner"),
    ("a mushroom risotto", "ein Pilzrisotto", "veg dinner dairy mushroom"),
    ("a spinach and feta omelette", "ein Omelett mit Spinat und Feta", "veg breakfast dinner egg dairy quick"),
    ("vegetable fajitas with guacamole", "Gemüse-Fajitas mit Guacamole", "veg vegan dinner spicy gluten"),
    ("a Thai red curry with tofu and vegetables", "ein rotes Thai-Curry mit Tofu und Gemüse", "veg vegan dinner spicy soy"),
    ("spicy Szechuan-style aubergine with rice", "scharfe Aubergine nach Sichuan-Art mit Reis", "veg vegan dinner spicy soy"),
    ("a spicy Korean bibimbap bowl with gochujang", "eine scharfe Bibimbap-Schüssel mit Gochujang", "veg dinner spicy egg soy"),
    ("shakshuka — eggs baked in a spicy tomato sauce", "Shakshuka – Eier in würziger Tomatensoße", "veg breakfast dinner egg spicy cheap"),
    ("a jacket potato with chili con carne", "eine Ofenkartoffel mit Chili con Carne", "meat dinner spicy cheap"),
    ("chicken tikka masala with rice", "Chicken Tikka Masala mit Reis", "meat dinner spicy dairy"),
    ("grilled chicken with roasted vegetables", "Hähnchen vom Grill mit Ofengemüse", "meat dinner"),
    ("a roast vegetable couscous salad", "ein Couscous-Salat mit Ofengemüse", "veg vegan dinner gluten cheap"),
    ("a quinoa bowl with roasted sweet potato and avocado", "eine Quinoa-Bowl mit Süßkartoffel und Avocado", "veg vegan dinner"),
    ("oatmeal with fruit and cinnamon", "Haferbrei mit Obst und Zimt", "veg vegan breakfast cheap cinnamon"),
    ("overnight oats with berries", "Overnight Oats mit Beeren", "veg vegan breakfast cheap"),
    ("avocado toast with tomatoes", "Avocado-Toast mit Tomaten", "veg vegan breakfast gluten quick"),
    ("a fruit smoothie with an oat drink and banana", "ein Frucht-Smoothie mit Haferdrink und Banane", "veg vegan breakfast snack quick"),
    ("rice cakes with avocado", "Reiswaffeln mit Avocado", "veg vegan snack quick"),
    ("hummus with carrot and cucumber sticks", "Hummus mit Karotten- und Gurkensticks", "veg vegan snack quick cheap"),
    ("popcorn", "Popcorn", "veg vegan snack cheap quick"),
    ("fresh fruit salad", "ein frischer Obstsalat", "veg vegan snack breakfast quick"),
    ("roasted chickpeas with paprika", "geröstete Kichererbsen mit Paprika", "veg vegan snack cheap spicy"),
    ("a cheese and cracker plate", "ein Teller mit Käse und Crackern", "veg snack dairy gluten"),
]
BAKES = [
    ("cinnamon rolls", "Zimtschnecken", "bake cinnamon gluten dairy egg"),
    ("an apple crumble with cinnamon", "einen Apfel-Crumble mit Zimt", "bake cinnamon gluten dairy"),
    ("a cinnamon apple cake", "einen Apfel-Zimt-Kuchen", "bake cinnamon gluten dairy egg"),
    ("a lemon drizzle cake", "einen Zitronenkuchen", "bake gluten dairy egg"),
    ("chocolate brownies", "Schoko-Brownies", "bake gluten dairy egg chocolate"),
    ("banana bread", "Bananenbrot", "bake gluten egg cheap"),
    ("a simple fruit tart", "eine einfache Obsttarte", "bake gluten dairy egg"),
]
GIFTS = [  # (english, german, price, tags)
    ("a nice pair of gardening gloves and seed packets", "gute Gartenhandschuhe und Saatgut", 20, "garden"),
    ("a book about gardening or a pretty plant for the garden", "ein Gartenbuch oder eine schöne Pflanze", 25, "garden"),
    ("a jazz record on vinyl from a second-hand shop", "eine Jazz-Schallplatte aus dem Second-Hand-Laden", 25, "jazz music vinyl"),
    ("a good crime novel", "einen guten Krimi", 15, "crime books reading"),
    ("a selection of loose-leaf teas with a nice mug", "eine Auswahl loser Tees mit schöner Tasse", 25, "tea"),
    ("a cookbook", "ein Kochbuch", 25, "cooking food"),
    ("good coffee beans and a small treat", "guten Kaffee und eine kleine Leckerei", 20, "coffee"),
    ("a framed photo of a shared memory", "ein gerahmtes Foto einer gemeinsamen Erinnerung", 20, "any"),
    ("tickets for a concert or a show", "Karten für ein Konzert oder eine Vorstellung", 60, "music theatre"),
    ("a cosy blanket", "eine kuschelige Decke", 35, "any"),
    ("a board game", "ein Brettspiel", 30, "games"),
    ("a scented candle and bath set", "eine Duftkerze und ein Badeset", 25, "any relax"),
    ("a handwritten letter and a homemade treat", "einen handgeschriebenen Brief und etwas Selbstgebackenes", 5, "any"),
]
FILMS = [  # (title, year, genres)
    ("Back to the Future", 1985, "comedy adventure"), ("Paddington 2", 2017, "comedy family"),
    ("The Grand Budapest Hotel", 2014, "comedy"), ("Amélie", 2001, "romance comedy"), ("Toy Story", 1995, "family animation"),
    ("Spirited Away", 2001, "animation fantasy"), ("The Princess Bride", 1987, "adventure romance comedy"),
    ("Knives Out", 2019, "mystery comedy"), ("Mad Max: Fury Road", 2015, "action"), ("Inception", 2010, "scifi thriller"),
    ("The Martian", 2015, "scifi"), ("Interstellar", 2014, "scifi"), ("Arrival", 2016, "scifi"),
    ("Star Wars: A New Hope", 1977, "scifi adventure"), ("Little Women", 2019, "drama"), ("A Quiet Place", 2018, "horror"),
    ("Get Out", 2017, "horror thriller"), ("Hereditary", 2018, "horror"), ("La La Land", 2016, "romance musical"),
]
_FORBID = {  # constraint → tags a suggestion must not carry
    "veg": {"meat", "fish", "shellfish"}, "vegan": {"meat", "fish", "shellfish", "dairy", "egg"},
    "nuts": {"nuts"}, "peanuts": {"nuts"}, "shellfish": {"shellfish"}, "fish": {"fish", "shellfish"}, "gluten": {"gluten"},
    "lactose": {"dairy"}, "egg": {"egg"}, "soy": {"soy"}, "halal": {"meat"}, "mushroom": {"mushroom"}, "cilantro": {"cilantro"},
}


_TAG_WORDS = {
    "meat": r"chicken|beef|pork|bacon|ham|sausages?|steak|lamb|veal|turkey|mince|salami|chorizo|pepperoni|meatballs?|burger|"
            r"hähnchen|huhn|rind\w*|schwein\w*|speck|schinken|wurst|würstchen|hack\w*|lamm|pute|salami|frikadelle\w*|schnitzel|fleisch",
    "fish": r"fish|salmon|tuna|cod|sardines?|anchov\w*|fisch|lachs|thunfisch|kabeljau|sardinen|sushi",
    "shellfish": r"shrimps?|prawns?|lobster|crab|mussels?|oysters?|scallops?|calamari|squid|seafood|garnelen|krabben|hummer|muscheln|"
                 r"meeresfrüchte|tintenfisch|scampi|paella",
    "nuts": r"nuts?|peanuts?|almonds?|walnuts?|cashews?|hazelnuts?|pistachios?|pecans?|pesto|satay|praline|marzipan|nutella|"
            r"nüsse|nuss|erdnuss\w*|mandeln?|walnüsse|haselnüsse|cashew\w*",
    "gluten": r"bread|toast|pasta|spaghetti|noodles|pizza|flour|wheat|couscous|bagels?|croissants?|cake|cookies|crackers|"
              r"brot|brötchen|nudeln|mehl|weizen|kuchen|kekse|semmel",
    "dairy": r"cheese|milk|cream|butter|yogh?urt|feta|mozzarella|parmesan|ice cream|käse|milch|sahne|joghurt|quark|schmand",
    "egg": r"eggs?|omelett?e|mayo\w*|frittata|quiche|eier|ei\b|rührei",
    "soy": r"tofu|soy|soja|tempeh|edamame|miso",
    "mushroom": r"mushrooms?|pilz\w*|champignons?",
    "spicy": r"chilli|chili|spicy|hot sauce|jalape\w*|scharf\w*|curry",
    "cilantro": r"cilantro|coriander|koriander",
}


def violates(text: str, c: dict) -> bool:
    """Does a reply suggest something the user has to avoid?"""
    low = text.lower()
    for tag in c["forbid"]:
        rx = _TAG_WORDS.get(tag)
        if rx and re.search(rf"\b(?:{rx})\b", low) and not re.search(rf"\b(?:no|without|free|ohne|kein\w*|-free|frei)\W+(?:{rx})", low):
            return True
    if "horror" in c["dislike"] and any(t.lower() in low for t, _, g in FILMS if "horror" in g):
        return True
    return False


def check(st, msg: str, lang: str, reply: str, kind: str) -> str | None:
    """After the other layers answered a request for a suggestion or a short text: a reply that breaks or ignores a
    stated condition is replaced; a good one stays."""
    low = msg.lower().strip()
    if not _REQ.search(low):
        return None
    alt = suggest(st, msg, lang)
    if not alt:
        return None
    c = constraints(st)
    r = (reply or "").lower()
    weak = kind in ("unknown", "nothing") or not reply or bool(re.match(
        r"(?:i don'?t know|you haven'?t told|das weiß ich|das kann ich auf deutsch|da muss ich passen|sorry, who|"
        r"das habe ich nicht|okay, verstehe|i'm not sure)", r)) or bool(re.search(
        r"(?:here'?s what usually helps|a few things that usually help|das hilft meistens|ein paar dinge, die meistens helfen)", r))
    listish = "•" in r or "\n\n" in r or len(r) > 160 or bool(re.search(
        r"\b(?:how about|why not|you could|try|maybe|perhaps|wie wär'?s|probier|vielleicht|du könntest)\b", r))
    said_words = {w for w in re.findall(r"[a-zäöüß]{5,}", _said(st))}
    mentions = bool(c.get("city") and c["city"].lower() in r) or bool(said_words & set(re.findall(r"[a-zäöüß]{5,}", r)))
    if weak or violates(reply, c) or not (listish or mentions):
        return alt
    if mentions and listish:
        return None                     # it already speaks to what the user said ("a pizza without mushrooms")
    if c["like"] & {"scifi"} and not any(t.lower() in r for t, _, g in FILMS if "scifi" in g) and re.search(r"\b(?:movie|film)\b", low):
        return alt
    if c.get("city") and c["city"].lower() not in r and re.search(r"\b(?:where|near|around|show|visit|day out|walk|brunch|"
                                                                  r"restaurant|wo |hier|unternehmen|hingehen|ausflug)\b", low):
        return alt
    if c.get("budget") is not None and not re.search(r"\d", r) and re.search(r"\b(?:get|gift|present|buy|plan|ideas?|cheap|"
                                                                            r"schenk\w*|geschenk|idee)\b", low):
        return alt
    if re.search(r"\b(?:write|draft|schreib\w*|formulier\w*)\b", low):
        names = [v.lower() for v in ((st.uses.get("u_notes") or {}).get("display") or {}).values()]
        if names and not any(nm.split()[-1] in r for nm in names) and (not reply or "[" in reply or
                                                                       re.search(r"\b(?:hi sister|hey there|dear friend)\b", r)):
            return alt
    return None


def _said(st) -> str:
    n = st.uses.get("u_notes") or {}
    return " ".join(n.get("_said", []))


def constraints(st) -> dict:
    """What the conversation says about diet, likes, dislikes, budget, place and the person a suggestion is for."""
    n = st.uses.get("u_notes") or {}
    t = _said(st)
    c: dict = {"forbid": set(), "like": set(), "dislike": set()}
    if re.search(r"\b(?:i'?m|i am|we'?re|being|ich bin|bin) (?:a |an )?(?:vegan|veganer\w*)\b|\bi(?:'ve| have) been vegan\b|\bich lebe vegan\b|"
                 r"\b(?:went|gone) vegan\b|\bvegan\b(?= (?:now|since|for))", t):
        c["forbid"] |= _FORBID["vegan"]
    if re.search(r"\b(?:vegetarian|vegetarier\w*|veggie|don'?t eat meat|no meat|kein fleisch|esse kein fleisch)\b", t):
        c["forbid"] |= _FORBID["veg"]
    neg = (r"(?:allergic|allergy|allergie|allergisch|intoleran\w*|unverträglich\w*|can'?t (?:eat|have|stand|do)|kann kein\w*|"
           r"darf kein\w*|no|kein\w*|ohne|itchy|swell\w*|react\w*|reagier\w*|hives|epipen|notfallpen|er\b|hospital|"
           r"vertrag\w* (?:ich )?(?:null|nicht|kein\w*)|eklig|gross|disgusting|hate|hasse|never|nie|off the table|"
           r"celiac|coeliac|zöliakie|don'?t eat|esse? (?:kein\w*|nicht)|isst kein\w*|not allowed|verboten|"
           r"auch nicht|either|nor)")
    for key, rx in (("nuts", r"\b(?:nuts?|nüsse|nuss|tree nuts?|haselnüss\w*|walnüss\w*|mandel\w*|almonds?|cashews?|hazelnuts?)\b"),
                    ("peanuts", r"\b(?:peanuts?|erdnüsse|erdnuss)\b"), ("mushroom", r"\b(?:mushrooms?|pilze?|champignons?)\b"),
                    ("cilantro", r"\b(?:cilantro|coriander|koriander)\b"),
                    ("shellfish", r"\b(?:shellfish|seafood|prawns?|shrimps?|meeresfrüchte|krabben|garnelen)\b"),
                    ("fish", r"\b(?:fish|fisch)\b"), ("gluten", r"\b(?:gluten|coeliac|celiac|zöliakie|wheat)\b"),
                    ("lactose", r"\b(?:lactose|laktose|dairy|milchprodukte|milk)\b"), ("egg", r"\b(?:eggs?|eier|ei)\b"),
                    ("soy", r"\b(?:soy|soja)\b")):
        for sent in re.split(r"[.!?\n]|\s{2,}", t):
            if re.search(rx, sent) and re.search(rf"\b{neg}", sent):
                c["forbid"] |= _FORBID[key]
    if re.search(r"\b(?:celiac|coeliac|zöliakie)\b", t):
        c["forbid"] |= _FORBID["gluten"]
    if re.search(r"\b(?:laktoseintoleran\w*|lactose intoleran\w*)\b", t):
        c["forbid"] |= _FORBID["lactose"]
    if re.search(r"\b(?:no animal (?:stuff|products)|nothing from animals|fully vegan|plant[- ]based)\b", t):
        c["forbid"] |= _FORBID["vegan"]
    if re.search(r"\bkein fleisch\b.*\bfisch\b", t) or re.search(r"\b(?:pescetarian|no meat)\b", t):
        c["forbid"] |= {"meat", "fish", "shellfish"}
    if re.search(r"\bhalal\b", t):
        c["forbid"] |= _FORBID["halal"]
    for word, tag in (("spic", "spicy"), ("hot food", "spicy"), ("scharf", "spicy"), ("zimt", "cinnamon"), ("cinnamon", "cinnamon"),
                      ("chocolate", "chocolate"), ("schoko", "chocolate"), ("pasta", "pasta"), ("comed", "comedy"),
                      ("romcom", "romance"), ("sci-fi", "scifi"), ("scifi", "scifi"), ("action", "action")):
        if re.search(rf"\b(?:love|loves|like|likes|into|adore|fan of|liebe|mag|steh\w* auf)\b[^.!?]{{0,25}}{re.escape(word)}", t):
            c["like"].add(tag)
    for word, tag in (("sci-fi", "scifi"), ("scifi", "scifi"), ("science fiction", "scifi"), ("spaceship", "scifi"),
                      ("comed", "comedy"), ("berge", "mountains"), ("mountain", "mountains"), ("draußen", "outdoors"),
                      ("outdoors", "outdoors"), ("hiking", "outdoors"), ("wander", "outdoors")):
        if re.search(rf"(?:only (?:genre|thing)|am liebsten|the more|je mehr|favou?rite|lieblings|love|liebe)[^.!?]{{0,40}}{re.escape(word)}|"
                     rf"{re.escape(word)}[^.!?]{{0,30}}(?:only genre|the better|desto besser|am liebsten)", t):
            c["like"].add(tag)
    for word, tag in (("stadtbummel", "city"), ("city trip", "city"), ("shopping", "city"), ("crowds", "city")):
        if re.search(rf"{re.escape(word)}[^.!?]{{0,30}}(?:langweil\w*|bore\w*|nicht mein|not my)|(?:hate|hasse|bored by)[^.!?]{{0,20}}"
                     rf"{re.escape(word)}", t):
            c["dislike"].add(tag)
    for word, tag in (("horror", "horror"), ("scary", "horror"), ("gruselfilm", "horror"), ("mushroom", "mushroom"),
                      ("pilz", "mushroom"), ("spic", "spicy"), ("scharf", "spicy"), ("musical", "musical"), ("loud", "loud"),
                      ("laut", "loud")):
        if re.search(rf"\b(?:hate|hates|can'?t stand|dislike|don'?t like|not big on|not a fan of|no |hasse|mag kein\w*|"
                     rf"nicht so|kein fan)\b[^.!?]{{0,25}}{re.escape(word)}", t):
            c["dislike"].add(tag)
            c["like"].discard(tag)
    if "mushroom" in c["dislike"]:
        c["forbid"].add("mushroom")
    if "spicy" in c["dislike"]:
        c["forbid"].add("spicy")
    budget = n.get("budget")
    m = re.search(r"\b(?:only (?:got|have)|can spend(?: about| around)?|spend(?: about| around)?|budget(?:'s| is)?(?: like| about)?|"
                  r"max(?:imal)?|höchstens|bis zu|nur noch|hab nur|habe nur)\s+(?:€|\$|£)?(\d+(?:[.,]\d+)?)", t)
    if m:
        budget = float(m.group(1).replace(",", "."))
    m = re.search(r"(?:€|\$|£)?(\d+(?:[.,]\d+)?)\s*(?:bucks|euros?|eur|dollars?|pounds?|€|\$)?\s*(?:max|maximum|tops|at most|höchstens|maximal)\b", t)
    if m:
        budget = float(m.group(1).replace(",", "."))
    c["budget"] = budget
    c["city"] = n.get("city")
    return c


def _pick(items, k: int, seed: str):
    """A stable choice of k items (the same conversation gets the same suggestions)."""
    h = zlib.crc32(seed.encode("utf-8"))
    order = sorted(range(len(items)), key=lambda i: (zlib.crc32(f"{h}:{i}".encode()), i))
    return [items[i] for i in order[:k]]


def _bullets(xs) -> str:
    return "\n".join(f"• {x[:1].upper() + x[1:]}" for x in xs)


# -- the request -----------------------------------------------------------------------------------------------------
_REQ = re.compile(r"\b(?:suggest|recommend|recommendation|ideas?|\w*idee\w*|recipe|rezept|what (?:should|could|can|shall) (?:i|we)|"
                  r"what dish|which dish|(?:should|could) i (?:get|order|make|cook|bake|pack|bring|take)|was (?:koch|back|bestell|"
                  r"mach|schenk|nehm)\w* ich|welche\w* \w+ (?:soll|sollte) ich|ich brauch\w* (?:ne|eine|einen) (?:idee|vorschlag)|"
                  r"what to (?:cook|make|eat|order|get|do|bake)|where (?:should|could|can) (?:i|we)|help me (?:pick|choose|write)|"
                  r"write|draft|meal plan|any tips|vorschlag|vorschläge|idee|ideen|empfiehl|empfehlung|was (?:soll|sollte|könnte|kann) "
                  r"(?:ich|man|wir)|wo (?:soll|sollte|könnte|kann) (?:ich|man|wir)|schreib\w*|formulier\w*|was könnten wir)\b", re.I)


def suggest(st, msg: str, lang: str) -> str | None:
    low = msg.lower().strip()
    if not _REQ.search(low):
        return None
    de = lang == "de"
    c = constraints(st)
    seed = f"{st.uses.get('u_seed', '')}:{low}"
    if re.search(r"\b(?:write|draft|help me write|card|toast|note|message|text for|schreib\w*|\w*karte|\w*nachricht|toast|rede|"
                 r"glückwunsch\w*|sätze|lines|words)\b", low) and re.search(r"\b(?:write|draft|schreib\w*|formulier\w*|help me)\b", low):
        return _writing(st, low, de)
    if re.search(r"\b(?:movie|film|films|movies)\b", low):
        return _films(c, de, seed)
    if re.search(r"\b(?:gift|present|get (?:him|her|them|my \w+)|buy (?:him|her|them)|geschenk\w*|schenken)\b", low) or \
            (re.search(r"\b(?:idee|ideen|ideas?)\b", low) and re.search(r"\b(?:geburtstag|birthday|schenken|present|gift)\b", _said(st))):
        return _gifts(st, c, de, seed)
    if re.search(r"\b(?:bake|backen|backe|kuchen|cake|dessert|nachtisch|nachspeise)\b", low):
        return _bakes(c, de, seed)
    if re.search(r"\b(?:order|bestellen|get)\b", low) and c["forbid"] and not re.search(r"\b(?:pizza|tacos?)\b", low):
        return _order(c, de)
    if re.search(r"\b(?:cook|make for dinner|eat|dinner|lunch|breakfast|snacks?|snack on|dish|meal|recipe|rezept|food|kochen|koche|"
                 r"koch|essen|gericht|frühstück\w*|abendessen|mittagessen|snack|pizza|tacos?|topping\w*|pack|order|bestellen|"
                 r"get)\b", low) and not re.search(r"\b(?:where|wo)\b", low) and (c["forbid"] or c["like"] or c.get("budget")):
        return _dishes(low, c, de, seed)
    if re.search(r"\b(?:urlaub\w*|vacation|holiday|trip|reise|wochenende|weekend|getaway)\b", low) and (c["like"] or c["dislike"]):
        return _holiday(c, de)
    if c.get("city") or c.get("budget") or c["dislike"]:
        return _activity(low, c, de, seed)
    return None


def _dishes(low: str, c: dict, de: bool, seed: str) -> str | None:
    if not (c["forbid"] or c["like"] or c.get("budget")):
        return None                                # nothing to respect: the general layers suggest
    kind = "breakfast" if re.search(r"\b(?:breakfast|frühstück\w*)\b", low) else \
        "snack" if re.search(r"\b(?:snacks?|snack on|knabber\w*|pack)\b", low) else "dinner"
    if re.search(r"\btacos?\b|\btopping", low):
        opts = [("grilled vegetables with lime and avocado", "Grillgemüse mit Limette und Avocado", "veg vegan"),
                ("black beans, corn salsa and lime", "schwarze Bohnen, Maissalsa und Limette", "veg vegan"),
                ("shredded chicken with pickled red onions", "Hähnchen mit eingelegten roten Zwiebeln", "meat"),
                ("pulled pork with pineapple salsa", "Pulled Pork mit Ananas-Salsa", "meat"),
                ("crumbled feta, radish and lime", "Feta, Radieschen und Limette", "veg dairy"),
                ("spicy shrimp with mango salsa", "scharfe Garnelen mit Mango-Salsa", "shellfish spicy")]
        picks = [o for o in opts if not (set(o[2].split()) & c["forbid"])][:3]
        names = [o[1] if de else o[0] for o in picks]
        return ("Ein paar Kombis für deine Tacos:\n\n" if de else "A few combos for your tacos:\n\n") + _bullets(names)
    if re.search(r"\bpizza\b", low):
        opts = [("Margherita", "Margherita", "veg dairy gluten"), ("Pizza Diavola with spicy salami", "Diavola mit scharfer Salami",
                 "meat spicy gluten dairy"), ("Pizza Verdure with grilled vegetables", "Verdure mit Grillgemüse", "veg gluten dairy"),
                ("Quattro Formaggi", "Quattro Formaggi", "veg dairy gluten"), ("Prosciutto e funghi", "Prosciutto e Funghi",
                 "meat mushroom gluten dairy"), ("Tonno with onions", "Tonno mit Zwiebeln", "fish gluten dairy")]
        picks = [o for o in opts if not (set(o[2].split()) & c["forbid"])][:3]
        names = [o[1] if de else o[0] for o in picks]
        return ("Wie wär's mit:\n\n" if de else "How about:\n\n") + _bullets(names)
    pool = [d for d in DISHES if kind in d[2].split() and not (set(d[2].split()) & c["forbid"])]
    if c.get("budget") or re.search(r"\b(?:cheap|budget|günstig|billig)\b", low):
        pool = [d for d in pool if "cheap" in d[2].split()] or pool
    liked = [d for d in pool if set(d[2].split()) & c["like"]]
    if kind == "snack":
        pool = [d for d in pool if not re.search(r"popcorn|smoothie|cheese", d[0])] + \
            [d for d in [("trail mix of seeds and dried fruit", "Studentenfutter aus Kernen und Trockenobst", "veg vegan snack"),
                         ("energy balls made of oats and dates", "Energiekugeln aus Haferflocken und Datteln", "veg vegan snack"),
                         ("apples, bananas and dried apricots", "Äpfel, Bananen und getrocknete Aprikosen", "veg vegan snack"),
                         ("rice crackers", "Reiscracker", "veg vegan snack")] if not (set(d[2].split()) & c["forbid"])]
    picks = liked[:3] if len(liked) >= 2 else (liked + _pick([d for d in pool if d not in liked], 3 - len(liked), seed))
    if not picks:
        return None
    names = [d[1] if de else d[0] for d in picks]
    if c.get("budget") and re.search(r"\b(?:plan|week|woche|dinners|few)\b", low):
        b = _num(c["budget"])
        if de:
            return (f"Ein günstiger Plan, der unter {b} bleibt:\n\n{_bullets(names)}\n\nGrundzutaten wie Reis, Nudeln, Linsen, "
                    f"Bohnen und Gemüse der Saison halten die Kosten niedrig.")
        return (f"Here's a cheap plan that stays under {b}:\n\n{_bullets(names)}\n\nStaples like rice, pasta, lentils, beans "
                f"and seasonal veg keep it well within budget.")
    if "spicy" in c["like"]:
        head = "Wie wär's mit etwas Scharfem:" if de else "Since you love it hot, how about one of these:"
    else:
        head = "Ein paar Ideen, die zu dem passen, was du erzählt hast:" if de else "A few ideas that fit what you told me:"
    return f"{head}\n\n{_bullets(names)}"


def _bakes(c: dict, de: bool, seed: str) -> str | None:
    pool = [b for b in BAKES if not (set(b[2].split()) & c["forbid"])]
    liked = [b for b in pool if set(b[2].split()) & c["like"]]
    picks = (liked or _pick(pool, 3, seed))[:3]
    if not picks:
        return None
    names = [b[1] if de else b[0] for b in picks]
    if "cinnamon" in c["like"]:
        head = "Wenn du Zimt so liebst:" if de else "Since you love cinnamon:"
    else:
        head = "Wie wär's mit:" if de else "How about:"
    return f"{head}\n\n{_bullets(names)}"


def _holiday(c: dict, de: bool) -> str:
    if c["like"] & {"mountains", "outdoors"}:
        en = ["a hut-to-hut hike in the mountains", "a few days in an alpine valley with day hikes",
              "a lake in the mountains with walks, swimming and an easy summit"]
        de_ = ["eine Hüttenwanderung in den Bergen", "ein paar Tage in einem Alpental mit Tagestouren",
               "einen Bergsee mit Wanderungen, Baden und einem leichten Gipfel"]
        return ("Raus in die Natur statt Stadtbummel:\n\n" if de else "Out in nature rather than city strolling:\n\n") + \
            _bullets(de_ if de else en)
    en = ["a quiet spot by the sea", "a cabin in the countryside", "a small town with good food"]
    de_ = ["ein ruhiger Ort am Meer", "eine Hütte auf dem Land", "eine kleine Stadt mit gutem Essen"]
    return ("Ein paar Urlaubsideen:\n\n" if de else "A few getaway ideas:\n\n") + _bullets(de_ if de else en)


def _order(c: dict, de: bool) -> str:
    safe_en = ["a grilled chicken or steak dish", "a salad with a simple oil-and-vinegar dressing", "pasta with tomato sauce",
               "fries or roast potatoes"]
    safe_de = ["ein Gericht mit Hähnchen oder Steak vom Grill", "einen Salat mit einfachem Essig-Öl-Dressing",
               "Pasta mit Tomatensoße", "Pommes oder Ofenkartoffeln"]
    if "meat" in c["forbid"]:
        safe_en[0], safe_de[0] = "a grilled vegetable dish", "ein Gericht mit Grillgemüse"
    if "gluten" in c["forbid"]:
        safe_en[2], safe_de[2] = "a rice dish", "ein Reisgericht"
    if de:
        return ("Sicherer sind meist:\n\n" + _bullets(safe_de) + "\n\nSag dem Personal unbedingt Bescheid, worauf du achten musst – "
                "in der Küche kann etwas übertragen werden.")
    return ("Usually safer choices:\n\n" + _bullets(safe_en) + "\n\nDo tell the staff what you have to avoid — cross-contact in "
            "the kitchen happens.")


def _gifts(st, c: dict, de: bool, seed: str) -> str | None:
    t = _said(st)
    tags = set()
    for word, tag in (("garden", "garden"), ("garten", "garden"), ("jazz", "jazz"), ("vinyl", "vinyl"), ("records", "vinyl"),
                      ("platten", "vinyl"), ("krimi", "crime"), ("crime", "crime"), ("thriller", "crime"), ("tea", "tea"),
                      ("tee", "tea"), ("coffee", "coffee"), ("kaffee", "coffee"), ("cook", "cooking"), ("koch", "cooking"),
                      ("music", "music"), ("musik", "music"), ("read", "reading"), ("lies", "reading"), ("liest", "reading"),
                      ("book", "books"), ("bücher", "books"), ("game", "games"), ("spiel", "games")):
        if word in t:
            tags.add(tag)
    pool = [g for g in GIFTS if c.get("budget") is None or g[2] <= c["budget"]]
    match = [g for g in pool if set(g[3].split()) & tags]
    rest = [g for g in pool if g not in match and "any" in g[3].split()]
    picks = (match + _pick(rest, 3, seed))[:3]
    if not picks or not (tags or c.get("budget")):
        return None
    names = [g[1] if de else g[0] for g in picks]
    b = _num(c["budget"]) if c.get("budget") else None
    if de:
        head = f"Ein paar Ideen bis {b} Euro:" if b else "Ein paar Ideen:"
    else:
        head = f"A few ideas under {b}:" if b else "A few ideas:"
    return f"{head}\n\n{_bullets(names)}"


def _films(c: dict, de: bool, seed: str) -> str | None:
    if not (c["dislike"] or c["like"]):
        return None
    pool = [f for f in FILMS if not (set(f[2].split()) & c["dislike"])]
    liked = [f for f in pool if set(f[2].split()) & c["like"]]
    picks = (liked[:3] if len(liked) >= 3 else liked + _pick([f for f in pool if f not in liked], 3, seed))[:3]
    names = [f"„{t}“ ({y})" if de else f"“{t}” ({y})" for t, y, _ in picks]
    head = "Ein paar Filme für heute Abend:" if de else "A few films for tonight:"
    return f"{head}\n\n{_bullets(names)}"


def _activity(low: str, c: dict, de: bool, seed: str) -> str | None:
    city = c.get("city")
    quiet = "loud" in c["dislike"]
    b = _num(c["budget"]) if c.get("budget") else None
    if re.search(r"\b(?:walk|hike|spazier\w*|wander\w*)\b", low):
        en = [f"one of the big parks in {city}" if city else "a big park nearby", "a riverside or canal path",
              "a nature reserve or woods on the edge of town"]
        de_ = [f"einen der großen Parks in {city}" if city else "einen großen Park in der Nähe", "einen Weg am Fluss oder Kanal",
               "ein Naturschutzgebiet oder Wald am Stadtrand"]
        head = (f"Für einen schönen Spaziergang in {city}:" if city else "Für einen schönen Spaziergang:") if de else \
            (f"For a nice walk around {city}:" if city else "For a nice walk:")
    elif re.search(r"\b(?:brunch|café|cafe|coffee|frühstücken)\b", low):
        en = [f"the cafés in {city}'s city centre and the lively neighbourhoods around it" if city else "the cafés in the city centre",
              "a map app's top-rated brunch spots — check the newest reviews", "a local market with food stalls"]
        de_ = [f"die Cafés in der Innenstadt von {city}" if city else "die Cafés in der Innenstadt",
               "die bestbewerteten Brunch-Lokale in einer Karten-App – auf aktuelle Bewertungen achten", "einen Markt mit Essensständen"]
        head = (f"Für Brunch in {city}:" if city else "Für Brunch:") if de else (f"For brunch in {city}:" if city else "For brunch:")
    elif re.search(r"\b(?:restaurant|essen gehen|dinner out|anniversary|jahrestag)\b", low):
        en = [f"a well-reviewed restaurant in {city}'s old town or centre" if city else "a well-reviewed restaurant in the centre",
              "somewhere quiet with a set menu for the occasion", "booking ahead and mentioning the occasion — many places add a little extra"]
        de_ = [f"ein gut bewertetes Restaurant in der Altstadt von {city}" if city else "ein gut bewertetes Restaurant in der Innenstadt",
               "ein ruhiges Lokal mit Menü für den Anlass", "rechtzeitig reservieren und den Anlass erwähnen – oft gibt's eine kleine Überraschung"]
        head = (f"Für euren Abend in {city}:" if city else "Für euren Abend:") if de else (f"For a special dinner in {city}:" if city else "For a special dinner:")
    elif re.search(r"\b(?:kids|children|kinder|family|familie|day out|ausflug)\b", low):
        en = [f"the zoo or an aquarium in {city}" if city else "a zoo or an aquarium", "a science or children's museum",
              "a big playground park with a picnic"]
        de_ = [f"den Zoo oder ein Aquarium in {city}" if city else "einen Zoo oder ein Aquarium", "ein Kinder- oder Technikmuseum",
               "einen großen Spielplatz-Park mit Picknick"]
        head = (f"Für einen Ausflug in {city}:" if city else "Für einen Ausflug:") if de else (f"For a day out in {city}:" if city else "For a day out:")
    elif re.search(r"\b(?:date|romantic|romantisch)\b", low) or quiet or b:
        en = ["a picnic in a park at sunset", "cooking dinner together at home with a nice bottle of something",
              "a quiet wine bar or a small bistro" if quiet else "a cosy restaurant", "a museum late opening or a gallery"]
        de_ = ["ein Picknick im Park bei Sonnenuntergang", "zusammen zu Hause kochen", "eine ruhige Weinbar oder ein kleines Bistro"
               if quiet else "ein gemütliches Restaurant", "eine Abendöffnung im Museum oder eine Galerie"]
        if city:
            en[0], de_[0] = f"a picnic in one of {city}'s parks at sunset", f"ein Picknick in einem Park in {city} bei Sonnenuntergang"
        head = (f"Ruhige Ideen{' bis ' + b + ' Euro' if b else ''}:" if de else f"Some calm ideas{' that stay under ' + b if b else ''}:")
    elif city:
        en = [f"the old town and the main sights of {city}", f"a local market and a typical dish from {city}",
              f"a viewpoint over {city} and a walk by the water", "a museum that fits their interests"]
        de_ = [f"die Altstadt und die wichtigsten Sehenswürdigkeiten von {city}", f"einen Markt und ein typisches Gericht aus {city}",
               f"einen Aussichtspunkt über {city} und einen Spaziergang am Wasser", "ein Museum, das zu euren Interessen passt"]
        head = f"In {city} könntet ihr zum Beispiel:" if de else f"In {city}, you could try:"
    else:
        return None
    return f"{head}\n\n{_bullets(de_ if de else en)}"


# -- personal texts ------------------------------------------------------------------------------------------------------
_OCCASIONS = [
    ("graduation", r"\b(?:graduat\w*|degree|diploma|finished (?:school|uni|university|college)|abschluss|abitur|examen|bachelor|master)\b"),
    ("farewell", r"\b(?:leaving|farewell|goodbye|last day|moving away|retir\w*|abschied|verabschied\w*|geht in rente|verlässt)\b"),
    ("thanks", r"\b(?:thank|thanks|looked after|took care|helped|danke\w*|gekümmert|geholfen|aufgepasst)\b"),
    ("wedding", r"\b(?:wedding|getting married|hochzeit|heiraten)\b"),
    ("baby", r"\b(?:baby|newborn|geburt|nachwuchs)\b"),
    ("getwell", r"\b(?:sick|ill|surgery|hospital|krank|operation|krankenhaus)\b"),
    ("birthday", r"\b(?:birthday|bday|turns? \d+|\d+(?:st|nd|rd|th) birthday|geburtstag|wird \d+)\b"),
    ("congrats", r"\b(?:promot\w*|new job|got the job|passed|beförder\w*|neuen job|bestanden)\b"),
    ("jubilee", r"\b(?:anniversary|jubiläum|firmenjubiläum|dienstjubiläum|\d+ years (?:at|with) the company)\b"),
]
_TEXT = {
    "graduation": ("Dear {name},\n\nCongratulations on your graduation! All the hard work has paid off — I'm so proud of you. "
                   "Enjoy this moment, you've earned every bit of it.\n\nWith love",
                   "Liebe{r} {name},\n\nherzlichen Glückwunsch zu deinem Abschluss! Die ganze Arbeit hat sich gelohnt – ich bin so "
                   "stolz auf dich. Genieß den Moment, du hast ihn dir verdient!\n\nAlles Liebe"),
    "farewell": ("Dear {name},\n\nIt won't be the same without you. Thank you for {years}all the help, the laughs and the coffee "
                 "breaks. Wishing you every success in what comes next — stay in touch!\n\nAll the best",
                 "Liebe{r} {name},\n\nohne dich wird es nicht dasselbe sein. Danke für {years}die Hilfe, das Lachen und die "
                 "Kaffeepausen. Alles Gute für das, was jetzt kommt – bleib in Kontakt!\n\nAlles Gute"),
    "thanks": ("Dear {name},\n\nThank you so much for your help — it really meant a lot to us. We're very grateful!\n\n"
               "Warm wishes",
               "Liebe{r} {name},\n\nvielen herzlichen Dank für deine Hilfe – das hat uns wirklich viel bedeutet. Wir sind dir "
               "sehr dankbar!\n\nHerzliche Grüße"),
    "wedding": ("Dear {name},\n\nCongratulations on your wedding! Wishing you a lifetime of love, laughter and adventures "
                "together.\n\nWith love", "Liebe{r} {name},\n\nherzlichen Glückwunsch zur Hochzeit! Ich wünsche euch ein Leben "
                "voller Liebe, Lachen und gemeinsamer Abenteuer.\n\nAlles Liebe"),
    "baby": ("Dear {name},\n\nCongratulations on your little one! Wishing you all lots of joy, cuddles and some sleep.\n\nWith love",
             "Liebe{r} {name},\n\nherzlichen Glückwunsch zum Nachwuchs! Ich wünsche euch ganz viel Freude, Kuscheln und ein "
             "bisschen Schlaf.\n\nAlles Liebe"),
    "getwell": ("Dear {name},\n\nGet well soon! Thinking of you and hoping you're back on your feet very soon.\n\nTake care",
                "Liebe{r} {name},\n\ngute Besserung! Ich denke an dich und hoffe, du bist bald wieder fit.\n\nPass auf dich auf"),
    "birthday": ("Happy {age}birthday, {name}! Wishing you a wonderful day and a year full of good things. Can't wait to "
                 "celebrate with you!", "Alles Liebe zum {age}Geburtstag, {name}! Ich wünsche dir einen wunderschönen Tag und "
                 "ein Jahr voller schöner Momente. Ich freu mich darauf, mit dir zu feiern!"),
    "jubilee": ("Congratulations on your anniversary, {name}! Thank you for all your work and the great time together — here's to "
                "many more years!", "Herzlichen Glückwunsch zum Jubiläum, {name}! Danke für deinen Einsatz und die tolle "
                "Zusammenarbeit – auf viele weitere Jahre!"),
    "congrats": ("Congratulations, {name}! You really deserve this — I'm so happy for you.",
                 "Herzlichen Glückwunsch, {name}! Das hast du dir wirklich verdient – ich freu mich so für dich."),
}
_TOAST = ("To {name}! {age_en}Thank you for all the love, the stories and the wisdom you've given this family. Here's to you "
          "— cheers!", "Auf {name}! {age_de}Danke für all die Liebe, die Geschichten und die Weisheit, die du dieser Familie "
          "geschenkt hast. Auf dich – Prost!")


def _writing(st, low: str, de: bool) -> str | None:
    n = st.uses.get("u_notes") or {}
    t = _said(st)
    people, disp = n.get("people") or {}, n.get("display") or {}
    rel_m = re.search(r"\b(?:for|to|für|an)\s+(?:my|mein\w*|unser\w*)\s+(\w+)", low)
    key = None
    if rel_m:
        key = next((k for k, r in people.items() if r == rel_m.group(1) or r.startswith(rel_m.group(1)[:5])), None)
    if key is None and re.search(r"\b(?:her|him|them|sie|ihn|ihr)\b", low):
        key = n.get("last_person")
    if key is None and len(people) == 1:
        key = next(iter(people))
    if key is None:
        m = re.search(r"\b(?:her|his) name(?:'s| is)\s+([a-z]+)", t)
        if m:
            key = m.group(1)
            disp = {**disp, key: key.capitalize()}
    if key is None:
        return None
    name = disp.get(key) or key.capitalize()
    occ = next((o for o, rx in _OCCASIONS if re.search(rx, t)), None)
    if not occ:
        return None
    age = re.search(r"\b(\d{1,3})(?:st|nd|rd|th)\s+birthday\b|\bturns? (\d{1,3})\b|\bwird (\d{1,3})\b", t)
    a = next((x for x in age.groups() if x), None) if age else None
    rel = people.get(key, "")
    fem = bool(re.search(r"(?:in|schwester|mutter|mama|tante|oma|cousine|frau)$", rel)) or name.lower().startswith("frau ")
    if re.search(r"\b(?:toast|trinkspruch|rede)\b", low):
        tpl = _TOAST[1] if de else _TOAST[0]
        return tpl.format(name=name, age_en=f"{a} years young and still the heart of every gathering. " if a else "",
                          age_de=f"{a} Jahre jung und immer noch das Herz jeder Feier. " if a else "")
    tpl = _TEXT[occ][1 if de else 0]
    yrs = re.search(r"\bafter (\d+) years\b|\bnach (\d+) jahren\b", t)
    years = (f"{next(x for x in yrs.groups() if x)} years of " if not de else f"{next(x for x in yrs.groups() if x)} Jahre ") if yrs else ""
    out = tpl.format(name=name, r="" if fem else "r", age=(f"{a}th " if not de else f"{a}. ") if a else "", years=years)
    if de and name.lower().startswith(("frau ", "herr ")):
        out = out.replace(f"Liebe{'' if fem else 'r'} {name},\n\n", f"{'Liebe' if fem else 'Lieber'} {name},\n\n")
    head = "Hier ein Vorschlag:" if de else "Here's a suggestion:"
    return f"{head}\n\n{out}"


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}".rstrip("0").rstrip(".")
