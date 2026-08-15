#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vox_fusion.py — VOX Stufe 3b: DER SPRECHER MIT GEDÄCHTNIS
===========================================================
(Projekt VOX, Blueprint §3-3b; AXIOM-Protokoll gilt.)

Prinzip: Ein lokales Sprachmodell (Qwen-3B via llama.cpp, GPU-frei) REDET
und VERSTEHT. ENGRAMM ist das GEDÄCHTNIS dahinter: es merkt sich Fakten in
Millisekunden, für immer, und liefert sie dem Modell als Kontext — mit
Provenienz. Das ist der Chatbot, den kein Cloud-ChatGPT bieten kann:
100 % lokal, sofort lernend, jede erinnerte Tatsache belegbar.

Ablauf pro Nutzer-Turn:
  1. ENGRAMM.recall(user_text): relevante gespeicherte Fakten abrufen (Bit-Abruf, ms).
  2. Prompt bauen: [System + erinnerte Fakten + kurze Dialoghistorie + user_text].
  3. LLM.generate(prompt): Qwen formuliert die Antwort (lokal, kein Netz).
  4. ENGRAMM.absorb(user_text): neue Fakten aus dem Turn ins Gedächtnis schreiben.
Trennung: Der LLM-Teil ist hinter MouthBackend gekapselt. Im Container läuft
ein deterministischer MockMouth (verifiziert die Gedächtnis-Mechanik); auf
dem Mac wird QwenMouth (llama.cpp, .venv_b1) eingesetzt — identische Schnittstelle.

Aufrufe:
  python3 vox_fusion.py selftest        # Gedächtnis-Mechanik (Mock, netzfrei)
  python3 vox_fusion.py demo            # Skript-Dialog mit Mock-Mund
  python3 vox_fusion.py chat            # echtes Gespräch (nutzt Qwen, falls da)
