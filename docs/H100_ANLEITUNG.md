# Anleitung: ENGRAMM auf einer gemieteten H100 bis GPT-2-Niveau trainieren

Stand 12. Oktober 2026. Ziel (Stufe 1, PLAN §6/§11): Test-Satz ≤ 1,04 Bits pro Byte, das Niveau von GPT-2 small.
Entscheidend ist der Test-Wert nach der Duplikatregel aus PLAN §10, angewendet auf den tatsächlich trainierten Text
(PLAN §11). Der Wert mit der alten Filterliste wird zusätzlich berichtet.

## Kurz gesagt

| | |
|---|---|
| Was du tust | Konto anlegen, Guthaben aufladen, GitHub-Schlüssel anlegen, eine GPU mieten, **drei Befehle** einfügen, am Ende kurz kontrollieren |
| Was automatisch passiert | Daten laden und prüfen, Lernrate suchen, trainieren, messen, Ergebnisse und Modell auf GitHub sichern, dann löscht sich der Pod selbst |
| Dauer | ca. 6,5–7,5 Stunden, davon ~20 Minuten mit dir |
| Kosten | erwartet ca. 25–30 $ (+ ggf. Steuer); **75 $ aufladen** (ungünstigster Fall ≈ 55 $, siehe unten); der Rest bleibt auf dem Konto |
| Ergebnis | Messwerte im Repository (Branch `h100-results-…`), das Modell (≈ 0,5 GB, volle Genauigkeit) als **privater** Entwurf unter „Releases“ (nur für dich sichtbar) |
| Ehrlich | GPT-2-Niveau ist wahrscheinlich, nicht garantiert (meine Schätzung: eher ja als nein). Auch ohne Ziel sind alle Messungen gesichert |

## Was die Skripte absichern

| Risiko | Schutz |
|---|---|
| Falsche oder kaputte Daten | Jede Quelldatei per SHA-256 festgelegt; die nachgebauten Prüfdaten müssen **bitgleich** zum CPU-Rechner sein, sonst Abbruch vor dem Training |
| Testdaten im Training (geschönte Werte) | Zusatztext nur aus dem Trainings-Bereich der Hash-Aufteilung; Prüfung aller 13-Token-Fenster der Test-Dokumente im gesamten Trainingstext; Beinahe-Duplikate zählen nicht |
| GitHub-Schlüssel falsch oder ohne Schreibrecht | Wird **in der ersten Minute** geprüft, nicht erst nach 7 Stunden |
| Falsche Lernrate | Kurze Suche über drei Werte vor dem Hauptlauf |
| GPU langsamer als gedacht | Zeitgrenze 5,5 h für das Haupttraining (Tokenzahl wird angepasst) |
| GPU-Speicher reicht nicht / Beschleunigung versagt | automatischer Rückfall auf die sparsame, auf der CPU getestete Variante |
| Training „explodiert“ | Erkennung; einmaliger Neustart mit halber Lernrate |
| Pod startet neu | Zustand alle 30 min gesichert; derselbe Startbefehl setzt fort; Pakete werden bei jedem Start geprüft |
| Doppelter Start | Ein zweiter Start erkennt den laufenden und beendet sich sofort |
| Lauf hängt, ohne abzubrechen | Status zeigt „Letzte Aktivität vor … min“ und warnt ab 60 min Stille bzw. ab 9 h Laufzeit |
| Fehler, während du nicht schaust | Pod **stoppt sich nach 2 h selbst** (GPU kostet nichts mehr, Daten bleiben; nur die 100 GB Speicher kosten weiter ≈ 0,70 $/Tag) |
| Pod läuft nach dem Ende weiter | Pod löscht sich selbst — **nur** nachdem Ergebnisse und Modell nachweislich auf GitHub liegen |

---

## Schritt 1 – Konto, Guthaben, GitHub-Schlüssel (15 Minuten, einmalig)

1. **RunPod-Konto:** <https://www.runpod.io> → *Sign up* → E-Mail bestätigen.
2. **Guthaben:** links *Billing* → *Add Credits* → **75 $** (Kreditkarte).
   - Guthaben wird nicht erstattet, bleibt aber auf dem Konto. Erwartet sind ~25–30 $.
   - Wichtig: Fällt das Guthaben auf 0, löscht RunPod den Pod samt Daten. 75 $ decken auch den ungünstigsten Fall
     (Training explodiert spät und läuft noch einmal: ≈ 13 h ≈ 55 $).
