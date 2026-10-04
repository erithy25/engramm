"""Build the compact situation lexicon (English and German) from open lexical resources.

    python -m experiments.lex_build --oewn english-wordnet-2024.xml.gz --odenet deWordNet.xml \
        --framenet framenet_v17/ [--spell pack/spell.json] --out engramm/understand/data

Sources (docs/DATA_LICENSES.md; German forms: --kaikki-de, the kaikki.org extract of Wiktionary, CC BY-SA):
  - Open English WordNet 2024 (CC BY 4.0, derived from Princeton WordNet): word classes (lexicographer files),
    hypernyms and part-whole relations, irregular forms;
  - OdeNet 1.4 (CC BY-SA 4.0): German words, linked to the English synsets through the Interlingual Index;
  - FrameNet 1.7 (CC BY 3.0): which situation frames a word can evoke.
VerbNet is not used: its licence is not stated in the distributed files.

Output, one line per (lemma, part of speech), tab-separated, gzip-compressed:
    lemma  pos  supersense  categories  evidence
- supersense: the lexicographer file of the first sense (artifact, body, animal, state, change, contact …);
- categories: general classes from the hypernym and part-of closure of the first two senses (DEVICE, VEHICLE,
  BODYPART, INSECT, PERSON, RELATIVE, BUILDPART …) — the classes are WordNet's own, named here once;
- evidence: what kind of situation the word points to (HARM, FLUID, BODY, LOSE, THEFT, CONFLICT, FAIL, WIN, REL,
  BIRTH, DEATH, JOB, EMO, MONEY, MOVE, TRAVEL, DELAY, IMPACT, FIRE, BUY, COOK, LEARN, CELEB, SLEEP, EAT) from the
  word's FrameNet frames and verb hypernyms.
A second file per language maps inflected forms to lemmas (English irregular forms from OEWN).
No word or topic of a conversation is written here by hand; the hand-written parts are the general maps from
frames and WordNet classes to these few labels.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

# ---- general maps (frames and WordNet classes → labels) -------------------------------------------------------
FRAME_EVIDENCE = {
    "HARM": "Cause_harm Experience_bodily_harm Damaging Render_nonfunctional Cause_to_fragment Breaking_apart Destroying "
            "Being_operational Reshaping Catastrophe",
    "IMPACT": "Impact Cause_impact Hit_target",
    "FLUID": "Fluidic_motion Cause_fluidic_motion Mass_motion Filling Cause_to_be_wet Precipitation",
    "BODY": "Perception_body Cause_bodily_experience Medical_conditions Biological_urge Health_response Breathing "
            "Excreting Body_mark Recovery Cure Medical_intervention",
    "LOSE": "Losing Losing_track_of_theme Remembering_to_do",
    "THEFT": "Theft Robbery Committing_crime",
    "CONFLICT": "Quarreling Hostile_encounter Attack Offenses Judgment_direct_address Revenge Fighting_activity",
    "FAIL": "Endeavor_failure Hit_or_miss Respond_to_proposal Bungling",
    "WIN": "Win_prize Accomplishment Successful_action Finish_competition",
    "REL": "Forming_relationships Personal_relationship Make_acquaintance",
    "BIRTH": "Giving_birth Being_born",
    "DEATH": "Death Killing Losing_someone Dead_or_alive",
    "JOB": "Firing Hiring Get_a_job Being_employed Quitting Employing Change_of_leadership",
    "EMO": "Emotion_directed Experiencer_focus Fear Stimulus_focus Experiencer_obj Emotion_active Emotion_heat "
           "Emotions_by_stimulus Emotions_of_mental_activity",
    "MONEY": "Commerce_pay Expensiveness Earnings_and_losses Borrowing Lending Wealthiness Fining Commerce_sell",
    "BUY": "Commerce_buy Getting Receiving",
    "MOVE": "Residence Moving_in_place Arriving Departing Quitting_a_place",
    "TRAVEL": "Travel Ride_vehicle Operate_vehicle Vehicle_departure_initial_stage",
    "DELAY": "Change_event_time Hindering Relative_time Waiting",
    "FIRE": "Fire_burning Absorb_heat",
    "COOK": "Apply_heat Cooking_creation Food",
    "LEARN": "Education_teaching Examination Studying Becoming_aware Memorization",
    "CELEB": "Social_event Celebrate",
    "SLEEP": "Sleep Fall_asleep Waking_up",
    "EAT": "Ingestion",
}
# verbs whose hypernym closure reaches these WordNet verbs carry the label (first sense of each anchor)
VERB_ANCHORS = {
    "break": "HARM", "damage": "HARM", "injure": "HARM", "hurt": "BODY", "ache": "BODY", "bleed": "BODY", "lose": "LOSE",
    "steal": "THEFT", "rob": "THEFT", "win": "WIN", "succeed": "WIN", "fail": "FAIL", "quarrel": "CONFLICT",
    "fight": "CONFLICT", "die": "DEATH", "kill": "DEATH", "marry": "REL", "buy": "BUY", "pay": "MONEY",
    "relocate": "MOVE", "cook": "COOK", "forget": "LOSE", "flow": "FLUID", "spill": "FLUID",
    "collide": "IMPACT", "hit": "IMPACT", "burn": "FIRE", "sleep": "SLEEP", "eat": "EAT", "learn": "LEARN",
    "study": "LEARN", "postpone": "DELAY", "cancel": "DELAY", "celebrate": "CELEB", "hire": "JOB", "fire": "JOB",
    "give_birth": "BIRTH", "worry": "EMO", "fear": "EMO", "fall": "IMPACT", "trip": "IMPACT", "slip": "IMPACT",
    "promote": "JOB WIN", "graduate": "WIN LEARN", "flunk": "FAIL",
}
NOUN_EVIDENCE_ANCHORS = {   # event nouns: the closure reaches …
    "illness": "BODY", "symptom": "BODY", "pain": "BODY", "injury": "HARM BODY", "wound": "HARM BODY",
    "accident": "IMPACT", "collision": "IMPACT", "disagreement": "CONFLICT", "quarrel": "CONFLICT",
    "fight": "CONFLICT", "theft": "THEFT", "robbery": "THEFT", "leak": "FLUID", "flood": "FLUID", "bill": "MONEY",
    "debt": "MONEY", "fee": "MONEY", "fine": "MONEY", "rent": "MONEY", "examination": "LEARN", "interview": "JOB",
    "wedding": "REL CELEB", "engagement": "REL", "marriage": "REL", "divorce": "REL", "birth": "BIRTH",
    "pregnancy": "BIRTH", "funeral": "DEATH", "death": "DEATH", "promotion": "JOB WIN", "job": "JOB",
    "journey": "TRAVEL", "vacation": "TRAVEL", "flight": "TRAVEL", "party": "CELEB", "celebration": "CELEB",
    "birthday": "CELEB", "fire": "FIRE", "failure": "FAIL", "success": "WIN", "victory": "WIN", "loss": "LOSE",
    "delay": "DELAY", "cancellation": "DELAY", "breakdown": "HARM", "damage": "HARM", "fracture": "HARM BODY",
    "infection": "BODY", "fever": "BODY", "allergy": "BODY", "hole": "HARM", "crack": "HARM", "dent": "HARM",
    "stain": "HARM", "malfunction": "HARM", "puncture": "HARM",
}
# object categories: noun closure reaches the first sense of … (in that lexicographer file)
CATEGORY_ANCHORS = {
    "DEVICE": [("device", "noun.artifact"), ("electronic equipment", "noun.artifact"), ("computer", "noun.artifact"),
               ("machine", "noun.artifact"), ("home appliance", "noun.artifact")],
    "VEHICLE": [("vehicle", "noun.artifact")],
    "BODYPART": [("body part", "noun.body")],
    "ANIMAL": [("animal", "noun.Tops")],
    "INSECT": [("insect", "noun.animal"), ("arthropod", "noun.animal")],
    "PET": [("domestic animal", "noun.animal"), ("dog", "noun.animal"), ("cat", "noun.animal")],
    "PLANT": [("plant", "noun.Tops")],
    "FOOD": [("food", "noun.food"), ("foodstuff", "noun.food")],
    "DRINK": [("beverage", "noun.food")],
    "LIQUID": [("liquid", "noun.substance"), ("fluid", "noun.substance"), ("water", "noun.substance")],
    "PERSON": [("person", "noun.Tops")],
    "RELATIVE": [("relative", "noun.person")],
    "CHILD": [("child", "noun.person"), ("juvenile", "noun.person"), ("offspring", "noun.person")],
    "PARTNER": [("spouse", "noun.person"), ("lover", "noun.person")],
    "FRIEND": [("friend", "noun.person"), ("acquaintance", "noun.person")],
    "WORKER": [("worker", "noun.person"), ("professional", "noun.person"), ("employee", "noun.person")],
    "BUILDING": [("building", "noun.artifact"), ("dwelling", "noun.artifact"), ("room", "noun.artifact")],
    "BUILDPART": [("structural member", "noun.artifact"),
                  ("ceiling", "noun.artifact"), ("wall", "noun.artifact"), ("floor", "noun.artifact"),
                  ("window", "noun.artifact"), ("door", "noun.artifact"), ("roof", "noun.artifact"),
                  ("pipe", "noun.artifact"), ("plumbing", "noun.artifact")],
    "FURNITURE": [("furniture", "noun.artifact")],
    "CLOTHING": [("clothing", "noun.artifact"), ("footwear", "noun.artifact")],
    "CONTAINER": [("container", "noun.artifact"), ("bag", "noun.artifact")],
    "TOOL": [("tool", "noun.artifact"), ("implement", "noun.artifact")],
    "DOCUMENT": [("document", "noun.communication"), ("document", "noun.artifact"), ("ticket", "noun.communication")],
    "MONEY": [("money", "noun.possession"), ("monetary unit", "noun.quantity"), ("financial gain", "noun.possession")],
    "ORG": [("organization", "noun.group"), ("institution", "noun.group"), ("school", "noun.group")],
    "PLACE": [("location", "noun.Tops"), ("geographical area", "noun.location")],
    "EVENT": [("event", "noun.Tops"), ("social event", "noun.event"), ("meeting", "noun.act")],
    "COMM": [("message", "noun.communication"), ("electronic mail", "noun.communication"), ("telephone call", "noun.communication")],
    "TIME": [("time period", "noun.time")],
    "JEWELRY": [("jewelry", "noun.artifact"), ("adornment", "noun.artifact")],
    "KEYTHING": [("key", "noun.artifact"), ("card", "noun.artifact"), ("wallet", "noun.artifact")],
    "SPORT": [("sport", "noun.act"), ("game", "noun.act")],
    "ILLNESS": [("illness", "noun.state"), ("symptom", "noun.state"), ("injury", "noun.state"), ("pain", "noun.state")],
}
ADJ_EVIDENCE = {   # adjectives FrameNet misses; general state words, not topics
    "HARM": "broken cracked damaged smashed shattered dented scratched ruined busted torn ripped wrecked faulty",
    "LOSE": "lost missing gone",
    "THEFT": "stolen robbed burgled",
    "BODY": "sick ill unwell feverish nauseous dizzy sore swollen itchy bruised injured bleeding sprained queasy",
    "BIRTH": "pregnant expecting",
    "REL": "engaged married divorced single dumped",
    "DELAY": "late delayed cancelled canceled overdue",
    "MONEY": "broke expensive overdrawn",
    "EMO": "nervous anxious worried scared afraid bored lonely sad depressed stressed overwhelmed upset angry "
           "frustrated excited happy proud thrilled relieved",
}

LEX_SS = {"noun.Tops": "tops", "verb.change": "change"}


def ss_short(lexfile: str) -> str:
    return lexfile.split(".", 1)[-1].lower() if lexfile else ""


class WordNet:
    def __init__(self):
        self.synsets: dict[str, dict] = {}            # id → {lexfile, pos, ili, hyper[], holo[]}
        self.senses: dict[tuple[str, str], list[str]] = defaultdict(list)   # (lemma, pos) → synset ids in order
        self.members: dict[str, list[str]] = defaultdict(list)            # synset → lemmas
        self.forms: dict[str, set[str]] = defaultdict(set)                 # irregular form → lemmas
        self.by_ili: dict[str, str] = {}
        self.exact: dict[tuple[str, str], list[str]] = defaultdict(list)

    def load_oewn(self, path: Path) -> None:
        op = gzip.open if str(path).endswith(".gz") else open
        with op(path, "rb") as f:
            entry_lemma = entry_pos = None
            for ev, el in ET.iterparse(f, events=("start", "end")):
                tag = el.tag
                if ev == "start":
                    if tag == "LexicalEntry":
                        entry_lemma = entry_pos = None
                    continue
                if tag == "Lemma":
                    entry_lemma, entry_pos = el.get("writtenForm"), el.get("partOfSpeech")
                elif tag == "Sense" and entry_lemma:
                    pos = "a" if entry_pos == "s" else entry_pos
                    self.exact[(entry_lemma, pos)].append(el.get("synset"))
                    self.members[el.get("synset")].append(entry_lemma.lower())
                elif tag == "Form" and entry_lemma:
                    self.forms[el.get("writtenForm").lower()].add(entry_lemma.lower())
                elif tag == "Synset":
                    hyper = [r.get("target") for r in el.findall("SynsetRelation")
                             if r.get("relType") in ("hypernym", "instance_hypernym")]
                    holo = [r.get("target") for r in el.findall("SynsetRelation")
                            if r.get("relType") in ("holo_part", "holo_member", "holo_substance")]
                    sid = el.get("id")
                    self.synsets[sid] = {"lexfile": el.get("lexfile", ""), "pos": el.get("partOfSpeech"),
                                         "ili": el.get("ili"), "hyper": hyper, "holo": holo}
                    if el.get("ili"):
                        self.by_ili[el.get("ili")] = sid
                    el.clear()
                elif tag == "LexicalEntry":
                    el.clear()
        # chat text is lower case: "wasp" means the insect, not "WASP"; a capitalised entry only counts when no
        # lower-case entry of that word exists ("Monday" → "monday")
        for (w, pos), sids in self.exact.items():
            if w == w.lower():
                self.senses[(w, pos)] = list(sids)
        for (w, pos), sids in self.exact.items():
            if w != w.lower() and (w.lower(), pos) not in self.exact:
                self.senses[(w.lower(), pos)].extend(sids)

    def closure(self, sid: str, holo: bool = True, depth: int = 14) -> set[str]:
        out, todo = set(), [(sid, 0)]
        while todo:
            s, d = todo.pop()
            if s in out or d > depth or s not in self.synsets:
                continue
            out.add(s)
            nxt = self.synsets[s]["hyper"] + (self.synsets[s]["holo"] if holo and d < 3 else [])
            todo.extend((t, d + 1) for t in nxt)
        return out

    def first(self, lemma: str, lexfile: str | None = None, pos: str = "n") -> str | None:
        for sid in self.senses.get((lemma, pos), []):
            if lexfile is None or self.synsets.get(sid, {}).get("lexfile") == lexfile:
                return sid
        return None


def load_framenet(fn_dir: Path) -> dict[tuple[str, str], set[str]]:
    x = (fn_dir / "luIndex.xml").read_text(encoding="utf-8")
    out: dict[tuple[str, str], set[str]] = defaultdict(set)
    for m in re.finditer(r"<lu ([^>]*)>", x):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        name, frame = attrs.get("name", ""), attrs.get("frameName", "")
        if "." not in name:
            continue
        lemma, p = name.rsplit(".", 1)
        p = {"v": "v", "n": "n", "a": "a", "adv": "r"}.get(p)
        if p and " " not in lemma and "(" not in lemma:
            out[(lemma.lower(), p)].add(frame)
    return out


class Classes:
    """General categories and situation evidence of one WordNet synset (shared by English and German)."""

    def __init__(self, wn: WordNet, fn: dict):
        self.wn, self.fn = wn, fn
        self.frame_ev = {f: ev for ev, fs in FRAME_EVIDENCE.items() for f in fs.split()}
        self.cat_ids: dict[str, set[str]] = defaultdict(set)
        for cat, anchors in CATEGORY_ANCHORS.items():
            for lemma, lexfile in anchors:
                sid = wn.first(lemma, lexfile, "n")
                if sid:
                    self.cat_ids[cat].add(sid)
                else:
                    print(f"  anchor not found: {cat} {lemma} {lexfile}")
        self.verb_ids = {}
        for lemma, ev in VERB_ANCHORS.items():
            sid = wn.first(lemma.replace("_", " "), None, "v")
            if sid:
                self.verb_ids[sid] = ev
            else:
                print(f"  verb anchor not found: {lemma}")
        self.noun_ev_ids = {}
        for lemma, ev in NOUN_EVIDENCE_ANCHORS.items():
            sid = wn.first(lemma, None, "n")
            if sid:
                self.noun_ev_ids[sid] = ev
        self._memo: dict[str, tuple[frozenset, frozenset]] = {}

    def of(self, sid: str, pos: str) -> tuple[frozenset, frozenset]:
        key = sid + pos
        if key in self._memo:
            return self._memo[key]
        wn = self.wn
        cats, ev = set(), set()
        own = wn.closure(sid, holo=False)
        clo = wn.closure(sid, holo=(pos == "n"))
        for cat, ids in self.cat_ids.items():
            if own & ids:
                cats.add(cat)
            elif pos == "n" and clo & ids and cat in ("VEHICLE", "DEVICE", "BUILDING", "BODYPART", "CLOTHING", "FURNITURE"):
                cats.add("P-" + cat)          # a part of one: tire → P-VEHICLE, screen → P-DEVICE
        if pos == "n":
            if wn.synsets.get(sid, {}).get("lexfile") == "noun.body":
                cats.add("BODYPART")
            for nid, e in self.noun_ev_ids.items():
                if nid in clo:
                    ev.update(e.split())
        if pos == "v":
            for vid, e in self.verb_ids.items():
                if vid in clo:
                    ev.update(e.split())
        for member in wn.members.get(sid, [])[:6]:
            for frame in self.fn.get((member, pos), ()):
                if frame in self.frame_ev and len(self.fn.get((member, pos), ())) <= 6:
                    ev.add(self.frame_ev[frame])
        self._memo[key] = (frozenset(cats), frozenset(ev))
        return self._memo[key]


_SKIP_SECOND = ("noun.group", "noun.communication", "noun.cognition", "noun.act")
_CONCRETE_SS = ("artifact", "animal", "body", "food", "plant", "substance", "object")


def build(wn: WordNet, fn: dict, keep_words: set[str] | None) -> tuple[dict, dict, Classes]:
    cl = Classes(wn, fn)
    frame_ev = cl.frame_ev
    adj_ev = {w: ev for ev, ws in ADJ_EVIDENCE.items() for w in ws.split()}
    entries = {}
    for (lemma, pos), sids in wn.senses.items():
        phrasal = pos == "v" and re.fullmatch(r"[a-z]+ (?:up|down|out|off|away|in|on|over|back|through|apart)", lemma)
        if pos not in ("n", "v", "a") or (" " in lemma and not phrasal) or not re.fullmatch(r"[a-z][a-z' -]*", lemma):
            continue
        if keep_words is not None and lemma not in keep_words and pos == "n":
            continue
        ss = ss_short(wn.synsets.get(sids[0], {}).get("lexfile", ""))
        cats, ev = set(), set()
        for k, sid in enumerate(sids[:2]):
            if k == 1 and pos == "n" and wn.synsets.get(sid, {}).get("lexfile") in _SKIP_SECOND and ss in _CONCRETE_SS:
                continue                       # "bee": the insect, not the spelling bee
            c, e = cl.of(sid, pos)
            cats |= c
            ev |= e
        frames = fn.get((lemma, pos), ())
        for frame in frames if len(frames) <= 5 else ():    # "drop" evokes eight frames, birth among them: too vague
            if frame in frame_ev:
                ev.add(frame_ev[frame])
        if pos == "a" and lemma in adj_ev:
            ev.update(adj_ev[lemma].split())
        if cats or ev or ss:
            entries[(lemma, pos)] = (ss, ",".join(sorted(cats)), ",".join(sorted(ev)))
    for w, e in adj_ev.items():          # state words that are only participles in WordNet
        if (w, "a") not in entries:
            entries[(w, "a")] = ("all", "", e)
    forms = {f: sorted(ls)[0] for f, ls in wn.forms.items() if re.fullmatch(r"[a-z][a-z'-]*", f)}
    return entries, forms, cl


def load_odenet(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    syn_ili = {}
    for s in root.iter("Synset"):
        syn_ili[s.get("id")] = (s.get("ili"), s.get("{https://globalwordnet.github.io/schemas/dc/}subject") or "")
    senses = defaultdict(list)
    for e in root.iter("LexicalEntry"):
        lem = e.find("Lemma")
        if lem is None:
            continue
        w, p = lem.get("writtenForm"), lem.get("partOfSpeech")
        p = "a" if p == "s" else p
        for s in e.findall("Sense"):
            senses[(w, p)].append(s.get("synset"))
    return senses, syn_ili


def build_de(wn: WordNet, cl: Classes, de_senses, syn_ili) -> dict:
    """German lemma → the classes of its English synsets (through the Interlingual Index). OdeNet's sense order is
    not by frequency, so the first four senses count, and the word class is the first one with an English link."""
    entries = {}
    for (w, pos), sids in de_senses.items():
        if pos not in ("n", "v", "a") or " " in w or not re.fullmatch(r"[A-Za-zÄÖÜäöüß-]+", w):
            continue
        ss, cats, ev = "", set(), set()
        for sid in sids[:4]:
            ili, subject = syn_ili.get(sid, (None, ""))
            esid = wn.by_ili.get(ili) if ili else None
            if not esid:
                continue
            if not ss:
                ss = ss_short(wn.synsets.get(esid, {}).get("lexfile", "") or subject)
            c, e = cl.of(esid, pos)
            cats |= c
            ev |= e
        if ss or cats or ev:
            key = (w.lower(), pos)
            if key in entries:              # "Decke" and "decke": merge
                o = entries[key]
                cats |= set(filter(None, o[1].split(",")))
                ev |= set(filter(None, o[2].split(",")))
                ss = o[0] or ss
            entries[key] = (ss, ",".join(sorted(cats)), ",".join(sorted(ev)))
    return entries


_DE_SKIP = {"haben", "sein", "hat", "ist", "hatte", "war", "habe", "bin", "werden", "wird", "zu", "der", "die", "das",
            "des", "dem", "den", "ein", "eine"}


def build_forms_de(lines, de_entries: dict) -> dict[str, list[tuple[str, str]]]:
    """German inflected forms → lemmas from Wiktionary (kaikki.org JSON lines), kept only where the general suffix
    rules of engramm/understand/lex.py do not already find the lemma (strong verbs: gestochen → stechen)."""
    from engramm.understand.lex import _de_candidates
    out: dict[str, set] = defaultdict(set)
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        pos, w = e.get("pos"), e.get("word", "")
        if pos not in ("verb", "noun") or not re.fullmatch(r"[A-Za-zÄÖÜäöüß-]+", w):
            continue
        p = "v" if pos == "verb" else "n"
        lemma = w.lower()
        if (lemma, p) not in de_entries:
            continue
        for f in e.get("forms", []):
            tags = set(f.get("tags", []))
            if "table-tags" in tags or "inflection-template" in tags:
                continue
            for tok in f.get("form", "").split():
                tok = tok.strip(",.;").lower()
                if re.fullmatch(r"[a-zäöüß-]+", tok) and tok not in _DE_SKIP and tok != lemma:
                    out[tok].add((lemma, p))
    small = {}
    for form, pairs in out.items():
        rule = {c for c, _ in _de_candidates(form)}
        pairs = sorted(((l, p) for l, p in pairs if l not in rule), key=lambda x: (len(x[0]), x[0]))[:2]
        if pairs:
            small[form] = pairs
    return small


def _gloss_lemmas(gloss: str, pos: str) -> list[str]:
    """English words of a Wiktionary gloss: "mobile phone, cell phone (portable …)" → phone, phone."""
    g = re.sub(r"\([^)]*\)|“[^”]*”|\[[^\]]*\]", " ", gloss.lower())
    out = []
    for part in re.split(r"[,;]| or ", g):
        ws = re.findall(r"[a-z][a-z'-]*", part)
        ws = [w for w in ws if w not in ("a", "an", "the", "to", "be", "one's", "someone", "something", "oneself",
                                         "of", "for", "with", "by", "in", "on")]
        if not ws or len(ws) > 4:
            continue
        out.append(ws[-1] if pos == "n" else ws[0])
    return out[:4]


def build_de_gloss(lines, en_entries: dict) -> dict:
    """German word → classes of the English words its Wiktionary senses translate to, plus the noun's gender."""
    out = {}
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        pos, w = e.get("pos"), e.get("word", "")
        if pos not in ("noun", "verb", "adj") or not re.fullmatch(r"[A-Za-zÄÖÜäöüß-]+", w):
            continue
        p = {"noun": "n", "verb": "v", "adj": "a"}[pos]
        senses = [s for s in e.get("senses", []) if s.get("glosses") and "form-of" not in s.get("tags", [])]
        if not senses:
            continue
        gender = ""
        for h in e.get("head_templates", []):
            g = str(h.get("args", {}).get("1", ""))[:1]
            if p == "n" and g in ("m", "f", "n"):
                gender = g
                break
        ss, cats, ev = "", set(), set()
        for s in senses[:3]:
            for el in _gloss_lemmas(s["glosses"][0], p):
                hit = en_entries.get((el, p))
                if hit:
                    ss = ss or hit[0]
                    cats |= set(filter(None, hit[1].split(",")))
                    ev |= set(filter(None, hit[2].split(",")))
        key = (w.lower(), p)
        if key in out:
            o = out[key]
            cats |= set(filter(None, o[1].split(",")))
            ev |= set(filter(None, o[2].split(",")))
            ss, gender = o[0] or ss, o[3] or gender
        if ss or cats or ev or gender:
            out[key] = (ss, ",".join(sorted(cats)), ",".join(sorted(ev)), gender)
    return out


