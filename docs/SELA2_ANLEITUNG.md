# Anleitung: Sela-2 auf einer gemieteten H100 trainieren (höchstens 25 $, Guthaben 30 $)

Stand 17. Oktober 2026. Was gebaut wird und warum, steht in PLAN §12; was zählt, steht vorab in
`docs/PREREG_SELA2.md`. Dieselbe Art Ablauf wie beim Sela-1-Lauf, nur einfacher: **drei Befehle**, danach läuft alles
allein.

## Kurz gesagt

| | |
|---|---|
| Was du tust | Alten Pod löschen, Guthaben auf 30 $ bringen, GitHub-Schlüssel anlegen, eine H100 mieten, **drei Befehle** einfügen, zweimal kurz nachsehen |
| Was automatisch passiert | Trainingsdaten (≈ 15 GB, fertig vorbereitet im privaten Entwurf) laden und per SHA-256 prüfen; **Vorab-Probe** (3 min: ein winziges Modell einmal durch den ganzen Ablauf, inkl. Hochladen); Vortraining bis zur Frist; Chat-Feinabstimmung; Messung; Chat-Modell, Basismodell und Fortsetzungs-Stand auf GitHub sichern; dann löscht sich der Pod selbst |
| Dauer | ≈ 6,3 Stunden, davon ~15 Minuten mit dir |
| Kosten | **höchstens 25 $** (Kostenbremse ab dem Mieten), danach höchstens 10 Minuten zum Sichern (≈ 0,70 $). Harte Grenze: **30 $ Guthaben, automatisches Aufladen aus** |
| Ergebnis | Messwerte im Repository (Branch `sela2-results-…`); privat unter „Releases“ (nur für dich): `sela2_chat_bf16.pt` (≈ 1 GB, das Chat-Modell), `sela2_basis_bf16.pt` (Basismodell), `fortsetzen_vor_abklingen.pt` (≈ 4,8 GB in 3 Teilen, zum späteren Weitertrainieren). Die App-Datei baue ich danach kostenlos auf GitHub |
| Ehrlich | Sela-2 hat die Größe von GPT-3 Medium, aber ~1 % von dessen Rechenzeit. Erwartung: Benchmarks zwischen GPT-2 small und medium, flüssiger kurzer Chat, Fakten aus ENGRAMMs Quellen mit Zitaten (in der App geprüft). Ohne Quellen erfindet es Fakten. Deutsch ist ein Versuch |

## Was die Skripte absichern

| Risiko | Schutz |
|---|---|
| Kosten laufen aus dem Ruder | Kostenzähler über alle Pod-Sitzungen; bei **25 $** stoppt sich der Pod, mit höchstens 10 min Nachlauf. Den Preis liest das Skript bei RunPod selbst ab (nie niedriger als 4,01 $/h). Dazu die harte Grenze 30 $ Guthaben |
| Fehler erst nach Stunden | Die **Vorab-Probe** prüft in den ersten Minuten alles: Kompilieren, schnelle Attention, Feinabstimmung, Messen und Hochladen. Ein Problem kostet dann < 1 $ |
| Daten falsch oder beschädigt | Jede Datei per SHA-256 geprüft; alle mit demselben Tokenizer gebaut wie im Repository; Testsätze vorher herausgefiltert |
| GitHub-Schlüssel falsch | In der ersten Minute geprüft (Daten lesen + Schreibrecht) |
| GPU langsamer als gedacht | Tokenzahl richtet sich nach dem gemessenen Tempo; das Abklingen der Lernrate endet sicher vor der Frist |
| Training „explodiert“ oder lernt nicht | Automatisch: weiter vom letzten Stand mit halber Lernrate bzw. einmal Neubeginn mit halber Lernrate |
| Pod startet neu / Absturz | Zustand alle 20 min gesichert, bis zu zwei automatische Neustarts; derselbe Startbefehl setzt fort |
| Ergebnisse gehen verloren | Basismodell und Fortsetzungs-Stand werden schon **während** der Feinabstimmung hochgeladen; große Dateien geteilt; der Pod löscht sich nur, wenn alles nachweislich auf GitHub liegt |
| Fehler, während du nicht schaust | Vor dem Training stoppt sich der Pod nach 10 min selbst, danach nach 30 min (Daten bleiben) |

