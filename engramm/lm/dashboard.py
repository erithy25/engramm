"""ENGRAMM dashboard: a local web page for chatting, writing, sources, learning and forgetting.

    python -m engramm.lm.dashboard                 # then open http://127.0.0.1:8765
    python -m engramm.lm.dashboard --port 9000 --model models/lm/main/model

Runs only on this machine (binds to 127.0.0.1) and needs no extra packages.
Every learn / forget goes through the same event log as the command line
(``user.log`` next to the model), so the dashboard and the CLI always share
one state.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

from engramm.chat.bot import BotConfig, ChatBot
from engramm.chat.config import FROZEN, cap_ratio
from engramm.chat.corpus import Corpus
from engramm.lm.generate import Decoding, generate
from engramm.lm.log import LoggedModel, replay_lm
from engramm.lm.model import HDCLanguageModel
from engramm.lm.tokenizer import EOS

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "models" / "lm" / "main" / "model"
MAX_TOKENS = 400


def load_logged(directory: Path) -> LoggedModel:
    model = HDCLanguageModel.load(directory)
    log = directory / "user.log"
    if log.exists():
        model, _, _ = replay_lm(log, model)
    return LoggedModel(model, log)


def _source(entry: dict | None) -> dict | None:
    if not entry:
        return None
    out = {"kind": entry.get("kind"), "source": entry.get("source")}
    if "key" in entry:
        out["key"] = entry["key"]
    if "match_tokens" in entry:
        out["match_tokens"] = entry["match_tokens"]
    if "distance" in entry:
        out["distance"] = entry["distance"]
    if "context" in entry:
        out["context"] = entry["context"]
    return out


def chat_index_dir(model_dir: Path, prefer: str | None = None) -> Path | None:
    """The configured sentence index next to the model (chat4: train stream + Wikipedia leads + SQuAD
    paragraphs), else the v2 index (``chat_build --v2``), if built. ``prefer`` names one to try first."""
    from engramm.chat.config import INDEX_NAME, QUICK_INDEX
    for name in ([prefer] if prefer else []) + [INDEX_NAME, QUICK_INDEX]:
        d = Path(model_dir).parent / name
        if (d / "info.json").exists():
            return d
    return None


def make_bot(lm: LoggedModel, index_dir: Path, config: BotConfig = FROZEN, df_cap: float | None = None) -> ChatBot:
    from engramm.chat.retrieve import Retriever
    corpus = Corpus.from_model(lm.model, index_dir)
    r = Retriever(corpus) if df_cap is None else Retriever(corpus, df_cap=df_cap)
    return ChatBot(lm, corpus, config, cap_ratio(index_dir), retriever=r)


class App:
    """The model plus a lock: one request changes or reads it at a time."""

    def __init__(self, lm: LoggedModel, bot: ChatBot | None = None):
        self.lm = lm
        self.lock = threading.Lock()
        self.bot = bot

    def chat(self, message: str) -> dict:
        if not message.strip():
            raise ValueError("Bitte etwas eingeben.")
        if self.bot is None:
            raise ValueError("Kein Satzindex – erst bauen: python -m experiments.chat_build --v2")
        return self.bot.turn(message).to_dict()

    def ask(self, question: str) -> dict:
        """One question, answered like in the chat (kept for scripts that used stage 1)."""
        question = question.strip()
        if not question:
            raise ValueError("Bitte eine Frage eingeben.")
        if self.bot is None:
            raise ValueError("Kein Satzindex – erst bauen: python -m experiments.chat_build --v2")
        r = self.bot.ask(question).to_dict()
        return {"question": question, "answer": r["answer"], "source": r["source"], "confidence": r["confidence"],
                "evidence": r["evidence"], "seconds": r["seconds"], "candidates": r["alternatives"]}

    @property
    def model(self) -> HDCLanguageModel:
        return self.lm.model

    def status(self) -> dict:
        m = self.model
        return {"state_digest": m.state_digest(), "base_digest": m.base_digest(),
                "train_tokens": int(len(m.tokens)), "train_documents": int(m.train.n_docs),
                "learned": [{"source": s, "tokens": int(len(m.tok.encode(t))), "preview": t[:120]}
                            for s, t in sorted(m.user_texts.items())],
                "tombstones": len(m.tombstones), "epoch": m.epoch,
                "chat": None if self.bot is None else {"sentences": self.bot.c.index.n,
                                                       "facts": len(self.bot.facts.facts)}}

    def write(self, prompt: str, tokens: int, seed: int, temperature: float, top_p: float, cache: str) -> dict:
        if not prompt.strip():
            raise ValueError("Bitte einen Satzanfang eingeben.")
        tokens = max(1, min(int(tokens), MAX_TOKENS))
        dec = Decoding(temperature=float(temperature), top_p=float(top_p), cache=cache)
        t0 = time.time()
        g = generate(self.model, prompt, tokens, int(seed), dec, explain=True)
        dt = time.time() - t0
        words = []
        for tid, step in zip(g.ids, g.steps):
            verbatim = step.get("verbatim") or []
            similar = step.get("similar") or []
            words.append({"text": self.model.tok.decode([tid]), "verbatim": _source(verbatim[0] if verbatim else None),
                          "similar": [_source(s) for s in similar[:3]]})
        return {"prompt": prompt, "text": g.text, "words": words, "tokens": len(g.ids),
                "seconds": dt, "tokens_per_second": len(g.ids) / max(dt, 1e-9)}

    def learn(self, source: str, text: str) -> dict:
        source, text = source.strip(), text.strip()
        if not source or not text:
            raise ValueError("Name und Text dürfen nicht leer sein.")
        if source in self.model.user_texts:
            raise ValueError(f"„{source}“ ist schon gelernt – erst vergessen oder anderen Namen wählen.")
        t0 = time.time()
        self.lm.learn_text(text, source)
        return {"source": source, "tokens": int(len(self.model.tok.encode(text))),
                "milliseconds": 1000 * (time.time() - t0), "state_digest": self.model.state_digest()}

    def forget(self, source: str) -> dict:
        t0 = time.time()
        kind = self.lm.forget(source.strip())
        return {"source": source, "kind": kind, "milliseconds": 1000 * (time.time() - t0),
                "state_digest": self.model.state_digest()}

    def next_words(self, prompt: str, k: int = 10) -> dict:
        ids = np.concatenate([[EOS], self.model.tok.encode(prompt)]).astype(np.uint16)
        p = self.model.next_distribution(ids)
        top = np.lexsort((np.arange(len(p)), -p))[:k]
        return {"prompt": prompt, "candidates": [{"text": self.model.tok.decode([int(t)]),
                                                  "probability": float(p[t])} for t in top]}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet console
            return

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/status":
                with app.lock:
                    self._json(200, app.status())
            else:
                self._json(404, {"error": "unbekannter Pfad"})

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n > 5_000_000:
                    raise ValueError("Anfrage zu groß (max. 5 MB Text).")
                data = json.loads(self.rfile.read(n) or b"{}")
                with app.lock:
                    if self.path == "/api/write":
                        out = app.write(data.get("prompt", ""), data.get("tokens", 80), data.get("seed", 0),
                                        data.get("temperature", 0.9), data.get("top_p", 0.8),
                                        data.get("cache", "off"))
                    elif self.path == "/api/learn":
                        out = app.learn(data.get("source", ""), data.get("text", ""))
                    elif self.path == "/api/forget":
                        out = app.forget(data.get("source", ""))
                    elif self.path == "/api/ask":
                        out = app.ask(data.get("question", ""))
                    elif self.path == "/api/chat":
                        out = app.chat(data.get("message", ""))
                    elif self.path == "/api/next":
                        out = app.next_words(data.get("prompt", ""))
                    else:
                        return self._json(404, {"error": "unbekannter Pfad"})
                self._json(200, out)
            except (ValueError, KeyError) as e:
                self._json(400, {"error": str(e).strip("'")})
            except Exception as e:  # noqa: BLE001 — report, keep serving
                self._json(500, {"error": f"{type(e).__name__}: {e}"})

    return Handler


def serve(app: App, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(app))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engramm.lm.dashboard", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    if not (args.model / "meta.json").exists():
        print(f"Kein Modell unter {args.model}. Erst bauen:\n"
              "  python -m experiments.lm_final_model --scale main --tau-index 1 --beta-index 1 --save")
        return 2
    print("Lade Modell … (dauert etwa eine Minute)", flush=True)
    lm = load_logged(args.model)
    idx = chat_index_dir(args.model)
    if idx is None:
        print("Hinweis: kein Satzindex – der Chat ist aus. Bauen mit: python -m experiments.chat_build --v2",
              flush=True)
    from engramm.chat.config import config_for
    app = App(lm, make_bot(lm, idx, config_for(idx)[0]) if idx else None)
    server = serve(app, port=args.port)
    print(f"ENGRAMM-Dashboard läuft: http://127.0.0.1:{args.port}  (Beenden mit Ctrl+C)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.lm.log.close()
    return 0


PAGE = r"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ENGRAMM</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1b;--muted:#6b6a66;--line:#e3e1dc;--accent:#2f5bd3;--accent-ink:#fff;
--user:#e6f4ea;--userline:#2e8b57;--base:#eef2fd;--hover:#fff3c4;--bad:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--card:#1e1e1e;--ink:#ecebe8;--muted:#a09e99;--line:#333;
--accent:#7aa2ff;--accent-ink:#0b1020;--user:#16301f;--userline:#5cc48b;--base:#1b2238;--hover:#4a3f12;--bad:#ff8a80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:18px 24px;border-bottom:1px solid var(--line);display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
header h1{margin:0;font-size:20px;letter-spacing:.5px}header p{margin:0;color:var(--muted)}
main{max-width:1100px;margin:0 auto;padding:20px 16px;display:grid;grid-template-columns:1fr 340px;gap:20px}
@media(max-width:860px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:20px}
h2{font-size:15px;margin:0 0 10px}label{font-size:13px;color:var(--muted);display:block;margin:8px 0 4px}
textarea,input,select{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit}
textarea{min-height:70px;resize:vertical}.row{display:flex;gap:10px;flex-wrap:wrap}.row>div{flex:1;min-width:90px}
button{background:var(--accent);color:var(--accent-ink);border:0;border-radius:8px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer;margin-top:10px}
button.ghost{background:transparent;color:var(--accent);border:1px solid var(--line)}button:disabled{opacity:.5;cursor:wait}
#out{font-size:17px;line-height:1.8;min-height:60px;white-space:pre-wrap}
#out .p{color:var(--muted)}#out .w{border-radius:4px;cursor:pointer;padding:1px 0}
#out .w.base{background:var(--base)}#out .w.user{background:var(--user);box-shadow:inset 0 -2px 0 var(--userline)}
#out .w:hover,#out .w.sel{background:var(--hover)}
.meta{color:var(--muted);font-size:13px;margin-top:8px}.err{color:var(--bad);font-size:14px;margin-top:8px}
.src{font-size:14px}.src .k{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px;margin-top:10px}
.src a{color:var(--accent);word-break:break-all}.pill{display:inline-block;font-size:12px;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}
ul{padding-left:0;list-style:none;margin:0}li{border-top:1px solid var(--line);padding:8px 0;display:flex;justify-content:space-between;gap:8px;align-items:center}
li small{color:var(--muted)}li button{margin:0;padding:4px 10px;font-size:13px}.legend span{margin-right:12px}
.log{max-height:460px;overflow-y:auto;margin:10px 0;display:flex;flex-direction:column;gap:10px}
.bub{max-width:88%;padding:9px 12px;border-radius:12px;line-height:1.45;word-wrap:break-word}
.bub.me{align-self:flex-end;background:var(--accent);color:var(--accent-ink);border-bottom-right-radius:4px}
.bub.bot{align-self:flex-start;background:var(--bg);border:1px solid var(--line);border-bottom-left-radius:4px}
.bub.bot.unknown{border-color:var(--bad)}.bub .ans{font-weight:600;font-size:16px}
.bub .meta{margin-top:4px}.bub details{font-size:13px;color:var(--muted);margin-top:4px}.bub details div{margin:5px 0}
.bub .ev{font-size:14px;color:var(--muted);margin-top:4px}.tag{display:inline-block;font-size:11px;padding:0 6px;
border-radius:99px;border:1px solid var(--line);color:var(--muted);margin-right:6px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px}.chip{background:transparent;color:var(--accent);
border:1px solid var(--line);border-radius:99px;padding:3px 10px;font-size:13px;margin:0;font-weight:500}
.send input{font-size:15px}
.cand{display:flex;justify-content:space-between;font-family:ui-monospace,Menlo,monospace;font-size:13px;border-top:1px solid var(--line);padding:3px 0}
</style></head><body>
<header><h1>ENGRAMM</h1><p>Antwortet und schreibt Englisch nur durch Lesen und Zählen · zeigt jede Quelle · lernt und vergisst auf Befehl</p></header>
<main>
<section>
 <div class="card">
  <h2>Chat</h2>
  <div class="meta">Frag etwas (Englisch), erzähl ENGRAMM etwas über dich oder die Welt, oder sag „Forget …“.
   Jede Antwort zeigt, woher sie stammt. Kein neuronales Netz, nur Zählen und Hypervektoren.</div>
  <div id="log" class="log" aria-live="polite"></div>
  <div class="chips" id="chips">
   <button class="chip" data-m="Who invented the telephone?">Who invented the telephone?</button>
   <button class="chip" data-m="Where was he born?">Where was he born?</button>
   <button class="chip" data-m="My name is Alex and I live in Hamburg.">My name is Alex …</button>
   <button class="chip" data-m="What is my name?">What is my name?</button>
   <button class="chip" data-m="Forget my name.">Forget my name.</button>
  </div>
  <div class="row send"><div style="flex:5"><input id="msg" placeholder="Type a message …" autocomplete="off"></div>
   <div style="flex:1;min-width:90px"><button id="send" style="margin-top:0;width:100%">Senden</button></div></div>
  <div id="qerr" class="err"></div>
 </div>
 <div class="card">
  <h2>Schreiben</h2>
  <label for="prompt">Satzanfang (Englisch)</label>
  <textarea id="prompt">The history of the city</textarea>
  <div class="row">
   <div><label for="tokens">Länge (Tokens)</label><input id="tokens" type="number" value="80" min="1" max="400"></div>
   <div><label for="seed">Seed</label><input id="seed" type="number" value="0"></div>
   <div><label for="temp">Temperatur</label><input id="temp" type="number" value="0.9" step="0.1" min="0.1" max="2"></div>
   <div><label for="topp">top-p</label><input id="topp" type="number" value="0.8" step="0.05" min="0.05" max="1"></div>
  </div>
  <button id="go">Schreiben</button> <button id="nx" class="ghost">Nächstes Wort?</button>
  <div id="werr" class="err"></div>
 </div>
 <div class="card">
  <h2>Text</h2>
  <div class="legend meta"><span class="pill" style="background:var(--base)">aus dem Korpus</span><span class="pill" style="background:var(--user)">aus deinem gelernten Text</span> Klick auf ein Wort zeigt die Quelle.</div>
  <div id="out" class="meta">Noch nichts geschrieben.</div>
  <div id="wmeta" class="meta"></div>
 </div>
</section>
<aside>
 <div class="card src" id="srcbox"><h2>Quelle</h2><div class="meta">Wähle ein Wort im Text.</div></div>
 <div class="card">
  <h2>Etwas beibringen</h2>
  <label for="lsrc">Name</label><input id="lsrc" placeholder="z. B. notizen">
  <label for="ltext">Text (Englisch)</label><textarea id="ltext" placeholder="The glass tower of Velmora was built by Quendrik Ashby."></textarea>
  <button id="learn">Lernen</button><div id="lmsg" class="meta"></div>
 </div>
 <div class="card">
  <h2>Gelernt</h2><ul id="learned"><li><small>Nichts.</small></li></ul>
  <div id="state" class="meta"></div>
 </div>
</aside>
</main>
<script>
const $=id=>document.getElementById(id);
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
 const j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function link(s){if(!s)return'';if(s.kind==='user')return'<b>Dein Text:</b> '+esc(s.source);
 const k=s.key||'';return s.source==='c4'&&/^https?:/.test(k)?'<b>Web:</b> <a href="'+esc(k)+'" target="_blank" rel="noopener">'+esc(k)+'</a>':'<b>Wikipedia:</b> '+esc(k.replace(/ @-@ /g,'-'))}
let words=[];
function showSource(i){document.querySelectorAll('#out .w').forEach(e=>e.classList.toggle('sel',+e.dataset.i===i));
 const w=words[i];let h='<h2>Quelle für „'+esc(w.text.trim()||w.text)+'“</h2>';
 if(w.verbatim){h+='<div class="k">Wörtlich gelesen</div><div>'+link(w.verbatim)+'</div><div class="meta">'+w.verbatim.match_tokens+' Tokens stimmen dort genau überein</div>'}
 else h+='<div class="meta">Keine wörtliche Quelle – neu kombiniert.</div>';
 if(w.similar.length){h+='<div class="k">Ähnliche Stellen</div>';for(const s of w.similar)h+='<div>„…'+esc(s.context)+'“ → '+link(s)+'</div>'}
 $('srcbox').innerHTML=h}
$('go').onclick=async()=>{$('werr').textContent='';$('go').disabled=true;$('out').textContent='Schreibe …';
 try{const r=await api('/api/write',{prompt:$('prompt').value,tokens:+$('tokens').value,seed:+$('seed').value,temperature:+$('temp').value,top_p:+$('topp').value,cache:'off'});
  words=r.words;let h='<span class="p">'+esc(r.prompt)+'</span>';
  r.words.forEach((w,i)=>{const cls=w.verbatim?(w.verbatim.kind==='user'?'user':'base'):'';h+='<span class="w '+cls+'" data-i="'+i+'">'+esc(w.text)+'</span>'});
  $('out').innerHTML=h;$('out').classList.remove('meta');
  document.querySelectorAll('#out .w').forEach(e=>e.onclick=()=>showSource(+e.dataset.i));
  $('wmeta').textContent=r.tokens+' Tokens · '+r.tokens_per_second.toFixed(0)+' Tokens/s · gleicher Seed = gleicher Text'}
 catch(e){$('werr').textContent=e.message;$('out').textContent=''}finally{$('go').disabled=false}};
$('nx').onclick=async()=>{$('werr').textContent='';try{const r=await api('/api/next',{prompt:$('prompt').value});
 let h='<h2>Wahrscheinlichste nächste Wörter</h2>';for(const c of r.candidates)h+='<div class="cand"><span>'+esc(JSON.stringify(c.text))+'</span><span>'+(100*c.probability).toFixed(1)+' %</span></div>';
 $('srcbox').innerHTML=h}catch(e){$('werr').textContent=e.message}};
const VIA={facts:'aus dem Faktengedächtnis (HDC)',lookup:'nachgeschlagen',memory:'Gedächtnis'};
function bubble(cls,html){const d=document.createElement('div');d.className='bub '+cls;d.innerHTML=html;$('log').appendChild(d);
 $('log').scrollTop=$('log').scrollHeight;return d}
async function send(text){text=(text||'').trim();if(!text)return;$('qerr').textContent='';$('send').disabled=true;
 bubble('me',esc(text));$('msg').value='';
 try{const r=await api('/api/chat',{message:text});let h='';
  if(r.kind==='answer'){h+='<div class="ans">'+esc(r.answer)+'</div>';
   if(r.evidence)h+='<div class="ev">„'+esc(r.evidence)+'“</div>';
   h+='<div class="meta"><span class="tag">'+(VIA[r.via]||r.via)+'</span>'+link(r.source)+' · '+(1000*r.seconds).toFixed(0)+' ms</div>'}
  else if(r.kind==='unknown'){h+='<div>'+esc(r.text)+'</div>';
   if(r.evidence)h+='<div class="ev">Nächster Fund: „'+esc(r.evidence)+'“ '+link(r.source)+'</div>'}
  else h+='<div>'+esc(r.text)+'</div>';
  if(r.resolved)h+='<div class="meta">verstanden als: '+esc(r.resolved)+'</div>';
  if(r.alternatives&&r.alternatives.length){h+='<details><summary>Weitere Fundstellen</summary>';
   for(const c of r.alternatives)h+='<div>„'+esc(c.text)+'“<br>'+link(c.source)+'</div>';h+='</details>'}
  bubble('bot'+(r.kind==='unknown'?' unknown':''),h);if(['learned','forgot'].includes(r.kind))refresh()}
 catch(e){$('qerr').textContent=e.message}finally{$('send').disabled=false;$('msg').focus()}}
$('send').onclick=()=>send($('msg').value);
$('msg').addEventListener('keydown',e=>{if(e.key==='Enter')send($('msg').value)});
document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>send(b.dataset.m));
async function refresh(){const s=await api('/api/status');const ul=$('learned');ul.innerHTML='';
 if(!s.learned.length)ul.innerHTML='<li><small>Nichts. Alles, was ENGRAMM weiß, stammt aus '+s.train_documents.toLocaleString('de')+' gelesenen Dokumenten.</small></li>';
 for(const l of s.learned){const li=document.createElement('li');li.innerHTML='<div><b>'+esc(l.source)+'</b><br><small>'+l.tokens+' Tokens · '+esc(l.preview)+'</small></div>';
  const b=document.createElement('button');b.className='ghost';b.textContent='Vergessen';b.onclick=async()=>{const r=await api('/api/forget',{source:l.source});
   $('lmsg').textContent='„'+l.source+'“ vergessen in '+r.milliseconds.toFixed(0)+' ms – spurlos.';refresh()};li.appendChild(b);ul.appendChild(li)}
 $('state').textContent='Zustand '+s.state_digest.slice(0,12)+' · '+(s.train_tokens/1e6).toFixed(0)+' Mio. gelesene Tokens'}
$('learn').onclick=async()=>{$('lmsg').textContent='';try{const r=await api('/api/learn',{source:$('lsrc').value,text:$('ltext').value});
 $('lmsg').textContent='Gelernt: '+r.tokens+' Tokens in '+r.milliseconds.toFixed(0)+' ms.';$('ltext').value='';$('lsrc').value='';refresh()}
 catch(e){$('lmsg').textContent=e.message}};
refresh().catch(e=>$('werr').textContent='Server nicht erreichbar: '+e.message);
</script></body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
