# VORREGISTRIERUNG v2 — ENGRAMM-LM: Schreibmodus

**Status: REGISTRIERT** am 2026-09-26, vor jeder Messung dieser Studie. Die Studie
folgt aus E12 (`docs/PREREG_LM.md`, Ausgang WIDERLEGT). Sie ändert kein Urteil von E12.

## 1. Hypothese

> Im Schreibmodus — Dokument-Cache beim Schreiben aus (sein Gewicht geht an KN-5 wie bei
> jeder Komponente ohne Signal), top-p 0,8, sonst die Dekodierung aus PREREG_LM §8 —
> schreibt ENGRAMM-LM (Hauptmodell aus E12, unverändert: Seed 42, τ = 1.024, β = 8)
> Texte, die ein LLM-Richter denen von KN-5 unter derselben Dekodierung vorzieht.

## 2. Herkunft und Vorbehalt

Der Modus wurde entworfen, *nachdem* die E12-Texte gesichtet waren. Explorativ gemessen
wurde er auf val-B-Prompts: 78,3 % gegen KN-5 und 53,3 % gegen das Null-Modell. Diese
Studie prüft ihn auf **frischen** Test-Prompts, die kein Schritt von E12 gesehen hat.

## 3. Prompts

Die Test-Dokumente sind nach Near-Duplicate-Filter und Split-Hash sortiert und haben
≥ 36 Tokens (dieselbe Regel wie `experiments/lm_generate.py`). Genommen werden die
Prompts **201–400** dieser Liste; die Prompts 1–200 hat E12/P6 verbraucht. Prompt sind
jeweils die ersten 16 Tokens, die Fortsetzung umfasst 100 Tokens, Seed 42.

## 4. Kriterien

| | Vergleich | Urteile | Schwelle |
|---|---|---|---|
| **V1** (primär) | ENGRAMM-LM gegen KN-5 | 200 Prompts × 2 Reihenfolgen | Präferenz ≥ 60 % |
| **V2** (sekundär) | ENGRAMM-LM gegen Null-Modell (beide im Schreibmodus) | 100 Prompts (201–300) × 2 | Präferenz ≥ 60 % |

Richter: unabhängige Claude-Agenten, fester Prompt (`experiments/lm_judge.py`), blind,
25 Urteile je Agent. Unentschieden zählt ½. Mitberichtet wird die längste wörtliche
Übernahme aus dem Korpus je Text.

## 5. Ehrliche Erwartung

- **V1** erfüllt, etwa 75 %. Der Vorsprung kommt überwiegend aus längeren wörtlichen
  Übernahmen (∞-Gramm, gedeckelt auf 32 Tokens).
- **V2** verfehlt, etwa 50–55 %. HDC verbessert das Schreiben nicht messbar.
