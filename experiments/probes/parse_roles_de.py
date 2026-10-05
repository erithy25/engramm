"""U9: do parser roles beat the rule roles on the German labelled set (frames_train2)? Needs the models from
experiments/nlp_train_de.py in /dev/shm/engramm/models_de. Prints numbers only."""
import sys, json, re
sys.path.insert(0, "/home/user/engramm")
from engramm.nlp.parse import Parser
from engramm.nlp.pos import PerceptronTagger
from engramm.understand.frames import parse
from engramm.understand.lex import lexicon
from experiments.probes.frames_eval import _obj_ok
from types import SimpleNamespace
M = "/dev/shm/engramm/models_de/"
tg, xt, ps = PerceptronTagger.load(M + "pos_de.json"), PerceptronTagger.load(M + "xpos_de.json"), Parser.load(M + "parse_de.json")
lx = lexicon("de")
rows = [json.loads(l) for l in open("experiments/probes/frames_train2.jsonl") if l.strip()]
rows = [r for r in rows if r["lang"] == "de" and r.get("obj")]
base = new = comb = 0
for r in rows:
    f = parse(r["text"], "de")
    words = re.findall(r"\w+(?:-\w+)?|[^\w\s]", r["text"])
    tags = tg.tag(words); heads, labs = ps.parse_labelled(words, tags, xt.tag(words))
    cand = [w for w, t, l in zip(words, tags, labs) if t in ("NOUN", "PROPN") and l in ("nsubj", "obj", "nsubj:pass", "obl", "iobj")]
    cand.sort(key=lambda w: 0 if labs[words.index(w)].startswith("nsubj") else 1)
    pobj = next((w.lower() for w in cand if lx.get(w.lower(), "n") is not None), "")
    g = r["obj"]
    b = _obj_ok("de", g, f); base += b
    fp = SimpleNamespace(obj=pobj); n = _obj_ok("de", g, fp) if pobj else False; new += n
    comb += b or (not f.obj and n)
print(f"DE obj rows {len(rows)}: rules {base} ({base/len(rows):.1%}), parser {new} ({new/len(rows):.1%}), rules+parser-fallback {comb} ({comb/len(rows):.1%})")