---

## Schritt 1 – Vorbereitung (10 Minuten)

1. **Alten Pod löschen**, falls noch da (er kostet Speicher): <https://www.runpod.io/console/pods> → beim alten Pod
   **Stop** → **Terminate**. Unter *Storage* darf kein altes Volume mehr stehen.
2. **Guthaben auf 30 $ bringen**: *Billing* → so viel einzahlen, dass das Guthaben **30 $** zeigt. **Automatisches
   Aufladen (Auto-Pay) ausschalten** – dann kann nie mehr als das Guthaben ausgegeben werden.
3. **Neuer GitHub-Schlüssel** (die alten `engramm-h100`/`engramm-h100-2` vorher löschen):
   <https://github.com/settings/personal-access-tokens/new>
   - *Token name:* `engramm-sela2` · *Expiration:* **7 days**
   - *Repository access:* **Only select repositories** → `erithy25/engramm`
   - *Permissions* → *Repository permissions* → **Contents: Read and write**
   - *Generate token* → Schlüssel (`github_pat_…`) kopieren und kurz in einer Notiz ablegen.

## Schritt 2 – GPU mieten (5 Minuten)

1. *Pods* → **Deploy**.
2. **H100 SXM** (80 GB), Anzahl **1**. Secure Cloud (≈ 3,99 $/h) ist der Normalfall. Gibt es eine H100 SXM in der
   Community Cloud billiger: geht auch, das Skript liest den echten Preis selbst ab.
3. Vorlage (Template): **Runpod PyTorch 2.8** (oder neuer; mindestens 2.6).
4. Speicher (*Edit Template*): **Container Disk 50 GB**, **Volume Disk 100 GB** (Pfad `/workspace`).
5. **Deploy On-Demand** (nicht Spot/Interruptible).
6. Warten bis **Running** (1–3 min). Ab jetzt läuft die Uhr – gleich weiter mit Schritt 3.

## Schritt 3 – Start (5 Minuten)

Pod → **Connect** → **Jupyter Lab** → *File → New → Terminal*. Einfügen: **Strg+Shift+V** (Mac: Cmd+V), nach jedem
Befehl Enter. Befehle mit dem Kopier-Symbol rechts oben im grauen Kasten kopieren. **Im Terminal nie Strg+C drücken.**

**Befehl 1** – Programm holen (genau geprüfter Stand):

```bash
cd /workspace && git clone -q -b claude/optimistic-cannon-i0u0ap https://github.com/erithy25/engramm.git && cd engramm && git checkout -q SELA2_COMMIT && echo "OK: Programm geladen"
```

Es muss „OK: Programm geladen“ erscheinen. Bei „already exists“:
`cd /workspace/engramm && git fetch -q origin && git checkout -q SELA2_COMMIT && echo "OK: Programm geladen"`

**Befehl 2** – GitHub-Schlüssel (beim Einfügen wird **nichts angezeigt** – richtig so): Befehl einfügen, Enter, dann
den Schlüssel einfügen, Enter:

```bash
read -s -p "GitHub-Schlüssel einfügen, dann Enter: " GH_TOKEN; GH_TOKEN=$(printf %s "$GH_TOKEN" | tr -d "[:space:]"); export GH_TOKEN; echo; echo "Schlüssel gesetzt (${#GH_TOKEN} Zeichen)"
```

Es muss „Schlüssel gesetzt (93 Zeichen)“ o. ä. erscheinen. Bei 0 Zeichen: Befehl 2 noch einmal.

**Befehl 3** – Start:

```bash
setsid nohup bash /workspace/engramm/experiments/sela2_run.sh > /workspace/sela2_console.log 2>&1 &
```

„[1] 1234“ o. ä. ist normal – der Lauf läuft im Hintergrund.

## Schritt 4 – Zweimal nachsehen

**Nach ~15 Minuten** (Pflicht, damit ein früher Fehler höchstens ~1 $ kostet):

```bash
bash /workspace/engramm/experiments/sela2_status.sh
```