3. **GitHub-Schlüssel** (damit der Pod Ergebnisse und Modell selbst sichert und sich danach löschen darf):
   - Öffnen: <https://github.com/settings/personal-access-tokens/new>
     (*Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token*)
   - *Token name:* `engramm-h100` · *Expiration:* **7 days**
   - *Repository access:* **Only select repositories** → `erithy25/engramm`
   - *Permissions*: bei *Repository permissions* (ggf. erst *+ Add permissions*) → **Contents** → **Read and write**
     („Metadata: Read-only“ kommt automatisch dazu – richtig so)
   - *Generate token* → Schlüssel (`github_pat_…`) kopieren und kurz in einer Notiz ablegen (wird nur einmal angezeigt).
4. **Alten Test-Branch löschen** (sonst verwechselbar mit dem echten Ergebnis): <https://github.com/erithy25/engramm/branches>
   → bei `h100-results-20261012-1047` auf den **Mülleimer** klicken. Der stammt aus einem Probelauf auf dem CPU-Rechner
   und enthält keine H100-Werte.

## Schritt 2 – GPU mieten (5 Minuten)

1. Links **Pods** → **Deploy**.
2. **Secure Cloud** wählen (nicht Community – zuverlässiger, ~1 $/h teurer).
3. GPU: **H100 SXM** (80 GB), Anzahl **1**. Falls nicht verfügbar: **H100 NVL** oder **H100 PCIe** (geht auch, etwas langsamer).
4. Template (Vorlage): **Runpod PyTorch**, neueste Version. Falls es einen Filter *CUDA Version* gibt: die zur Vorlage
   passende Version (oder neuer) wählen.
5. Speicher (*Edit Template* / Storage): **Container Disk 50 GB**, **Volume Disk 100 GB** (Pfad `/workspace`).
6. **Deploy On-Demand** (nicht „Spot“/„Interruptible“ – die können mitten im Lauf weggenommen werden).
7. Warten, bis der Pod **Running** zeigt (1–3 Minuten; nach 10 Minuten noch nicht → siehe Tabelle unten). Ab jetzt läuft
   die Uhr (~4 $/h).

## Schritt 3 – Training starten (5 Minuten)

1. Beim Pod auf **Connect** → **Jupyter Lab** (öffnet sich im Browser) → oben *File → New → Terminal*.
2. Einfügen im Terminal: **Windows/Linux: Strg+Shift+V** (oder Rechtsklick → Paste), **Mac: Cmd+V**. Nach jedem Befehl Enter.
3. **Befehl 1** – Programm holen (den genauen, geprüften Stand):

   ```bash
   cd /workspace && git clone -q -b claude/optimistic-cannon-i0u0ap https://github.com/erithy25/engramm.git && cd engramm && git checkout -q 6de894fd05ea18dce9db672b634260669983aab6 && echo "OK: Programm geladen"
   ```

   Es muss „OK: Programm geladen“ erscheinen.
4. **Befehl 2** – GitHub-Schlüssel (beim Einfügen wird **nichts angezeigt** – das ist richtig): Befehl einfügen, Enter,
   dann den Schlüssel einfügen, Enter:

   ```bash
   read -s -p "GitHub-Schlüssel einfügen, dann Enter: " GH_TOKEN; export GH_TOKEN; echo; echo "Schlüssel gesetzt (${#GH_TOKEN} Zeichen)"
   ```

   Es muss „Schlüssel gesetzt (93 Zeichen)“ o. ä. erscheinen. **Steht dort 0 Zeichen: Befehl 2 einfach noch einmal.**
   Den Schlüssel nie direkt an der normalen Eingabe einfügen.
5. **Befehl 3** – Start:

   ```bash
   setsid nohup bash /workspace/engramm/experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &
   ```

   Danach erscheint evtl. „[1] 1234“ oder „[1]+ Done …“ – **das ist normal**, der Lauf läuft im Hintergrund weiter.
6. Nach **2 Minuten** prüfen:

   ```bash
   bash /workspace/engramm/experiments/h100_status.sh
   ```

   Es muss **„Lauf aktiv: ja“** und **„GitHub-Schlüssel geprüft: ja (Schreibrecht bestätigt …)“** stehen. Steht dort
   „NEIN“ oder ein FEHLER zum Schlüssel: neuen Schlüssel anlegen (Schritt 1.3), dann Befehl 2 und Befehl 3 wiederholen.
   **Danach kannst du den Browser schließen** – der Lauf geht weiter.
