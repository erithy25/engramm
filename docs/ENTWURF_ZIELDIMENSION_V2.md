# ENTWURF — Zieldimension V2 (Neuverhandlung nach M3-Krise)

**Status: ENTWURF.** Entscheidung liegt bei Projektleitung + Missionskontrolle.
**Keine stille Einarbeitung in D1/D5** — dieser Vorschlag wird erst nach expliziter
Freigabe kanonisch. Auslöser: M3-Krise (D6 §7; R-1 + R-2 ausgelöst, Falsifikation
§6.2 getroffen). Datum: 2026-07-06.

---

## Warum überhaupt neu verhandeln

Die M3-Messung hat gezeigt: die vorregistrierte „Vergessens"-Metrik
(acc-Abfall über Tranchen, +10,00 pp) ist **fehlspezifiziert**. Sie vermengt
zwei Effekte:

- **Verwechslungs-Verdrängung** (Score-Raum verdichtet bei wachsendem K): ~8 pp — kein Informationsverlust.
- **Echtes Interferenz-Vergessen** (T2 überschreibt Alt-Prototypen): ~2 pp.

T1 ist append-only und kann mechanisch nicht vergessen; die T1-only-Ablation
(+8,00 pp) beweist, dass die Metrik überwiegend Verdrängung misst. Die
Zieldimension „Lernen ohne Vergessen" meint aber nur den zweiten Effekt.
Die **Operationalisierung** muss korrigiert werden — nicht die Ambition.

---

## Vorgeschlagene Operationalisierung V2

**(i) Zustands-Invarianz [BEWIESEN, M3 @1000].**
Sequenzieller und gemischter (Batch-)Aufbau erzeugen **bit-identische** Prototypen
(A) **und** identische Episoden-Multimenge. Das ist die architektonische Kernaussage,
die ein Gradientensystem strukturell nicht bietet (Reihenfolge-Unabhängigkeit des
gelernten Zustands). Bereits erfüllt.

**(i-b) Auslese-Determinismus [OFFEN, Fix M4 — W19].**
Trotz bit-identischem Zustand weicht die *Klassifikation* unter Episoden-Umordnung
um 0,03 pp ab (M3-orderinv @1000: 577 vs. 580 Treffer). Ursache: `argpartition`-
Tie-Break über die Episoden-Array-Reihenfolge (W19, gleiche Wurzel wie W15).
Kriterium: nach deterministischem Tie-Break (Sortierung nach (d_H, Episoden-ID),
M4-Arbeitspaket) ist die Auslese bitgenau reihenfolge-invariant. **Nach dem Fix
sind (i) und (i-b) zusammen bitgenau.**

**(ii) Interferenz-Vergessen (korrigierte Kernmetrik).**
Interferenz-Vergessen := (acc der vollen Pipeline) − (acc T1-only) **auf einem
festen Altblock** nach Hinzulernen weiterer Klassen. Kriterium: **≤ 1 pp**.
Isoliert echte T2-Interferenz von Verdrängung. M3-Datenpunkt: ~2 pp (knapp über
Schwelle; Kandidat für T2-klassenlokal-Beschränkung, D5-§4-No-Go-Pfad, sofern
nach Neuverhandlung noch verfolgt).

**(iii) Nischen-Verengung nach R-1.**
Absolut-Nutzschwelle gilt nur noch für **strukturierte/symbolische Domänen**
(z. B. Sprach-ID, Logs, Records). **1000er-Stilometrie ist als zu hart dokumentiert**
(Top-1 5,94 % — Trigramm-HDC ohne gelernte Repräsentationen; Sprach-ID war der
günstige Fall). Kein Umdeklarieren: die Grenze wird ehrlich ausgewiesen, nicht
die Schwelle abgesenkt.

**(iv) M5-Kriterium-4-Anpassung [OFFENER PUNKT].**
Das M5-UND-Kriterium Nr. 4 (D5 §6) nutzt die alte, fehlspezifizierte Vergessens-
Metrik. Es muss **vor M5** auf (ii) umgestellt werden, sonst trägt M5 den Fehler
weiter. Genaue Formulierung offen — Teil dieser Neuverhandlung.

---

## Was NICHT zur Debatte steht (R5)

- Vorregistrierte M0–M3-Kriterien werden **nicht rückwirkend** geändert; die
  Messungen bleiben als registriert dokumentiert (M3 = NICHT ERFÜLLT).
- V2 gilt ausschließlich **vorwärts** (ab M5 bzw. einem etwaigen M3-Re-Run unter
  neuer, explizit als V2 gekennzeichneter Registrierung).
- Diese Datei ändert nichts an D1/D5, bis Projektleitung + Missionskontrolle
  zustimmen.