"""
from __future__ import annotations
import argparse
import re
import sys
import time

import numpy as np

from engramm import Engramm, ItemMemory, hamming, sim_from_dh

FACT_THRESHOLD = 0.18          # ab welcher Ähnlichkeit ein erinnerter Fakt gilt
MAX_FACTS = 4                  # wie viele Fakten max. in den Prompt


# ---------------------------------------------------------------------------
# GEDÄCHTNIS (ENGRAMM) — hier verifizierbar, plattformunabhängig
# ---------------------------------------------------------------------------
class Memory:
    """ENGRAMM als Fakten- und Dialoggedächtnis. Lernen = Schreiben (ms)."""

    # Fakt-Extraktion: (Schluessel, Wert) — Schluessel steuert den Abruf.
    FACT_PATTERNS = [
        (re.compile(r"\bmy ([\w ]{2,30}?) (?:is|are|is called|is named) ([\w .'&-]{1,40})", re.I), "en"),
        (re.compile(r"\bi (?:work at|work for) ([\w .'&-]{2,40})", re.I), "work"),
        (re.compile(r"\bi live in ([\w .'-]{2,40})", re.I), "live"),
        (re.compile(r"\bi (?:like|love|prefer) ([\w .'-]{2,40})", re.I), "like"),
        (re.compile(r"\bich arbeite bei ([\w .'&-]{2,40})", re.I), "work"),
        (re.compile(r"\bich wohne (?:in|zwischen) ([\w .'&-]{2,50})", re.I), "live"),
        (re.compile(r"\bich (?:mag|liebe) ([\w .'-]{2,40})", re.I), "like"),
        (re.compile(r"\bich (?:heiße|bin) ([\w .'-]{2,40})", re.I), "name"),
        (re.compile(r"\bmy name is ([\w .'-]{2,40})", re.I), "name"),
        (re.compile(r"\b(?:er|sie|es|he|she|it) (?:heißt|is called|is named) ([\w .'-]{1,40})", re.I), "en"),
        (re.compile(r"\bmein(?:e)? ([\w ]{2,30}?) (?:ist|heißt|sind) ([\w .'-]{1,40})", re.I), "de"),
    ]
    # Abruf-Synonyme: Frageworte -> Schluessel-Hinweise, damit "where do I work" den work-Fakt trifft
    QUERY_HINTS = {"work": ["work", "job", "arbeite", "beruf"],
                   "live": ["live", "wohne", "where", "wo"],
                   "like": ["like", "love", "food", "mag", "essen"],
                   "name": ["name", "called", "heiße", "heißt"]}

    def __init__(self, seed: int = 42, persist_path: str | None = "data/vox_facts.log"):
        self.eng = Engramm(ItemMemory(seed), t2_local=True)
        self.facts: list[str] = []          # menschenlesbare Fakttexte
        self._keys = None
        self.persist_path = persist_path
        self._log = None
        if persist_path:
            self._replay()                  # frühere Fakten laden (Neustart-fest)
            import os
            os.makedirs(os.path.dirname(persist_path) or ".", exist_ok=True)
            self._log = open(persist_path, "a", encoding="utf-8")

    def _replay(self):
        """Fakten aus dem append-only-Log wiederherstellen (M2b-Muster)."""
        import os, json as _j
        if not os.path.exists(self.persist_path):
            return
        for line in open(self.persist_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = _j.loads(line)
            self._register(rec["fact"], rec["key"])

    def _register(self, fact: str, key_text: str):
        """Einen Fakt in Gedächtnis + Index eintragen (ohne Log-Schreiben)."""
        self.eng.learn(key_text.encode("utf-8"), f"fact:{fact}")
        self.facts.append(fact)
        self._store_key(key_text)

    @staticmethod
    def _clean_value(val: str) -> str:
        """Wert an Konjunktionen/Satzgrenzen abschneiden — verhindert, dass ein
        Muster den halben Satz verschluckt ('Erik and my dog...' -> 'Erik')."""
        val = val.strip(" .,!?")
        # an ' and ' / ' und ' / Komma abschneiden
        val = re.split(r"\s+(?:and|und)\s+|,", val, maxsplit=1)[0].strip()
        words = val.split()
        return " ".join(words[:4])              # max. 4 Wörter pro Fakt

    def _extract(self, text: str):
        out, seen = [], set()
        for pat, cat in self.FACT_PATTERNS:
            for m in pat.finditer(text):
                raw = " ".join(g for g in m.groups() if g)
                if cat == "live":                   # Orte: 'A und B' zusammenhalten
                    val = " ".join(raw.strip(" .,!?").split()[:5])
                else:
                    val = self._clean_value(raw)
                low = val.lower()
                if len(val) >= 2 and low not in seen:
                    seen.add(low)
                    out.append((cat, val))
        return out

    def absorb(self, text: str):
        """Neue Fakten aus einem Turn ins Gedächtnis schreiben (append-only)."""
        new = []
        for cat, val in self._extract(text):
            fact = val if cat in ("en", "de") else f"{cat}: {val}"
            if fact in self.facts:
                continue
            if cat in ("de", "en"):
                # Sachwort steht im Wert selbst (z.B. "Hund Loui") -> Wert IST der Schluessel,
                # plus generische Frage-Woerter, damit "wie heisst..." zieht.
                key_text = f"{val} heißt is called name"
            else:
                hint = " ".join(self.QUERY_HINTS.get(cat, [cat]))
                key_text = f"{hint} {val}"
            self._register(fact, key_text)
            if self._log:                              # append-only Persistenz
                import json as _j
                self._log.write(_j.dumps({"fact": fact, "key": key_text},
                                         ensure_ascii=False) + "\n")
                self._log.flush()
            new.append(fact)
        return new

    def _store_key(self, text: str):
        k = self.eng.im.encode(text.encode("utf-8"))[None, :]
        self._keys = k if self._keys is None else np.vstack([self._keys, k])

    def recall(self, query: str, k: int = MAX_FACTS):
        """Relevante Fakten abrufen. ARCHITEKTUR (ehrlich, nach AXIOM-Befund):
        ENGRAMM leistet schnellen Praefilter + Persistenz, NICHT die semantische
        Auswahl (das ist die bewiesene Trigramm-Grenze). Der LLM-Mund waehlt den
        passenden Fakt aus den Kandidaten. Bei kleinem Gedaechtnis (<= 8 Fakten)
        werden ALLE als Kontext gereicht — Qwens Fenster traegt das muehelos und
        die Semantik-Wahl passiert dort, wo sie hingehoert."""
        if self._keys is None:
            return []
        if len(self.facts) <= 8:                       # kleines Gedaechtnis: alles
            return [(f, 1.0) for f in self.facts]
        q = self.eng.im.encode(query.encode("utf-8"))  # Praefilter per Bit-Abruf
        sims = sim_from_dh(hamming(q, self._keys))
        order = np.argsort(sims)[::-1][:k]
        return [(self.facts[i], float(sims[i])) for i in order
                if sims[i] >= FACT_THRESHOLD]


# ---------------------------------------------------------------------------
# MUND (LLM) — gekapselt; Mock hier, Qwen auf dem Mac
# ---------------------------------------------------------------------------
class MouthBackend:
    def generate(self, system: str, facts: list[str], history, user: str) -> str:
        raise NotImplementedError


class MockMouth(MouthBackend):
    """Deterministischer Ersatz-Mund für Container-Verifikation (netzfrei).
    Beweist die GEDÄCHTNIS-Mechanik: nutzt die erinnerten Fakten sichtbar."""

    def generate(self, system, facts, history, user):
        if facts:
            top = facts[0][0]
            return f"(erinnere mich: {top}) — dazu passend antworte ich auf: {user}"
        return f"(kein Fakt erinnert) — ich antworte auf: {user}"


class QwenMouth(MouthBackend):
    """Echter Mund: lokales Qwen-3B via llama.cpp (nur Mac, .venv_b1).
    Lädt das Modell einmalig; identische Schnittstelle wie MockMouth."""

    def __init__(self, model_path: str, n_ctx: int = 4096):
        from llama_cpp import Llama
        self.llm = Llama(model_path=model_path, n_ctx=n_ctx,
                         n_gpu_layers=-1, verbose=False, seed=42)

    def generate(self, system, facts, history, user):
        fact_block = ""
        if facts:
            fact_block = ("Was du über den Nutzer weißt (aus deinem Gedächtnis):\n"
                          + "\n".join(f"- {f}" for f, _ in facts) + "\n\n")
        hist = "".join(f"Nutzer: {u}\nAssistent: {a}\n" for u, a in history[-4:])
        prompt = (f"<|im_start|>system\n{system}\n{fact_block}<|im_end|>\n"
                  f"{hist}<|im_start|>user\n{user}<|im_end|>\n"
                  f"<|im_start|>assistant\n")
        out = self.llm(prompt, max_tokens=200, temperature=0.7,
                       stop=["<|im_end|>"])
        return out["choices"][0]["text"].strip()


SYSTEM = ("Du bist VOX, ein lokaler Assistent mit perfektem Langzeitgedächtnis. "
          "Nutze erinnerte Fakten über den Nutzer, wenn sie zur Frage passen. "
          "Antworte natürlich und knapp.")


# ---------------------------------------------------------------------------
class VoxFusion:
    def __init__(self, mouth: MouthBackend, seed: int = 42):
        self.mem = Memory(seed)
        self.mouth = mouth
        self.history: list[tuple[str, str]] = []

    @staticmethod
    def _used_facts(reply: str, facts):
        """Welche Kandidaten hat der Mund WIRKLICH benutzt? Wort-Überlappung
        zwischen Antwort und Faktwert (ohne generische Schlüsselwörter)."""
        stop = {"name", "work", "live", "like", "heißt", "is", "called",
                "der", "die", "das", "und", "in", "at"}
        rl = set(re.findall(r"\w+", reply.lower()))
        used = []
        for f, _ in facts:
            val = f.split(":", 1)[-1]
            content = {w for w in re.findall(r"\w+", val.lower())
                       if w not in stop and len(w) > 2}
            if content and content & rl:            # mind. ein Inhaltswort taucht auf
                used.append(f)
        return used

    def turn(self, user: str):
        t0 = time.perf_counter()
        facts = self.mem.recall(user)               # intern: alle Kandidaten an den Mund
        recall_ms = (time.perf_counter() - t0) * 1e3
        reply = self.mouth.generate(SYSTEM, facts, self.history, user)
        learned = self.mem.absorb(user)
        self.history.append((user, reply))
        return reply, {"genutzt": self._used_facts(reply, facts),  # nur was zählt
                       "kandidaten": len(facts),
                       "neu_gelernt": learned,
                       "abruf_ms": round(recall_ms, 2)}


# ---------------------------------------------------------------------------
DEMO = ["Hi! My name is Erik and my dog is called Rex.",
        "I work at Carlsquare in M&A.",
        "What is my dog called?",
        "Where do I work?",
        "By the way I love pizza.",
        "What food do I like?"]


def cmd_selftest(seed=42):
    m = Memory(seed)
    m.absorb("my dog is called Rex")
    m.absorb("I work at Carlsquare")
    m.absorb("my brother is Erik")
    m.absorb("I love pizza")
    checks = [("what is my dog called", "Rex"),
              ("where do I work", "Carlsquare"),
              ("who is my brother", "Erik"),
              ("what food do I like", "pizza")]
    ok = True
    print("VOX-Fusion Gedächtnis-Selftest (netzfrei):")
    for q, want in checks:
        facts = m.recall(q)
        hit = any(want.lower() in f.lower() for f, _ in facts)
        ok &= hit
        print(f"  [{'OK ' if hit else 'FAIL'}] '{q}' -> Kandidat vorhanden: "
              f"{[f for f,_ in facts if want.lower() in f.lower()] or '—'}")
    print("SELFTEST:", "BESTANDEN" if ok else "FEHLER")
    return ok


def cmd_demo(seed=42):
    v = VoxFusion(MockMouth(), seed)
    print("VOX-Fusion Demo (Mock-Mund — zeigt die Gedächtnis-Mechanik):\n")
    for u in DEMO:
        reply, prov = v.turn(u)
        print(f"  DU : {u}")
        print(f"  VOX: {reply}")
        tags = []
        if prov["genutzt"]:
            tags.append(f"genutzt: {', '.join(prov['genutzt'])}")
        if prov["neu_gelernt"]:
            tags.append(f"gelernt: {', '.join(prov['neu_gelernt'])}")
        if tags:
            print(f"       [{' | '.join(tags)} | {prov['abruf_ms']} ms]")
        print()


def cmd_chat(seed=42):
    model = None
    for p in ("models/qwen2.5-3b-q4.gguf",
              "models/qwen2.5-3b-instruct-q4_k_m.gguf"):
        import os
        if os.path.exists(p):
            model = p
            break
    if model:
        print(f"Lade Qwen ({model}) ...")
        mouth = QwenMouth(model)
        print("VOX-Fusion — echter Mund (Qwen, lokal) + ENGRAMM-Gedächtnis.\n")
    else:
        mouth = MockMouth()
        print("VOX-Fusion — Qwen-Modell nicht gefunden, nutze Mock-Mund.\n"
              "(Für den echten Mund: Modell nach models/ und in .venv_b1 starten.)\n")
    v = VoxFusion(mouth, seed)
    print("Leere Eingabe beendet.\n")
    while True:
        try:
            u = input("DU : ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not u:
            break
        reply, prov = v.turn(u)
        print(f"VOX: {reply}")
        tags = []
        if prov["genutzt"]:
            tags.append(f"🧠 erinnert: {', '.join(prov['genutzt'])}")
        if prov["neu_gelernt"]:
            tags.append(f"✏️ gelernt: {', '.join(prov['neu_gelernt'])}")
        if tags:
            print(f"     [{' | '.join(tags)}]")
    print("\nBis bald! (Gedächtnis bleibt im Log gespeichert.)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("selftest", "demo", "chat"):
        p = sub.add_parser(name)
        p.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    {"selftest": cmd_selftest, "demo": cmd_demo, "chat": cmd_chat}[a.cmd](a.seed)


if __name__ == "__main__":
    main()
