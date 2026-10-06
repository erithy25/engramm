# Abschluss ENGRAMM „Verstehen“ v3.2 (Stand 6. Oktober 2026, Release v3.2.0-beta.4)

Ziel des Plans: Alltagsgespräche ohne neuronales Netz und ohne Server allgemein verstehen, aus dem Kontext schließen,
mit Quelle raten und lokal dazulernen. Messplan: `docs/PREREG_UNDERSTAND_V0.md`; alle Zahlen: `docs/EXPECTATIONS.md`;
Aufbau: `docs/SPEC_UNDERSTAND.md`.

## Ergebnis gegen die vorab festgelegten Schwellen

| Kriterium | Letzter Wert (blind, versiegelt) | Schwelle | Bewertung |
|---|---|---|---|
| Situation (Ereignisart) | 91,7 % | ≥ 85 % | erfüllt |
| Rollen (Person, Gegenstand, Körperteil) | 82,8 % | ≥ 75 % | erfüllt |
| Korrektur kehrt zurück | 2,4 % | ≤ 5 % | erfüllt |
| „vergiss das“ bitgleich | 83/83 | 100 % | erfüllt |
| unsicherer Rat ohne Quelle/Warnung | 0 | 0 | erfüllt |
| Tempo / Speicher / Paket | p95 0,19 s, 745 MB, 679 MB | ≤ 1,5 s, ≤ 1,5 GB, ≤ 4,5 GB | erfüllt |
| schwache Antworten auf frischen Gesprächen | 65–78 % in sechs Messungen (zuletzt 71,9 %) | ≤ 25 % | verfehlt |
| konkreter Rat auf eine Bitte | 1 von 72 | ≥ 60 % | verfehlt |
| Schlüsse aus dem Gespräch | 40 % | ≥ 80 %, 0 erfunden | verfehlt |

## Was gebaut ist

Situationsrahmen aus offenen Lexika und gemitteltem Perzeptron; Rollen wie ein Zuhörer sie füllt; Zusammensetzen von
Antworten; Schließen (Zeiten, Daten, Mengen, Personen, Ort, Bedingungen); Vorschläge unter Bedingungen; Rat-Schicht;
Anleitungs-Index (6 893 Wikipedia-Artikel) und Wikibooks-Schritte EN/DE, immer mit Quelle; Vorausdenken nach
Missgeschicken; lokales Lernen (Korrekturen, Wörter, Stil, Episoden, Bandit) mit bitgleichem Vergessen; Rückfrage bei
unbekannten Wörtern; Lernpakete zum geprüften Teilen; Lernstand in der App; Browser-Tests für Lernen und Rat.

## Bewusst nicht übernommen (mit Messung oder Grund)

- Handgeschriebene Handler abbauen: das allgemeine System deckt sie messbar nicht gleich gut ab.
- Deutscher Parser (UD German GSD, UAS 82 %): als Rollenquelle +1,6 Punkte für 126 MB.
- Codebuch-Nachbarn für neue Wörter: unbekannte Wörter haben keinen eigenen Token-Vektor.
- VerbNet: Lizenz in den Dateien nicht angegeben. CDC/Ready.gov: aus Rechenzentren gesperrt (HTTP 403).

## Einschätzung und nächster Schritt

Erkennen, Lernen, Vergessen, Quellen und Sicherheit funktionieren messbar. Freie Alltagsgespräche bleiben mit Regeln,
Wortlisten und linearen Modellen schwach; jede themenbezogene Runde hob die Entwicklungssätze, nicht die versiegelten.
Für die drei verfehlten Ziele gibt es zwei ehrliche Wege, beide eine Grundsatzentscheidung:

1. ein kleines lokales Sprachmodell (offline, < 1 GB) als eigene, vorregistrierte Stufe – gibt die Vorgabe „ohne
   neuronales Netz“ auf;
2. ENGRAMM als Werkzeug für Fakten mit Quelle, Gedächtnis und echtes Vergessen positionieren und das offene Gespräch
   zurückstellen.

Eine Bewertung durch Menschen (ChatBench) steht weiterhin aus; alle Gesprächszahlen stammen von einem blinden KI-Leser.