def merge_de(odenet: dict, gloss: dict) -> dict:
    """Wiktionary glosses first (they are by frequency and hand-written), OdeNet adds what they lack."""
    merged = {}
    for key in set(odenet) | set(gloss):
        o, g = odenet.get(key), gloss.get(key)
        if g and o:
            ss = g[0] or o[0]
            cats = set(filter(None, g[1].split(","))) or set(filter(None, o[1].split(",")))
            ev = set(filter(None, g[2].split(","))) or set(filter(None, o[2].split(",")))
            merged[key] = (ss, ",".join(sorted(cats)), ",".join(sorted(ev)), g[3])
        elif g:
            merged[key] = g
        else:
            merged[key] = o + ("",)
    return merged


def write(path: Path, entries: dict) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as f:
        for (lemma, pos), vals in sorted(entries.items()):
            f.write("\t".join((lemma, pos) + tuple(vals)).rstrip("\t") + "\n")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--oewn", type=Path, required=True)
    ap.add_argument("--odenet", type=Path, required=True)
    ap.add_argument("--framenet", type=Path, required=True)
    ap.add_argument("--spell", type=Path, help="spell.json of a pack: keep only nouns seen in the reading")
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--kaikki-de", type=Path, help="kaikki.org German Wiktionary extract (JSON lines) for forms_de")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    wn = WordNet()
    wn.load_oewn(a.oewn)
    print(f"OEWN: {len(wn.synsets)} synsets, {len(wn.senses)} lemma/pos")
    fn = load_framenet(a.framenet)
    print(f"FrameNet: {len(fn)} lexical units")
    keep = None
    if a.spell:
        sp = json.loads(a.spell.read_text())
        keep = {w for w, c in zip(sp["words"], sp["counts"]) if c >= a.min_count}
        keep |= {w.lower() for w in keep}
    en, forms, cl = build(wn, fn, keep)
    write(a.out / "lex_en.tsv.gz", en)
    with gzip.open(a.out / "forms_en.tsv.gz", "wt", encoding="utf-8", compresslevel=9) as f:
        for form, lemma in sorted(forms.items()):
            f.write(f"{form}\t{lemma}\n")
    de_senses, syn_ili = load_odenet(a.odenet)
    de = build_de(wn, cl, de_senses, syn_ili)
    if a.kaikki_de:
        with open(a.kaikki_de, encoding="utf-8") as f:
            de = merge_de(de, build_de_gloss(f, en))
    write(a.out / "lex_de.tsv.gz", de)
    if a.kaikki_de:
        with open(a.kaikki_de, encoding="utf-8") as f:
            forms_de = build_forms_de(f, de)
        with gzip.open(a.out / "forms_de.tsv.gz", "wt", encoding="utf-8", compresslevel=9) as f:
            for form, pairs in sorted(forms_de.items()):
                f.write(form + "\t" + " ".join(f"{l}:{p}" for l, p in pairs) + "\n")
        print(f"forms_de: {len(forms_de)}")
    for name in ("lex_en.tsv.gz", "forms_en.tsv.gz", "lex_de.tsv.gz"):
        print(f"{name}: {(a.out / name).stat().st_size / 1e6:.2f} MB")
    print(f"entries: en {len(en)}, de {len(de)}, forms {len(forms)}")


if __name__ == "__main__":
    main()
