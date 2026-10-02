# PREREG — SearchBench-EN v0: Antworten mit Internetzugang (Atlas), vorab registriert

**Registriert 2026-10-02, vor jeder Testmessung.** Gilt für ENGRAMM v3.1 mit den Kanälen aus
`docs/SPEC_ATLAS.md` (Regal, Feeds, Bote). Regeln wie in `docs/CLAUDE.md`: Schwellen stehen fest,
bevor gemessen wird; ein einziger Testlauf; kein KI-Richter; das Ergebnis kommt in
`docs/EXPECTATIONS.md`, auch wenn es danebenliegt.

## Frage

Beantwortet ENGRAMM mit eingeschaltetem Internetzugang belegte Faktenfragen **korrekt und belegt**, auch
aktuelle und seltene — ohne dass eine Frage den Rechner verlässt?

## Daten (noch nicht erstellt — Voraussetzung für den Testlauf)

- **SearchBench-EN:** 400 von Menschen geschriebene englische Fragen, je mit Referenzantwort und Quelle,
  geschrieben ohne Zugriff auf ENGRAMM:
  - 160 **aktuell** (Ereignisse oder Werte nach dem 1. Januar 2023),
  - 120 **Langschwanz** (Gegenstand nicht unter den 400.000 Artikeln des Lite-Pakets),
  - 120 **allgemein**.
- Aufteilung 100 Entwicklung / 300 Test; die Testfragen werden versiegelt (SHA-256 im Repo) und erst für den
  einen Lauf geöffnet.
- **Bewertung:** zwei Menschen je Antwort, blind gegenüber dem System; Kategorien *richtig und belegt*,
  *richtig*, *falsch*, *keine Antwort*. Ein belegtes Zitat zählt als *richtig und belegt*, wenn der zitierte
  Satz die Frage beantwortet. Uneinigkeit: dritte Person entscheidet.

## Systeme

1. **v3 offline** (Lite-Paket, alle Kanäle aus) — Grundlinie.
2. **v3.1 Atlas** (Lite-Paket + Lite-Regalindex; Regal und Feeds an, Bote an über Tor).
3. Optional als Gegner, nie als Richter: ein Chat-Assistent mit Websuche.

## Schwellen (fest, vor der Messung)

| # | Kriterium | Schwelle |
|---|---|---|
| S1 | Exaktheit: Anteil *falsch* unter allen gegebenen Antworten (System 2) | ≤ 5 % |
| S2 | Langschwanz: Anteil *richtig und belegt*, System 2 minus System 1 | ≥ +20 Prozentpunkte |
| S3 | Aktuell: Anteil *richtig und belegt* (System 2) | ≥ 30 % |
| S4 | Privatsphäre: Abrufe im Netzprotokoll, die Text der Frage enthalten (alle 300 Fragen) | 0 |
| S5 | Kanäle aus: Antworten von System 2 mit ausgeschalteten Kanälen identisch zu System 1 | 300 / 300 |
| S6 | Antwortzeit Regal (Fach nicht im Cache), p95, 50 Mbit/s | ≤ 2 s |

Bestanden ist v0, wenn S1, S4 und S5 halten; S2, S3, S6 werden berichtet und entscheiden über den
nächsten Schritt (Standard-Paket, Quellen-Abgleich).

## Was schon gemessen wurde (Entwicklung, verbrauchte Daten — kein Testlauf)

Siehe `docs/EXPECTATIONS.md` E30: Konfidenzmodell auf SQuAD-train, Ende-zu-Ende-Batterie mit 12 Fragen
an einem echten Regal aus Shard 0. Diese Zahlen sind Entwicklungsstand und zählen nicht für S1–S6.

## Stand

Registriert; Testdaten und menschliche Bewertung stehen aus. Der Lauf findet statt, sobald das Regal für
ganz Wikipedia veröffentlicht ist (`.github/workflows/shelf.yml`) und die 400 Fragen geschrieben sind.
