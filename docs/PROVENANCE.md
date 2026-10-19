# Provenance of the preregistration

The study was developed in a repository that is now private (`erithy25/engramm-dev`). This public repository holds
the documents, the result files and the paper. This page lists where each step sits in the development history, so
that the order *registered → measured → decided* can be checked.

**How to verify:** every hash below is a commit of the development repository. Reviewers who want to check a
registration against its commit can ask for read access (open an issue). The text of `docs/PREREG_SELA2.md` in this
repository is the final version of that file; each section's registered text is unchanged since its registration
commit apart from whitespace, results were appended as subsections, and two later corrections are marked as such
(§9.1, §10.1).

SHA-256 of `docs/PREREG_SELA2.md` as published here: `6b071ad8ee8e0190297a8d8a775a52286ae0f5f0193cf552dda9d9b936054615`

## Registered measurements

| Section | Registered (commit · time) | First result file committed by the measurement workflow | Decision applied (commit · time) | Results |
|---|---|---|---|---|
| §7 | `a594d98` · 2026-10-19 00:28:53 UTC | `b12fe09` · 2026-10-19 04:41:39 UTC | `81bedb3` · 2026-10-19 04:49:16 UTC | `results/sela2/learn` |
| §8 | `b59414a` · 2026-10-19 10:20:47 UTC | `15e59bc` · 2026-10-19 10:29:24 UTC | `4472452` · 2026-10-19 10:35:52 UTC | `results/sela2/learn_v2` |
| §9 | `bed30a6` · 2026-10-19 13:02:09 UTC | `88f7f30` · 2026-10-19 13:10:12 UTC | `3c7f979` · 2026-10-19 13:20:42 UTC | `results/sela2/learn_v3_labels, learn_v3_sentences` |
| §10 | `87a4c4d` · 2026-10-19 13:22:26 UTC | `203881f` · 2026-10-19 13:30:10 UTC | `b81af24` · 2026-10-19 13:52:17 UTC | `results/sela2/learn_v4_labels, learn_v4_sentences` |
| §11 | `3fb881a` · 2026-10-19 18:10:36 UTC | `975d994` · 2026-10-19 18:19:30 UTC | `f4894d4` · 2026-10-19 18:23:52 UTC | `results/sela2/learn_real` |
| §12 | `789abea` · 2026-10-19 18:38:11 UTC | `8b4e2fc` · 2026-10-19 18:48:21 UTC | `68a2782` · 2026-10-19 18:59:10 UTC | `results/sela2/learn_real2_relevant, learn_real2_all` |

The measurement workflows ran on GitHub Actions on the code of the commit that started them and committed their result
files themselves (commit author "ENGRAMM Sela-2 evaluation").

## Every change to the preregistration file