Es muss stehen: **„Lauf aktiv: ja“**, **„GitHub-Schlüssel geprüft: ja“**, **[x] Trainingsdaten**, **[x] Vorab-Probe**
und eine Zeile „Vortraining: … Token/s“. Dann kannst du den Browser schließen.

**Nach ~6,5 Stunden** (Pflicht, spätestens 7 h nach dem Mieten): Ist der Pod aus der Liste verschwunden und gibt es
unter <https://github.com/erithy25/engramm/branches> einen Branch `sela2-results-…`, ist alles fertig → mir schreiben:
**„Sela-2 fertig“**. Ist der Pod noch da: Status aufrufen (oben) und nach der Tabelle handeln.

| Status zeigt | Was tun |
|---|---|
| „Lauf aktiv: ja“ | läuft noch → später nachsehen (bei „ungewöhnlich lange still“: Ausgabe an mich, Pod nicht beenden) |
| „Alles auf GitHub gesichert“ | Pod → **Stop** → **Terminate** (die Selbstlöschung hat nicht geklappt) |
| „NICHT alles auf GitHub gesichert“ oder „FEHLER: …“ | Ausgabe an mich schicken, Pod **nicht** löschen |
| „KOSTENBREMSE hat gegriffen“ | Ausgabe an mich; der Pod stoppt sich (Daten bleiben) |

| Phase | Dauer |
|---|---|
| Prüfungen, Daten laden und prüfen | 5–10 min |
| Vorab-Probe | ≈ 3–5 min |
| **Vortraining** | **≈ 5,2 h** |
| Chat-Feinabstimmung | ≈ 20 min |
| Messung, Hochladen, Selbstlöschung | ≈ 15 min |

## Was tun, wenn …

| Situation | Lösung |
|---|---|
| FEHLER oder „Lauf aktiv: NEIN“ (ohne „Lauf beendet“) | Zeilen an mich. Neustart setzt fort: neues Terminal → **Befehl 2** → **Befehl 3** |
| Pod wurde neu gestartet / war gestoppt | Pod starten → Jupyter Lab → Terminal → sofort **Befehl 2** und **Befehl 3** (schaltet auch die Kostenbremse wieder ein) |
| Frisch gemieteter Pod nach 10 min nicht „Running“ / keine GPU | Pod beenden, neu mieten |
| H100 SXM nicht verfügbar | Später erneut versuchen (H100 NVL/PCIe gehen auch, sind aber langsamer: weniger Token fürs gleiche Geld) |
| Du musstest einen **zweiten** Pod mieten | Vor Befehl 3 auf dem neuen Pod: `export SELA2_SPENT_USD=…` (was der erste Pod laut *Billing* gekostet hat) – damit bleibt es insgesamt bei 25 $ |
| Du willst abbrechen | Erst Status: was ist gesichert? Dann Stop → Terminate |

## Technische Details

- Ablauf `experiments/sela2_run.sh`, Status `experiments/sela2_status.sh`, Training `experiments/sela2_train.py`,
  Modell `experiments/sela2_model.py`, Optimierer `experiments/sela2_optim.py`, Daten `experiments/sela2_data.py`
  (gebaut von `.github/workflows/sela2_data.yml`), Release-Zugriff `experiments/gh_release.py`.
- Geprüft vor dem Mieten (`.github/workflows/sela2_check.yml`, torch 2.8 wie auf dem Pod):
  - Unit-Tests;
  - CPU-Lauf mit simuliertem Abbruch (bitgleiche Fortsetzung) und künstlicher Verlangsamung (Abklingen vor der Frist);
  - das Pod-Skript im Testmodus auf den echten Daten mit einem winzigen Modell.
- Einstellungen (vor Befehl 3, werden für Neustarts gemerkt):
  - `SELA2_MAX_USD` (25);
  - `SELA2_SPENT_USD` (0);
  - `SELA2_PRICE` (4.01 = Mindestpreis für die Bremse);
  - `SELA2_AUTO_END` (`terminate` | `stop` | `none`).
- Fortsetzungs-Stand: Gewichte, Optimierer und Datenposition beim Übergang ins Abklingen. Von dort kann man später mit
  mehr Token weitertrainieren.
