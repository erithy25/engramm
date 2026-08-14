# AUDIT — Bestandsaufnahme ENGRAMM

**Datum:** 2026-08-14 · **Auditierter Stand:** `a1af719` („Recover ENGRAMM: core, milestone
harnesses M0-M5, project documents") · **Auftrag:** Schritt 1 (Bestandsaufnahme) von
Reproduzierbarkeits-Audit · **Prüfer:** Claude Code (Sitzung `claude/engramm-reproducibility-audit-y94aa7`)

---

## 0. Kernbefund — vorweg, weil er alles Weitere bestimmt

**Dieses Repository enthält die ENGRAMM-Implementierung nicht.** Es enthält *Bruchstücke*
davon. Die beiden dokumentierten Zahlen (79,30 % WiLI-2018, 94,62 % MNIST) sind aus diesem
Repository heraus **weder reproduzierbar noch falsifizierbar** — nicht, weil sie falsch wären,
sondern weil der Code, der sie erzeugt hat, nicht eingecheckt ist.

Die drei harten Belege:

| Beleg | Befund |
|---|---|
| Kern-Modul | `engramm.py` ist laut D1/D4 **469 Zeilen**. Im Git liegen **17 Zeilen** — eine einzelne Methode (`learn_online`), ohne `class`-Kopf, ohne Imports, ohne `ItemMemory`, ohne `Engramm`. |
| WiLI-Harness | Existiert **überhaupt nicht**. Es gibt keine Datei, die die 79,30 % erzeugt. Kein `m1_wili.py`, kein anderer Kandidat. |
| MNIST-Harness | `m1b_mnist.py` hat **9 Zeilen** — das Ende einer Auswertungsfunktion, die Mittelwerte druckt. Weder Datenladen noch Encoder noch Trainingsschleife sind vorhanden. |

**5 von 12 `.py`-Dateien sind nicht einmal syntaktisch parsbar** (`IndentationError` in Zeile 1,
weil die Datei mitten in einem Block beginnt). Von den 7 parsbaren sind 4 Duplikate desselben
Nebenprojekts (`vox_fusion`). Es gibt **keine einzige lauffähige Datei**, die ENGRAMM benutzt.

**Konsequenz:** Schritt 2 (Reproduzierbarkeit), Schritt 3 (Korrektheitsprüfung im Code) und
Schritt 4 (Verifikationslauf mit 5 Seeds) sind in der beauftragten Form **nicht ausführbar**.
Es gibt nichts zu seeden, nichts zu pinnen, nichts zu messen. Details und Optionen: §8.

**Was das ausdrücklich *nicht* heißt:** Es ist kein Hinweis darauf, dass die Zahlen erfunden
sind. Die Dokumentation ist detailliert, intern konsistent, nennt Messprotokolle, Hardware,
Bibliotheksversionen, Datum, Laufzeiten pro Seed, und dokumentiert an mehreren Stellen
Ergebnisse, die dem Projekt schaden (§7.3). Das ist mit einer echten Messung gut vereinbar.
Es ist nur eben kein Beweis — und nachprüfen lässt es sich hier nicht.

---

## 1. Wie es zu diesem Zustand kam (Rekonstruktion)

Neben jeder Quelldatei liegt eine `<datei>.edits.json`. Inhalt, Beispiel aus
`engramm.py.edits.json`:

```json
{ "replace_all": false,
  "file_path": "/Users/erikthye/engramm/engramm.py",
  "old_string": "    def consolidate(self, theta_merge: float = 0.12, ...",
  "new_string": "    def consolidate(self, theta_merge: float = 0.12, ..." }
```

Das sind **Protokolle von Claude-Code-`Edit`-Aufrufen** einer früheren Sitzung auf dem Mac
(`/Users/erikthye/engramm/`) — `old_string`/`new_string`-Paare, kein Quelltext.

Damit ist der Hergang klar: Der Commit `a1af719` heißt „Recover ENGRAMM" und ist der Versuch,
das Projekt **aus einem Edit-Log zu rekonstruieren**, nachdem der eigentliche Arbeitsbaum
verloren ging. Rekonstruiert werden konnte nur, was zufällig in einem `new_string` stand —
also genau die Stellen, die einmal bearbeitet wurden, und sonst nichts. Deshalb beginnt
`engramm.py` mitten in einer Methode: `learn_online` war der letzte bearbeitete Block.

Die Git-Historie bestätigt es — eine vollständige Fassung war **nie** eingecheckt:

```
13f7832 Initial commit                                    README.md (2 Zeilen)
e94f74a Add README, measurement harnesses and protocols    README.md (+52 Zeilen)   ← nur README
a1af719 Recover ENGRAMM: ...                               alle Fragmente + edits.json
```

Der Commit `e94f74a` verspricht im Titel „measurement harnesses and protocols", ändert aber
ausschließlich `README.md`. Die Harnesses waren zu keinem Zeitpunkt im Repository.

---

## 2. Struktur — welche Datei was tut

### 2.1 Fragmente (nicht ausführbar, nicht importierbar)

| Datei | Zeilen | Was tatsächlich drinsteht | Was fehlt |
|---|---|---|---|
| `engramm.py` | 17 | Methode `learn_online` (T2-Perceptron-Update) | **Der gesamte Kern**: `ItemMemory`, `Engramm`, `hamming`, `sim_from_dh`, `popcount_rows`, `encode_signed`, `_scores`, `_rebinarize`, `_ensure_class`, `classify`, `learn`, `consolidate`, Konstante `UTIL_CLIP` |
| `m1b_mnist.py` | 9 | Schlussblock der Seed-Auswertung (Mittelwert/SD-Druck, Kriteriumsprüfung) | Datenladen, Thermometer-Encoder (`PixelLevelMemory`), T1/T2-Schleifen, Zeitmessung, `main()`, Argumente |
| `m2_stream.py` | 10 | Funktion `evaluate()` (zählt Treffer je Quelle b77/wili) | `load_banking77()` — von `m5_baselines.py` importiert —, Streamaufbau, T3-Konsolidierung |
| `m5_engramm.py` | 9 | Schlussblock: baut `meta`-Dict, schreibt `logs/..._meta.json` | `fewshot_split()`, `load_clinc()` — beide von `m5_baselines.py` importiert —, gesamter Messpfad |
| `m5_compare.py` | 10 | Endauswertung: Ausgangs-Klassifikation (1)/(2)/(3) | Einlesen der Meta-JSONs, Berechnung von `c1..c4`, `gap` |
| `vox_fusion-5.py` | 13 | Nur die `FACT_PATTERNS`-Regex-Liste | Alles andere |
| `m3.py` | 21 | `main()` mit vollständigem Argparse (`prepare`/`run`/`orderinv`) | `import argparse`, `cmd_prepare()`, `cmd_run()`, `cmd_orderinv()` — parst zufällig, läuft aber nicht |

`m3.py` ist der einzige Sonderfall: er *importiert* ohne Fehler, weil das Fragment nur
Funktionsdefinitionen enthält. Ein Aufruf schlägt sofort mit `NameError` fehl.

### 2.2 Vollständige Dateien (syntaktisch intakt, trotzdem nicht lauffähig)

| Datei | Zeilen | Zweck | Warum trotzdem tot |
|---|---|---|---|
| `m5_baselines.py` | 279 | M5-Gegner-Baselines B1 (bge+FAISS+Qwen-3B-RAG) und B3 (LoRA auf Qwen-0.5B) | `from m5_engramm import fewshot_split, load_clinc` und `from m2_stream import load_banking77` → beide Ziele sind Fragmente ohne diese Funktionen |
| `spielwiese.py` | 71 | Interaktive Handprobe (3 Sprachen lernen, dann raten) | `from engramm import ItemMemory, Engramm` → `IndentationError` |
| `vox_fusion-2/-3/-4.py` | 313/347/429 | Nebenprojekt VOX: lokales Qwen als „Mund", ENGRAMM als Faktengedächtnis | `from engramm import Engramm, ItemMemory, hamming, sim_from_dh` → dito |

Diese Dateien sind vollständig, weil sie in der Ursprungs-Sitzung per `Write` (nicht `Edit`)
erzeugt wurden — sie standen daher komplett im Log.

### 2.3 In der Doku benannte, komplett fehlende Harnesses

| Datei | Erzeugt laut Doku |
|---|---|
| `m0_bench.py` | M0-Recall-Audit: 95,57 % Recall @ ef=128, 27,4 mJ/Query (README-Zeile 3) |
| `m2b.py` | M2b Verdrängung + L2-Persistenz („Exact crash-replay proven", README) |
| `vox_fusion.py` | VOX-Fusion — existiert nur als 4 unbenannte Versionsstände `-2` … `-5` |
| **kein Name bekannt** | **M1/WiLI — die 79,30 %.** In keinem Dokument wird ein Dateiname genannt. |

### 2.4 Dokumente

Auch die D-Dokumente sind Fragmente: `D1_MANIFEST.md` beginnt bei „## 5." und endet mitten im
Satz („…existiert und wurde ausgeführt:"), `D2_SPEC.md` beginnt mitten im Pseudocode,
`D8_AUDIT.md` beginnt bei Prognose P4. Vollständig sind nur `ENTWURF_ZIELDIMENSION_V2.md` (70
Z.), `PROJECT_NOTES.md`, `CLAUDE.md`, `README.md`.

**Wichtig:** Die `.edits.json`-Dateien enthalten inhaltlich **mehr** als die zugehörigen
`.md`-Dateien (z. B. `D4_PROTOTYP.md` = 5 Zeilen, `D4_PROTOTYP.md.edits.json` = 38 KB mit
kompletten Ergebnistabellen). Der größte Teil der inhaltlichen Substanz dieses Projekts steckt
derzeit in den Edit-Logs, nicht in den Dokumenten. Alle Zitate in §7 stammen daher aus den
Edit-Logs.

---

## 3. Datenladen, Split, Vorverarbeitung

**Befund: Im gesamten Repository existiert kein einziges Stück Datenlade-Code.**

Systematische Suche über alle `.py`-Dateien *und* alle `.edits.json`-Logs nach:

```
load_wili · load_mnist · train_test_split · test_size · shuffle · default_rng
np.random.seed · random.seed · normali* · vocab · fit_transform · StandardScaler
```

→ **kein einziger Treffer.** Nicht im Code, nicht in den Edit-Logs.

Was sich über die Datenbehandlung sagen lässt, stammt ausschließlich aus Prosa:

| Aspekt | Dokumentierte Angabe | Quelle |
|---|---|---|
| WiLI-Setup | „235-Sprachen-10-shot", 10 Beispiele pro Sprache | `D1_MANIFEST.md.edits.json` |
| WiLI-Vorabmessung | „10 Beispiele pro Sprache: 78,5 % Top-1", Zufallsniveau 0,4 % | `D1_MANIFEST.md.edits.json` |
| MNIST-Split | „volle Größe (train=60.000, test=10.000)" | `D4_PROTOTYP.md.edits.json` |
| MNIST-Encoding | „Q=16-Stufen-Thermometer-Encoding", `PixelLevelMemory`: Position ⊗ Level, Mehrheitsbündelung, „per Duck-Typing injiziert" | `D4_PROTOTYP.md.edits.json` |
| M5-Few-Shot-Split | Signatur `fewshot_split(xtr, ytr, shots, seed)` — nimmt einen Seed, zieht aus **`xtr`** | Aufruf in `m5_baselines.py:42` |
| M0-Datenbasis | „10⁶ reale WiLI-Fenster-Keys", Integritätsanker `md5(keys[:1000]) = 709c995db1f227cd6722055e5536d20a` | `D5_EXPERIMENTE.md.edits.json` |

`data/` steht in `.gitignore` — es liegen also weder Rohdaten noch ein Download-Skript noch ein
Prüfsummen-Manifest vor. Ein Downloadpfad für WiLI-2018 oder MNIST ist nirgends dokumentiert.

Der einzige verwertbare Code-Beleg ist der Aufruf `fewshot_split(xtr, ytr, shots, seed)` in
`m5_baselines.py:42`: Er zieht die Few-Shot-Beispiele nachweislich aus dem **Train-Teil** und
nimmt einen **Seed** entgegen. Das ist ein positives Signal — es betrifft aber M5
(Banking77/CLINC150), **nicht** die beiden auditierten Benchmarks.

---

## 4. Wo genau die dokumentierten Zahlen produziert werden

| Zahl | Erzeugender Code | Status |
|---|---|---|
| **79,30 % WiLI** | unbekannt — nirgends benannt | **fehlt vollständig** |
| **94,62 % MNIST** | `m1b_mnist.py`, Seed 42 | **9-Zeilen-Fragment** |
| 95,57 % Recall / 27,4 mJ | `m0_bench.py` | **fehlt vollständig** |
| 62,6 % / 69,0 % (M5) | `m5_engramm.py` | **9-Zeilen-Fragment** |
| M2a-Kollaps, M2b-Replay | `m2_stream.py`, `m2b.py` | Fragment / fehlt |
| M3-Ordnungsinvarianz | `m3.py` | Fragment (nur `main()`) |

**Keine einzige Zahl des Projekts ist an ausführbaren Code gebunden.**

Zusätzlich fehlen die Rohbelege: `logs/` ist gitignored, ein `results/`-Verzeichnis existiert
nicht. Die in den Dokumenten referenzierten Belegdateien (`logs/m3_t2local.log`,
`logs/m5_engramm_*_meta.json`, `logs/m5_b1_powermetrics_raw.log`) sind sämtlich nicht vorhanden.
Es gibt damit **weder Code noch Rohdaten noch Logs** — die Zahlen existieren ausschließlich als
Prosa in den Edit-Logs.

---

## 5. Abhängigkeiten und Versionen

**Es gibt kein Dependency-Manifest.** Kein `requirements.txt`, keine `pyproject.toml`, kein
`setup.py`, kein `environment.yml`, kein `Pipfile`, kein Lockfile. **Null Pins.**

Aus Code-Imports rekonstruiert:

| Paket | Von | Version gepinnt? |
|---|---|---|
| `numpy` | überall | nein |
| `faiss` | `m5_baselines.py` (B1), `m0_bench.py` (fehlt) | nein |
| `sentence-transformers` | `m5_baselines.py` | nein |
| `llama-cpp-python` | `m5_baselines.py` | nein |
| `torch`, `transformers`, `peft` | `m5_baselines.py` (B3) | nein |

Versionen sind **nur in Prosa** dokumentiert (in den Messprotokoll-Absätzen, R6):

> Apple M4, 10 Kerne, 16 GB RAM · Python **3.13.7** · NumPy **2.4.1** · FAISS-CPU **1.14.3** ·
> llama-cpp-python **0.3.33** (Metal) · Qwen2.5-3B-Instruct-Q4_K_M · 2026-07-06/07

Das ist mehr als bei vielen Projekten — aber es ist keine installierbare Umgebung.

Weitere Reproduzierbarkeits-Hindernisse:

- **Modellgewichte**: `m5_baselines.py` erwartet `models/qwen2.5-3b-q4.gguf` (lokaler Pfad, nicht
  im Repo, keine Bezugsquelle, keine Prüfsumme).
- **Plattformbindung**: `_pkg_power_mw()` ruft `sudo powermetrics` — macOS-only, benötigt
  Root. Die Energiemessung ist auf keiner anderen Plattform reproduzierbar.
- **Zwei getrennte Umgebungen**: Doku nennt System-Python 3.13 für ENGRAMM und eine isolierte
  `.venv_b1` (Python 3.12) für die Baselines. Keine der beiden ist spezifiziert.
- **Aktuelle Sandbox**: Python 3.11.15, **NumPy nicht installiert**. Selbst ein vollständiges
  `engramm.py` liefe hier ohne `pip install` nicht.

---

## 6. Ist der Zufall kontrolliert?

**Aus dem Code nicht feststellbar** — es gibt keinen Seed-setzenden Code im Repository.

Belege, die *für* eine kontrollierte Zufallsbehandlung sprechen (alle indirekt):

- `spielwiese.py:16` → `Engramm(ItemMemory(42))`: Der Item-Memory nimmt einen Seed als
  **erstes Konstruktor-Argument**. Die Zufallshypervektoren sind also seed-gesteuert.
- `m5_baselines.py:177` → `torch.manual_seed(seed)` im B3-Pfad (Baseline, nicht ENGRAMM).
- `m5_baselines.py:155` → `np.random.default_rng(0)` im Energie-Lastgenerator.
- `fewshot_split(xtr, ytr, shots, seed)` — Split ist seed-parametrisiert.
- Alle Harnesses haben `--seed`-Argumente mit Default 42 (`m3.py:8`, `m5_baselines.py`).
- Dokumentierte Seed-Menge: **42, 7, 1337, 2026, 99**.
- Dokumentierter Determinismus-Nachweis: „Seed 42 = 94,62 % (9462/10000) bitgleich zum
  offiziellen Lauf (W15-Determinismus, plattformintern)" und der M0-Integritätsanker
  `md5(keys[:1000]) = 709c99…d20a`, „plattformübergreifend deterministisch bestätigt".

**Bekannte, vom Projekt selbst dokumentierte Determinismus-Lücken:**

- **W19/W15 — Tie-Break-Nichtdeterminismus:** `ENTWURF_ZIELDIMENSION_V2.md:34-40`. Trotz
  bit-identischem Zustand weicht die *Klassifikation* unter Episoden-Umordnung um 0,03 pp ab
  (577 vs. 580 Treffer). Ursache: `argpartition`-Tie-Break über die Episoden-Array-Reihenfolge.
  Fix ist für M4 vorgemerkt, **derzeit offen**. Das heißt: Die Ergebnisse sind bei identischer
  Eingabereihenfolge reproduzierbar, aber **nicht ordnungsinvariant** — die im README genannte
  Eigenschaft „Order-invariance proven bit-identical" (M3) gilt laut Projekt selbst für den
  *Zustand* (Prototypen A + Episodenmenge), **nicht** für die Auslese.
- **W14 — Tie-Vektor-Kopplung:** Bei gerader Shot-Zahl teilen sich alle Klassen denselben
  Füllvektor; bei 2 Shots/Klasse dokumentierter „Kollaps auf eine Klasse". Ab ~10 Shots
  irrelevant — die beiden auditierten Benchmarks liegen bei 10 Shots (WiLI) bzw. voller
  Trainingsmenge (MNIST), sind also nicht betroffen.

Nicht feststellbar: ob `random.seed()` und `PYTHONHASHSEED` gesetzt sind, ob BLAS-Threading
fixiert ist, ob der MNIST-Datenreihenfolge-Shuffle geseedet ist.

---

## 7. TODOs, toter Code, tote Pfade

### 7.1 Toter Code / Duplikate

- **`vox_fusion-2/-3/-4/-5.py`** — vier Versionsstände derselben Datei, alle mit identischem
  Docstring `"""vox_fusion.py — VOX Stufe 3b"""`. Die eigentliche `vox_fusion.py` existiert
  nicht. Diff-Abstände: `-2`→`-3` 58 Zeilen, `-3`→`-4` 156 Zeilen, `-4`→`-5` 419 Zeilen. Welche
  Fassung die gültige ist, ist nirgends vermerkt; `-5` ist ohnehin nur ein 13-Zeilen-Fragment.
  Das ist manuelle Versionierung per Dateiname — mitten in einem Git-Repository.
- **Alle 15 `.edits.json`** — Werkzeug-Artefakte ohne Funktion für das Projekt. Sie sind
  derzeit paradoxerweise die *wertvollsten* Dateien im Repo (sie enthalten die
  Ergebnistabellen), aber sie gehören nicht in den Quellbaum.
- **`m5_baselines.py:120` `_merge_meta()`** — für den B3-Pfad definiert, dort aber nicht
  benutzt (`run_b3` schreibt mit `json.dump` direkt und überschreibt damit bestehende Metadaten,
  während B1 sie zusammenführt). Inkonsistenz, kein Fehler.

### 7.2 Offene Punkte, die die Dokumente selbst benennen

| ID | Offener Punkt | Quelle |
|---|---|---|
| W19 | Auslese-Determinismus (Tie-Break) — Fix erst M4 | `ENTWURF…V2.md:34` |
| (iv) | M5-Kriterium 4 nutzt noch die als fehlspezifiziert erkannte Vergessens-Metrik; „muss **vor M5** umgestellt werden, sonst trägt M5 den Fehler weiter" | `ENTWURF…V2.md:56-59` |
| P5 | Prognose „Episodenbeitrag M3: −2 bis +3 pp" — als **offen** markiert | `D8_AUDIT.md:2` |
| W13 | „Zwei Benchmark-Familien ≠ Repräsentativität" — offen | `D6…edits.json` |
| — | `ENTWURF_ZIELDIMENSION_V2.md` und `RATIFIZIERT_ZIELDIMENSION_V2.md` liegen **beide** vor; D6 nennt die V2-Ratifizierung als vollzogen („Freigabe JA-V2"), der Entwurf trägt weiter „Status: ENTWURF". Welches Dokument kanonisch ist, ist unklar. |

### 7.3 Bewertung der Dokumentationskultur

Der Vollständigkeit halber, weil es für die Einschätzung der Zahlen relevant ist: Die
Dokumente berichten durchgängig auch Ergebnisse, die dem Projekt schaden — M2a als
„No-Go-Endpunkt" (−53 pp), M5 als „(3) NIEDERLAGE auf beiden Aufgaben", M3 als „NICHT ERFÜLLT",
die 1000er-Stilometrie mit 5,94 % Top-1, die Timing-Anomalie, den Ausreißer-Seed 99. Auf WiLI
wird sogar die *schlechtere* der beiden gemessenen Konfigurationen als offizielle Zahl geführt
(§8.3). Das ist ungewöhnlich und spricht für die Redlichkeit der Aufzeichnung.

Es ändert nichts daran, dass die Zahlen hier nicht nachprüfbar sind. Gute Dokumentation ist
kein Ersatz für ausführbaren Code — sie ist genau das, was der Auftrag prüfen sollte und was
sich ohne Code nicht prüfen lässt.

---

## 8. Vorgriff auf Schritt 3 — was sich ohne Code beantworten lässt

Der Auftrag verlangt, jeden Prüfpunkt zu dokumentieren, „auch wenn nichts gefunden wird". Hier
der Stand. **Keine dieser Antworten beruht auf Code-Prüfung** — das ist der springende Punkt.

### 8.1 Datenleck (Normalisierung / Vokabular / Feature-Statistiken über den Gesamtdatensatz)

**Nicht prüfbar.** Kein Vorverarbeitungs-Code vorhanden.

Ein *struktureller* Hinweis, kein Beweis: Der Ansatz ist laut D2-Spezifikation ein
Trigramm-HDC-Verfahren mit **zufällig erzeugten Hypervektoren aus geseedetem RNG**
(`ItemMemory(42)`). Ein solches Verfahren baut typischerweise **kein datengetriebenes
Vokabular** und **keine Feature-Statistiken** — Trigramme werden auf feste Zufallsvektoren
abgebildet, nicht auf gelernte Embeddings. Der klassische Leckpfad (Vokabular oder
Normalisierung über Train+Test gefittet) ist damit architektonisch weitgehend ausgeschlossen.

**Die eine offene Stelle, die bei Code-Wiederherstellung zuerst zu prüfen ist:** das
MNIST-Thermometer-Encoding mit „Q=16 Stufen". Wenn die 16 Schwellen als **Quantile über den
gesamten Datensatz** (statt nur über Train, oder statt fest bei 0…255) berechnet werden, ist das
ein echtes — wenn auch mildes — Leck. Aus der Prosa geht nicht hervor, welche Variante
vorliegt. **Das ist die konkreteste offene Leck-Frage des Projekts.**

### 8.2 Saubere Trennung Train/Val/Test vor jeder Vorverarbeitung

**Nicht prüfbar.** Einziger Code-Beleg: `fewshot_split(xtr, ytr, shots, seed)` zieht aus `xtr`
— korrekt, betrifft aber nur M5. Für WiLI und MNIST existiert kein Split-Code.

Eine **Val-Menge wird in keinem Dokument erwähnt.** Es gibt durchgängig nur Train und Test.
Das ist für die Hyperparameter-Frage (§8.3) unmittelbar relevant.

### 8.3 Werden Hyperparameter auf dem Testset gewählt?

**Teilweise beantwortbar — und hier gibt es tatsächlich einen Befund.**

Zugunsten des Projekts: Die Betriebskonfiguration λe=λp=1 war laut D5 **vorregistriert**, und
das Projekt berichtet auf WiLI die **schlechtere** Zahl:

> „Episoden-Paradox (B2): Die Episodenschicht *senkt* auf M1 die Genauigkeit: **79,30 % mit vs.
> 82,64 % ohne** (Prototypen-only)." — `D4_PROTOTYP.md.edits.json`

Die offizielle Zahl 79,30 % ist also **4,2 pp schlechter** als die beste gemessene
Konfiguration. Das ist das exakte Gegenteil von Rosinenpickerei.

Gleichwohl, und das ist der Befund: **Sämtliche Ablationen wurden auf den Testmengen
ausgewertet**, die auch die Hauptzahlen liefern — die MNIST-λe-Ablation ausdrücklich auf allen
10.000 Testbildern, die WiLI-Ablation auf der WiLI-Testmenge, dazu die M2a-θ-Sweeps (θ = 0,12 /
0,20 / 0,28 / 0,35) und die Verdrängungskurve (100/80/50/20 %). Mangels Val-Menge (§8.2) gibt es
dafür auch keine Alternative. Die Ablationen sind als „EXPLORATIV, nicht kriteriumsrelevant"
gekennzeichnet und stehen laut D4 „**neben** der offiziellen Zahl, nie an ihrer Stelle" — die
Trennung ist also bewusst gezogen und dokumentiert. Für künftige Konfigurationsentscheidungen
bleibt es trotzdem eine Test-Menge, die bereits mehrfach angesehen wurde.

### 8.4 WiLI-2018: alle 235 Sprachen?

**Ja, laut Dokumentation — alle 235.** Konsistent an mehreren Stellen: „235-Sprachen-10-shot"
(D1), Zufallsniveau „0,4 %" (= 1/235 ≈ 0,426 %, passt), D2 §6 Speicherbudget „C-M1 (K=235)".

**Wichtige Einordnung, die im README fehlt:** Es handelt sich um ein **10-Shot-Setting** — 10
Trainingsbeispiele pro Sprache, nicht die vollen ~500 Trainingsabsätze je Sprache des offiziellen
WiLI-2018-Trainingssplits. 79,30 % bei 235 Klassen aus je 10 Beispielen ist eine ganz andere —
und für sich genommen respektable — Aussage als 79,30 % nach Training auf dem Volldatensatz.
Der README nennt nur „WiLI-2018 language identification | 79.30% accuracy". **Das ist die
gravierendste Darstellungslücke des Projekts** (§8.7).

Ob die Testmenge der offizielle WiLI-Testsplit ist oder ein Eigen-Split, geht aus keinem
Dokument hervor. **Offen.**

### 8.5 MNIST: offizieller 60k/10k-Split?

**Ja, laut Dokumentation.** „volle Größe (train=60.000, test=10.000)" und „Top-1 (volle 10.000
Testbilder) … 94,62 % (9462/10000)". Die Zahl 9462/10000 ist konsistent mit 94,62 %.

Nicht prüfbar bleibt, ob es der *offizielle* Split ist oder ein eigener 60k/10k-Schnitt, und ob
eine Val-Menge abgezweigt wurde (nirgends erwähnt — vermutlich nein).

### 8.6 Ist die Metrik Accuracy, und ist die Klassenverteilung balanciert?

**Metrik: ja, Accuracy (Top-1).** Der einzige erhaltene Metrik-Code ist `m2_stream.py`
(`hit[src][0] += int(pred == label)`) und `m5_baselines.py:103` (`ok = int(pred == gold)`) —
beides schlichte Trefferquote, keine Gewichtung.

**Balance:**
- **WiLI-2018 ist konstruktionsbedingt exakt balanciert** (gleich viele Absätze je Sprache).
  Bei balancierten Klassen entspricht Accuracy dem Macro-Recall; Macro-F1 kann davon nur
  abweichen, wenn sich die *Vorhersage*verteilung stark verschiebt. Das ist bei 235 Klassen und
  einem Prototypen-Klassifikator durchaus möglich — Macro-F1 wäre hier informativ.
- **MNIST ist annähernd balanciert** (Testklassen 892–1135 Bilder, Faktor ~1,27). Accuracy ist
  vertretbar; der Unterschied zu Macro-F1 liegt erfahrungsgemäß im Zehntel-pp-Bereich.

**Macro-F1 wird nirgends berechnet.** Für WiLI wäre es die aussagekräftigere Zahl. Nachrüstbar
ist es nur mit dem fehlenden Code — oder aus Prediction-Dumps, die ebenfalls fehlen.

**Positiv anzumerken:** Das Projekt nennt das Zufallsniveau (0,4 %) und ordnet die 94,62 % in
das HDC-Literaturband 89–96 % ein. Beides ist gute Praxis.

### 8.7 Wird mehrfach evaluiert und das beste Ergebnis berichtet?

**Nein für die Genauigkeit — aber ja, in abgeschwächter Form, für das Zeitkriterium.**

**Genauigkeit — sauber.** Der 5-Seed-Lauf ist vollständig ausgewiesen, alle fünf Werte
einzeln:

| Seed | 42 | 7 | 1337 | 2026 | 99 | Mittel ± SD |
|---|---|---|---|---|---|---|
| Top-1 | 94,62 % | 94,52 % | **94,63 %** | 94,61 % | 94,58 % | **94,59 % ± 0,04** |

Der berichtete Wert 94,62 % ist **nicht** der beste (94,63 % bei Seed 1337), sondern der des
vorab festgelegten offiziellen Seeds 42. Kein Cherry-Picking.

**Zeitkriterium — hier liegt der Befund.** Chronologie aus den Dokumenten:

1. Vorregistriert (D5 §2): acc ≥ 94 % **∧** Lernzeit < 30 min.
2. Offizieller Einzellauf: 94,62 % ✓, **41,4 min ✗** → „**NICHT ERFÜLLT**".
3. Danach D5 **v1.1**: Adjudikationsregel eingeführt — maßgeblich ist die **mittlere**
   Lernzeit des 5-Seed-Laufs, nicht die des Einzellaufs.
4. 5-Seed-Ergebnis: Mittel **28,1 ± 2,4 min**, **Max 31,8 min** (Seed 99).
5. Urteil gedreht: „28,1 min < 30 min ⇒ Zeitkriterium **ERFÜLLT**. Zusammen mit acc 94,59 % ist
   damit **M1b insgesamt ERFÜLLT**."
6. Der Harness-Code wurde nachgezogen — belegt in `m1b_mnist.py.edits.json`:
   `crit = accs.mean() >= 0.94 and learns.max() < 1800` → `... and learns.mean() < 1800`.

Das Projekt legt diesen Vorgang **vollständig offen**: Die Regel sei „registriert VOR Vorliegen
der 5-Seed-Zeiten" und „richtungsneutral" formuliert (Mittel ≥ 30 min hätte NICHT ERFÜLLT
bestätigt); das Kriterium selbst (< 30 min) blieb unverändert, geregelt wurde nur, welche
Messung zählt; die Historie bleibt dokumentiert; der Ausreißer-Seed 99 und die knappe Marge
werden ausdrücklich benannt.

**Bewertung, nüchtern:** Die Regel wurde **nach** einer fehlgeschlagenen Messung und **vor** der
entlastenden eingeführt, und die Änderung von `max` auf `mean` verschiebt die Entscheidung von
„alle Seeds müssen bestehen" auf „im Mittel bestehen" — bei Max 31,8 min ist das
ergebnisrelevant. Dass die alte Regel überhaupt im Code stand, zeigt, dass `max` einmal die
gelebte Lesart war. Ich würde das nicht als Manipulation bezeichnen — die Offenlegung ist
vorbildlich und die Begründung (Thermal-Throttling im 11,5-h-Lauf) ist plausibel und mit dem
Vergleich 41,4 → 27,4 min für denselben Seed 42 belegt. Aber es ist ein Kriterium, das nach
seinem Scheitern operational gelockert wurde, und es sollte so benannt werden.

**Ohne Belang für die beiden auditierten Zahlen:** Der Vorgang betrifft ausschließlich das
Zeitkriterium. Die 94,62 %/94,59 % sind davon nicht berührt.

### 8.8 Zusammenfassung Schritt 3

| Prüfpunkt | Ergebnis |
|---|---|
| Datenleck Normalisierung/Vokabular | **Nicht prüfbar.** Strukturell unwahrscheinlich (geseedete Zufallsvektoren statt gelernter Embeddings). Offene Stelle: MNIST-Thermometer-Schwellen. |
| Train/Val/Test-Trennung vor Vorverarbeitung | **Nicht prüfbar.** Keine Val-Menge dokumentiert. |
| Hyperparameter auf Testset | **Betriebskonfiguration vorregistriert** und dokumentiert schlechter als die Alternative. Aber: alle Ablationen auf der Testmenge, mangels Val-Menge. |
| WiLI: alle 235 Sprachen | **Ja** (dokumentiert). Aber **10-Shot** — im README nicht erwähnt. |
| MNIST: offizieller 60k/10k-Split | **Ja** (dokumentiert), Herkunft nicht prüfbar. |
| Metrik Accuracy / Balance / Macro-F1 | Accuracy bestätigt. Beide Datensätze (nahezu) balanciert → Accuracy vertretbar. **Macro-F1 fehlt**, für WiLI wünschenswert. |
| Mehrfachevaluation, bestes Ergebnis berichtet | **Genauigkeit: nein** (Seed 42 statt bestem Seed 1337). **Zeitkriterium: Regel nach Fehlschlag von `max` auf `mean` geändert** — offengelegt, aber ergebnisrelevant. |

### 8.9 Weitere Darstellungslücken im README

Unabhängig vom Code-Problem, da der README die öffentliche Außendarstellung ist:

1. **„79.30% accuracy" ohne „10-Shot".** Die gravierendste Lücke — sie lässt ein
   Few-Shot-Ergebnis wie ein Volldaten-Ergebnis aussehen. Korrekt wäre etwa: „79,30 % ± 0,68 %,
   235 Sprachen, 10 Beispiele pro Sprache".
2. **„94.62% accuracy" ist ein Einzelseed-Wert.** Maßgeblich ist laut D4 der 5-Seed-Mittelwert
   **94,59 % ± 0,04**. Differenz 0,03 pp — unerheblich in der Sache, aber es ist die
   Einzelmessung, die als Kopfzahl steht, während für WiLI korrekt der 5-Seed-Wert genannt wird.
3. **„M1b" fehlt der Hinweis, dass das UND-Kriterium beim Zeitteil hing** (§8.7).
4. **„Order-invariance proven bit-identical" (M3)** gilt laut Projekt für den *Zustand*, nicht
   für die *Auslese* — dort stehen 0,03 pp Abweichung offen (W19, §6).
5. Der README nennt die M5-Niederlage nicht, obwohl D5/D6 sie als getroffenen
   Falsifikationspunkt führen („(3) NIEDERLAGE auf beiden Aufgaben, Banking77 −20,4 pp,
   CLINC150 −22,0 pp"). Unter „Documented failures" stehen M2a und M3, nicht M5 — bei einem
   Projekt, das Negativergebnisse ausdrücklich zum Prinzip erhebt, ist das eine Auslassung.

---

## 9. Konsequenz für die Schritte 2–4

Die beauftragte Reihenfolge setzt lauffähigen Code voraus. Den gibt es nicht. Schritt 2
(Pinnen, Ein-Befehl-Reproduktion, Seeds, Laufzeit/RAM, results/-JSON), Schritt 3
(Code-Prüfung auf Leckage) und Schritt 4 (5-Seed-Verifikationslauf) sind damit blockiert, bis
die Quelle wieder da ist.

**Erste Frage vor allem anderen:** Existiert der ursprüngliche Arbeitsbaum
`/Users/erikthye/engramm/` auf dem MacBook noch — ganz oder teilweise? Auch ein Time-Machine-
Backup, ein Zip, ein `__pycache__/engramm.cpython-313.pyc` (daraus ist der Quelltext
weitgehend dekompilierbar) oder die alten Claude-Code-Sitzungstranskripte unter
`~/.claude/projects/` würden genügen. Danach zu suchen ist mit Abstand der billigste Weg —
alles andere ist Neuschreiben.

Denkbare Wege, in dieser Reihenfolge:

**A — Wiederherstellung (empfohlen, falls irgend möglich).** Original oder `.pyc` finden,
`engramm.py` zurückholen, dann Schritte 2–4 wie beauftragt durchführen. Nur dieser Weg prüft
die bestehenden Zahlen wirklich.

**B — Neuimplementierung aus D2.** Die Spezifikation ist detailliert genug (Pseudocode für
`QUERY`, `CONSOLIDATE`, T1/T2/T3, Speicherbudget), um den Kern nachzubauen. Ergebnis wäre eine
*unabhängige Reimplementierung*: erreicht sie ~79 %/~94,6 %, stützt das die Zahlen kräftig;
verfehlt sie sie, wäre unklar, ob Doku oder Nachbau schuld ist. Aufwand: erheblich. Und es
verstößt gegen die Auftragsauflage „keine Änderungen am Algorithmus" nur scheinbar — es ist gar
kein Algorithmus da, den man ändern könnte.

**C — Nur die Infrastruktur bauen (unabhängig von A/B sinnvoll).** Was sich *ohne* den Kern
schon jetzt erledigen lässt und in jedem Fall gebraucht wird: `requirements.txt` mit den in R6
dokumentierten Pins (Python 3.13.7, NumPy 2.4.1, FAISS-CPU 1.14.3), Datendownload-Skript für
WiLI-2018 und MNIST inklusive Prüfsummen, Runner-Gerüst mit Seed-Setzung für alle
Zufallsquellen, Laufzeit-/Peak-RAM-Messung, `results/`-JSON-Schema mit Zeitstempel, Seed,
Commit-Hash und Umgebungsdaten. Das ist Schritt 2 minus dem Teil, der den Kern braucht.

**D — Repository-Hygiene (klein, sofort).** `.edits.json` aus dem Quellbaum entfernen (Inhalte
vorher in die D-Dokumente zurückführen — dort steckt die Substanz), `vox_fusion-*.py` auf eine
Fassung konsolidieren, README um die Punkte aus §8.9 korrigieren.

**Meine Empfehlung:** zuerst A prüfen (Suche auf dem Mac, Kosten: Minuten). Parallel dazu C, weil
es in jedem Szenario gebraucht wird und nichts vorwegnimmt. B nur, wenn A endgültig scheitert —
und dann ausdrücklich als Neuimplementierung deklariert, nicht als Reproduktion.

**Bis dahin gilt:** Die Zahlen 79,3 % und 94,6 % sind **unbelegt im Sinne von nicht
nachprüfbar**. Nicht widerlegt, nicht bestätigt. Wer sie öffentlich führt — der README tut das —
sollte wissen, dass derzeit kein Artefakt existiert, mit dem ein Dritter sie nachvollziehen
könnte.