| Commit | Time | Message (German, as written) |
|---|---|---|
| `74556b0` | 2026-10-17 13:26:23 UTC | v5: Sela-2 App-Oberfläche, Anleitung, Vorab-Registrierung, PLAN §12, CI-Prüfung mit torch 2.8 |
| `d585d39` | 2026-10-17 14:10:14 UTC | v5: Sela-2 – Befunde der drei unabhängigen Prüfungen behoben (Trainer, Pod-Skript, App) [skip ci] |
| `57bd242` | 2026-10-18 10:54:38 UTC | v5: Sela-2 Varianten-Messung – Basis, Chat und Gewichtsmischungen, Auswahlregel vorab in PREREG §5 |
| `ae78a51` | 2026-10-18 12:01:21 UTC | v5: Sela-2.1 vorab registriert (PREREG §6), Pod-Anleitung, Vergleich der Sela-2.1-Dateien gegen §5 |
| `83b2895` | 2026-10-18 13:41:51 UTC | v5: Sela-2.1 auf das Restbudget eingestellt – Kostenbremse 5 $ (≈ 75 min H100), Mindestbudget 4 $ |
| `a594d98` | 2026-10-19 00:28:53 UTC | v5: Sela-2 lernt vom Nutzer – Fakten, Gesprächsfaden, Sprachgedächtnis mit Fehlerfilter; PREREG §7 vor der Messung [skip ci] |
| `fb2ca80` | 2026-10-19 01:52:29 UTC | v5: Sela-2 lernt – 39 Befunde der unabhängigen Prüfung behoben, PREREG §7.1 vor der Messung [skip ci] |
| `f8f0cd3` | 2026-10-19 02:54:18 UTC | v5: Sela-2 lernt – zweite Prüfung, 23 weitere Punkte behoben, PREREG §7.2 vor der Messung [skip ci] |
| `480ae7c` | 2026-10-19 03:46:41 UTC | v5: Sela-2 lernt – dritte Prüfung, 21 Punkte behoben, PREREG §7.3 vor der Messung [skip ci] |
| `f8226ad` | 2026-10-19 04:36:00 UTC | v5: Sela-2 lernt – letzte Prüfung vor der Messung: Wort-Nachfrage kein Befehl, deutsche Lerntexte als Deutsch (PREREG §7.4) [skip ci] |
| `81bedb3` | 2026-10-19 04:49:16 UTC | v5: Sela-2 lernt – Ergebnis nach PREREG §7: Fakten 0 → 52,5 %, aber Rollen-Verwechslung; Regel: alles aus [skip ci] |
| `b59414a` | 2026-10-19 10:20:47 UTC | v5: PREREG Sela-2 §8 registriert – Sela-2 lernt, Fassung 2 (vor der Prüfmessung) [skip ci] |
| `4472452` | 2026-10-19 10:35:52 UTC | v5: PREREG §8.1, Modellkarte, PLAN §12.7 – Ergebnis „Sela-2 lernt“, Fassung 2: alles an [skip ci] |
| `7360145` | 2026-10-19 10:44:54 UTC | v5: Test-Build 8 der Desktop-App starten – Sela-2 lernt vom Nutzer (PREREG §8: alles an) |
| `bed30a6` | 2026-10-19 13:02:09 UTC | v5: PREREG Sela-2 §9 registriert – Notiz als Sätze, A/B-Test auf frischen Nutzern v3 (vor der Messung) [skip ci] |
| `3c7f979` | 2026-10-19 13:20:42 UTC | v5: Sela-2 lernt §9.1 – Regel angewandt: Satzform nicht übernommen, Sprachgedächtnis (C) wieder aus |
| `87a4c4d` | 2026-10-19 13:22:26 UTC | v5: PREREG Sela-2 §10 registriert – Notizform, Wiederholung auf Nutzern v4 mit einer Regel nur für A (vor der Messung) [skip ci] |
| `b81af24` | 2026-10-19 13:52:17 UTC | v5: Sela-2 lernt §10.1 – Regel angewandt: Notiz als Sätze ist jetzt Standard |
| `3fb881a` | 2026-10-19 18:10:36 UTC | v5: Sela-2 lernt §11 registriert – Sprachgedächtnis auf echten Nutzern; Prüfmessung auf den 40 echten Testnutzern starten |
| `f4894d4` | 2026-10-19 18:23:52 UTC | v5: Sela-2 lernt §11.1 – Regel angewandt: Sprachgedächtnis auf echten Nutzern bestätigt, jetzt Standard; Test-Build 10 |
| `789abea` | 2026-10-19 18:38:11 UTC | v5: Sela-2 lernt §12 registriert – Fakten nur, wenn die Nachricht davon handelt; Messung auf 40 neuen echten Testnutzern |
| `68a2782` | 2026-10-19 18:59:10 UTC | v5: Sela-2 lernt §12.1 – Regel angewandt: Fakten nur, wenn die Nachricht davon handelt (Standard); Test-Build 11 |
| `03f6c52` | 2026-10-19 20:12:29 UTC | v5: Paper fertig (16 Seiten, PDF) – KI-Rollen klar benannt, deutsche Kurzfassung; PREREG §9.1/§10.1 mit offengelegter Korrektur der L4-Zählu |