7. **Empfohlen: nach ca. 45 Minuten** noch einmal den Status aufrufen (Schritt 4). Erst dann arbeitet die GPU zum ersten
   Mal (Lernraten-Suche). Es muss „Lauf aktiv: ja“ und **[x] Basisdaten** stehen und kein FEHLER; spätestens nach ~1 Stunde
   erscheint die erste Zeile „Lernrate …: val-A … bpb“. Steht ein FEHLER da: Zeilen an mich schicken – so kostet ein
   GPU-Problem höchstens ~4 $ statt mehr.

## Schritt 4 – Während es läuft (optional)

Jederzeit: Pod → *Connect* → *Jupyter Lab* → Terminal → `bash /workspace/engramm/experiments/h100_status.sh`

Live-Protokoll (Strg+C beendet nur die Anzeige): `tail -f /workspace/h100/run.log` (Zeiten in UTC = deutsche Zeit − 2 h)

| Phase | Dauer (Schätzung) |
|---|---|
| Prüfungen, Pakete | 2–5 min |
| Basisdaten (Download 630 MB, Tokenisierung, Bit-Prüfung) | 10–20 min |
| Lernraten-Suche (GPU), gleichzeitig Zusatztext: 36 C4-Teile, ~11 GB (CPU) | 30–45 min |
| Zusammenführen und Kontaminationsprüfung | 5–15 min |
| **Haupttraining** (bis 6 Mrd. Token, Grenze 5,5 h) | **4,5–5,5 h** |
| Endmessung, Textproben, Hochladen | 10–20 min |
| **Gesamt** | **≈ 6,5–7,5 h** |

## Schritt 5 – Am Ende (nach ca. 7,5 Stunden nachsehen)

**Fertig erkennst du daran:** Auf <https://github.com/erithy25/engramm/branches> gibt es einen Branch
`h100-results-…` (**nicht** `h100-results-20261012-1047` – das ist der alte Probelauf aus Schritt 1.4) **und** der Pod
ist aus der Liste unter *Pods* verschwunden. Dann:

1. Mir schreiben: **„H100 fertig“** – ich hole die Ergebnisse, rechne die Mischung mit dem Zählmodell und berichte.
2. Kontrolle unter *Billing*: es läuft nichts mehr.
3. Das Modell liegt privat unter <https://github.com/erithy25/engramm/releases> (Entwurf, nur für dich sichtbar).

**Ist der Pod noch da: NICHT sofort beenden**, erst Status aufrufen (Connect → Jupyter Lab → Terminal →
`bash /workspace/engramm/experiments/h100_status.sh`):

| Status zeigt | Bedeutung → Was tun |
|---|---|
| „Lauf aktiv: ja“ | läuft noch → später wieder nachsehen. **Ausnahme:** Status meldet „ungewöhnlich lange still“ (über 60 min keine Aktivität) oder „Laufzeit über 9 h“ → Ausgabe an mich schicken, Pod **nicht** beenden |
| „Auf GitHub gesichert: JA“ | alles gesichert, nur die Selbstlöschung klappte nicht → Pod aufklappen → **Stop** → **Terminate** |
| „Auf GitHub gesichert: NEIN“ | → **Schritt 5b** |
| „FEHLER: …“ | Zeilen an mich schicken; Neustart siehe Tabelle unten |

### Schritt 5b – Ohne GitHub-Schlüssel oder wenn das Hochladen fehlschlug

1. In Jupyter Lab links im Dateibrowser in den Ordner `h100` wechseln → `h100_results.tgz` und `MODELL.pt` jeweils
   Rechtsklick → **Download**.
2. Erst danach den Pod beenden: *Pods* → aufklappen → **Stop** (Quadrat) → **Terminate** (Mülleimer) → bestätigen.
3. Mir Bescheid geben; ich sage dir, wie die kleine Datei `h100_results.tgz` ins Repository kommt.

Hinweis: Hat sich der Pod nach einem Fehler oder fehlgeschlagenem Hochladen selbst **gestoppt** (Kostenschutz nach 2 h),
sind alle Daten noch da: Pod → **Start** → Jupyter Lab → wie oben herunterladen (oder Neustart, siehe unten).
- Ein gestoppter Pod kostet für die 100 GB Speicher weiter **≈ 0,70 $/Tag** – also bald herunterladen oder neu starten,
  und am Ende immer **Terminate**.
