# VORREGISTRIERUNG — ENGRAMM-Chat, Stufe 1: Nachschlagen statt Plappern

**Status: REGISTRIERT** am 2026-09-26, vor dem Bau des Index und vor jeder Messung.
Folgt auf E12/E13 (`docs/PREREG_LM.md`, `docs/PREREG_LM_V2.md`). Kein fremdes KI-Modell,
weder im System noch in der Bewertung: Die Antworten werden gegen bekannte Lösungen
geprüft, nicht von einem Richter-Modell.

## 1. Hypothese

> ENGRAMM beantwortet englische Wissensfragen, indem es in den Texten, die es gelesen hat,
> den passendsten Satz findet und ihn mit Quelle zurückgibt — allein mit Zählen
> (Wortstatistik) und seinen HDC-Bedeutungsvektoren.

Zwei Teilfragen: (a) Ist das nützlich (C1)? (b) Hilft der HDC-Teil gegenüber reiner
Wortstatistik (C2)?

## 2. System

* **Gedächtnis:** der Train-Strom des Hauptmodells (285 M Tokens), zerlegt in Sätze:
  Grenze nach einem Token, dessen Text auf `.`, `!` oder `?` endet oder einen Zeilenumbruch
  enthält, und am Dokumentende. Sätze mit mehr als 64 Tokens werden in 64er-Stücke geteilt.
* **Begriffe:** jedes Token wird auf einen Begriff abgebildet, d. h. seinen Text ohne
  Leerzeichen und in Kleinbuchstaben. Satzzeichen und reine Leerzeichen zählen nicht.
* **BM25 (Null-System):** invertierter Index Begriff → Sätze. Score
  Σ_q idf(q) · (k₁+1) / (1 + k₁·(1 − b + b·len/avglen)) über die Begriffe q der Frage, die im
  Satz vorkommen. Dabei gilt k₁ = 1,2, b = 0,75 und idf = ln(1 + (N − df + 0,5)/(df + 0,5)).
  Begriffe mit df > 5 % der Sätze werden ignoriert. Die Top-200 gehen weiter.
* **HDC-Umordnung (ENGRAMM-Chat):** Score = BM25 + α · S_HDC. S_HDC = Σ_q idf(q) · max_s
  sim(q, s) / Σ_q idf(q), mit sim = 1 − ham(eng[q], eng[s]) / 1024 (auf 0 abgeschnitten)
  über die Begriffe s des Satzes. Das ist eine weiche Wortübereinstimmung
  („born“ ≈ „birthplace“) aus den gezählten Bedeutungsvektoren (Seed 42).
  α ∈ {0, 0,5, 1, 2, 4} wird auf dem Dev-Satz gewählt (bester Hit@1, bei Gleichstand das
  kleinere α).
* **Eigene Texte:** Mit `learn` gelernte Texte werden genauso in Sätze zerlegt und bei
  jeder Frage mit durchsucht.
* **„Weiß ich nicht“:** Liegt der normierte Score (Score / Σ_q idf(q)) unter θ, antwortet
  ENGRAMM mit „I don't know“. θ wird auf Dev als kleinster Wert gewählt, bei dem die
  Präzision der gegebenen Antworten ≥ 60 % ist.
* **Antwort:** der beste Satz, mit Quelle (URL oder Wikipedia-Artikel bzw. eigener Text).

## 3. Fragen

SQuAD v1.1 (Rajpurkar et al. 2016), train + dev, geladen mit SHA-256:
- `train-v1.1.json`: `3527663986b8295af4f7fcdff1ba1ff3f72d07d61a20f487cb238a6ef92fd955`
- `dev-v1.1.json`: `95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9`

**Pool:** nur Fragen, deren Absatz in ENGRAMMs Korpus steht. Das heißt: ≥ 80 % der
13-Token-Fenster des Absatzes (Schrittweite 13) kommen wörtlich im Train-Strom vor.
Eine Vorab-Prüfung nur der Datenlage ergab: das trifft auf ≈ 18 % der Absätze zu.

**Aufteilung** über SHAKE-256 der Frage-ID: Dev = die ersten 500 Fragen in Hash-Reihenfolge
mit Hash-Bit 0, Test = die ersten 1.000 mit Hash-Bit 1. Dev dient nur der Wahl von α und θ.

**Treffer:** Eine der Goldantworten ist nach SQuAD-Normalisierung (Kleinschreibung,
Satzzeichen und Artikel entfernt, Leerraum zusammengefasst) Teilstring des normalisierten
Antwortsatzes. Hit@1 prüft den besten Satz, Hit@5 die fünf besten.

## 4. Kriterien (Test-Split)

| | Kriterium | Schwelle |
|---|---|---|
| **C1** Nützlich | Hit@1 von ENGRAMM-Chat | ≥ 30 % |
| **C2** HDC hilft | Hit@1(ENGRAMM-Chat) − Hit@1(BM25) | ≥ 2 Prozentpunkte **und** untere Grenze des gepaarten 95 %-Bootstrap-KI > 0 |
| **C3** Ehrlich | mit θ von Dev: Präzision der gegebenen Antworten | ≥ 55 % bei einer Abdeckung ≥ 25 % |
| **C4** Eigene Texte | 200 erfundene Fakten (`data/lm_facts_templates.json`), gelernt in Form A; Fragen in Form B und C: Anteil, bei dem der gelernte Satz Platz 1 ist | ≥ 80 % |
| **C5** Schnell | Median-Antwortzeit | ≤ 1 s (Container berichtet, M4 offiziell) |

Bootstrap: 2.000 Replikate über Fragen, Seed 42.

## 5. Ausgang

- **Nützlich** ist Stufe 1, wenn C1 und C3 erfüllt sind.
- **Bestätigt** ist der HDC-Beitrag nur mit C2.
- C4 und C5 werden einzeln berichtet.

## 6. Ehrliche Erwartung

| | Erwartung |
|---|---|
| Hit@1 BM25 | 30–40 % (SQuAD-Fragen teilen viele Wörter mit ihrem Satz) |
| C1 | knapp erfüllt, ≈ 60 % |
| C2 | eher verfehlt, ≈ 30 % — wie in E12 dürfte HDC nur wenig beitragen |
| C3 | erfüllt, ≈ 70 % |
| C4 | erfüllt, ≈ 85 % |
| C5 | erfüllt |

Die Antworten sind ganze Sätze, keine formulierten Antworten. Das ist Stufe 4.

## 7. Änderungsprotokoll

* v1.0 (2026-09-26): Erstregistrierung.
