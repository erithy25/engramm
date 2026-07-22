#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spielwiese.py — ENGRAMM manuell testen (Projekt AXIOM)
Ins selbe Verzeichnis wie engramm.py legen, dann:  python3 spielwiese.py

Zwei Regeln fuer gute Ergebnisse (aus dem Praxistest gelernt!):
  1. Genug Text pro Beispiel: 1-2 volle Saetze, nicht drei Woerter.
     Das System zaehlt Buchstaben-Trigramme — Statistik braucht Laenge.
  2. UNGERADE Anzahl Beispiele pro Klasse (3, 5, 7 ...).
     Bei gerader Anzahl entstehen Unentschieden-Bits, die alle Klassen
     mit demselben Fuellvektor auffuellen — Prototypen verschwimmen.
"""
from engramm import ItemMemory, Engramm

eng = Engramm(ItemMemory(42))

# ---------------------------------------------------------------------------
# 1) BEIBRINGEN — hier eigene Klassen und Beispiele eintragen (je 3 Stueck!)
# ---------------------------------------------------------------------------
BEISPIELE = {
    "deutsch": [
        "guten morgen zusammen, ich hoffe ihr hattet alle ein schoenes wochenende und seid gut erholt",
        "koenntest du mir bitte kurz helfen, ich finde meinen schluessel schon seit heute morgen nicht mehr",
        "das essen gestern abend war wirklich ausgezeichnet, besonders die suppe hat mir sehr gut geschmeckt",
    ],
    "englisch": [
        "good morning everyone, i hope you all had a wonderful weekend and feel well rested today",
        "could you please help me for a moment, i have not been able to find my keys since this morning",
        "the dinner last night was truly excellent, i especially enjoyed the soup very much indeed",
    ],
    "spanisch": [
        "buenos dias a todos, espero que hayan tenido un fin de semana maravilloso y esten descansados",
        "podrias ayudarme un momento por favor, no encuentro mis llaves desde esta manana",
        "la cena de anoche estuvo realmente excelente, la sopa me gusto muchisimo de verdad",
    ],
}

for label, texte in BEISPIELE.items():
    for t in texte:
        # Lernen = Schreiben. Millisekunden.
        eng.learn(t.encode(), label)
print(
    f"Gelernt: {len(eng.labels)} Klassen, {eng.keys.shape[0]} Erinnerungen.\n")

# ---------------------------------------------------------------------------
# 2) ABFRAGEN — interaktiv. Extra-Trick: live dazulernen mit
#       lerne <klasse>: <satz>
#    (neue Klasse ist SOFORT nutzbar — kein Training, das ist der Punkt!)
# ---------------------------------------------------------------------------
print("Satz eingeben  ->  ENGRAMM raet die Klasse.")
print("Dazulernen:    lerne <klasse>: <satz>      Beenden: leere Eingabe\n")

while True:
    try:
        zeile = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not zeile:
        break
    if zeile.lower().startswith("lerne ") and ":" in zeile:
        kopf, satz = zeile.split(":", 1)
        klasse = kopf[6:].strip()
        eng.learn(satz.strip().encode(), klasse)
        print(f"  [gemerkt als '{klasse}' — sofort einsatzbereit]")
        continue
    label, scores = eng.classify(zeile.encode())
    top = sorted(zip(eng.labels, scores), key=lambda x: -x[1])[:3]
    print("  -> " + "   ".join(f"{l}: {s:+.3f}" for l, s in top))

print("Bis bald!")