- Startet ein gestoppter Pod nicht mehr oder ohne GPU (die GPU wurde inzwischen an jemand anderen vergeben): **niemals
  Terminate** – dort liegt die einzige Kopie. Bietet RunPod an, ohne GPU zu starten („0 GPUs“), das wählen: Zum
  Herunterladen (5b) und für das erneute Hochladen (Befehl 2 + 3, sobald das Training fertig war) reicht das. Sonst mir
  schreiben.

## Was tun, wenn …

| Situation | Lösung |
|---|---|
| Status zeigt „FEHLER: …“ oder „Lauf aktiv: NEIN“ (ohne „Lauf beendet“) | Zeilen an mich schicken. Neustart setzt fort: neues Terminal → **Befehl 2** (Schlüssel) → **Befehl 3** |
| Pod wurde neu gestartet / war gestoppt | Pod starten → Jupyter Lab → Terminal → **Befehl 2** → **Befehl 3** (Befehl 1 nicht nötig) |
| Ein **frisch gemieteter** Pod (Befehl 3 noch nie gelaufen) ist nach 10 Minuten nicht „Running“ / meldet „keine GPU“ | Pod beenden, neu mieten: CUDA-Filter passend zur Vorlage oder eine Vorlage mit älterem CUDA (z. B. PyTorch 2.4 / CUDA 12.4) |
| Ein **gestoppter** Pod (Lauf hatte schon begonnen) startet nicht oder ohne GPU | **Nie Terminate.** Siehe Hinweis unter Schritt 5b (ohne GPU starten, herunterladen, mir schreiben) |
| „torch zu alt“ | Pod beenden, neu mieten mit neuerer *Runpod PyTorch*-Vorlage |
| „zu wenig Platz“ beim **ersten** Start | Pod beenden, neu mieten mit Volume Disk 100 GB. Mitten im Lauf nicht beenden, sondern mir schreiben |
| H100 SXM nicht verfügbar | H100 NVL oder H100 PCIe nehmen; die Zeitgrenze kürzt notfalls die Tokenzahl |
| Guthaben wird knapp | Unter *Billing* nachladen (Lauf läuft weiter) |
| Du willst abbrechen | Erst Status: „Auf GitHub gesichert“? Sonst Schritt 5b. Dann Stop → Terminate |

## Technische Details (zum Nachprüfen)

- Skripte: `experiments/h100_run.sh` (Ablauf), `experiments/h100_data.py` (Daten), `experiments/h100_train.py`
  (Training, Endmessung), `experiments/h100_status.sh` (Status). Tests auf der CPU: `h100_train smoke` (mit/ohne
  torch.compile, bf16, beide Verlust-Varianten, Fortsetzen; schlägt fehl, wenn der Lauf still auf die Ersatz-Variante
  ausweicht oder das gespeicherte Modell nicht fp32 ist), `h100_data check-dedup` (reproduziert dedup.json exakt),
  echter Download + Tokenisierung + Zusammenführung + Kontaminationsprüfung von C4-Teil 1, Ablaufskript im Testmodus.
- Modell: Rezept fast-v1 aus dem CPU-Lauf, Größe GPT-2 small (d = 768, 12 Schichten, 12 Köpfe), Kontext 1.024,
  bf16, 524.288 Token je Schritt, AdamW (β₂ 0,95), WSD (300 Aufwärmschritte, Abnahme in den letzten 30 %).
- Daten: Basis (C4-Teil 0 + WikiText-103, 285 Mio. Token, bitgleich) + C4-Teile 1–36 (nur Trainings-Hash-Bereich),
  zusammen ≈ 6,4 Mrd. Token; trainiert werden bis zu 6 Mrd.
- Einstellungen per Umgebungsvariable: `H100_BUDGET_HOURS` (5.5), `H100_SHARDS` (36), `H100_TOKENS` (6000000000),
  `H100_AUTO_END` (`terminate` | `stop` | `none`), `export H100_NO_GITHUB=1` vor Befehl 3 (bewusst ohne Schlüssel), `touch /workspace/h100/KEEP`
  (Kostenschutz-Stopp aussetzen).
