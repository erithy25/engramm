# Anleitung: ENGRAMM auf einer gemieteten H100 bis GPT-2-Niveau trainieren

Stand 12. Oktober 2026. Ziel (Stufe 1, PLAN §6/§11): Test-Satz ≤ 1,04 Bits pro Byte, das Niveau von GPT-2 small.
Entscheidend ist der Test-Wert nach der Duplikatregel aus PLAN §10, angewendet auf den tatsächlich trainierten Text
(PLAN §11). Der Wert mit der alten Filterliste wird zusätzlich berichtet.

## Kurz gesagt

| | |
|---|---|
| Was du tust | Konto anlegen, Guthaben aufladen, GitHub-Schlüssel anlegen, eine GPU mieten, **drei Befehle** einfügen, am Ende kurz kontrollieren |
| Was automatisch passiert | Daten laden und prüfen, Lernrate suchen, trainieren **so lange das Budget reicht**, messen, Ergebnisse, Modell und Fortsetzungs-Stand auf GitHub sichern, dann löscht sich der Pod selbst |
| Dauer | ca. 6 Stunden, davon ~20 Minuten mit dir |
| Kosten | **höchstens 25 $** (feste Kostenbremse, gemessen ab dem Mieten). Bei 30 $ Guthaben bleiben 5 $ Puffer – RunPod darf nie auf 0 $ fallen |
| Ergebnis | Messwerte im Repository (Branch `h100-results-…`); als **privater** Entwurf unter „Releases“ (nur für dich sichtbar): das fertige Modell (≈ 0,5 GB) und der **Fortsetzungs-Stand** (≈ 1,6 GB) zum späteren Weitertrainieren |
| Ehrlich | Mit 25 $ bleiben ~4–4,5 h echtes Training (statt 5,5 h). GPT-2-Niveau ist damit offen – etwa Münzwurf. Reicht es nicht, kann vom Fortsetzungs-Stand aus weitertrainiert werden: eigener Rechner mit NVIDIA-GPU ab 16 GB, ≥ 32 GB Arbeitsspeicher und ≥ 45 GB freiem Platz – oder ein paar Dollar mehr auf RunPod |

## Was die Skripte absichern

| Risiko | Schutz |
|---|---|
| Falsche oder kaputte Daten | Jede Quelldatei per SHA-256 festgelegt; die nachgebauten Prüfdaten müssen **bitgleich** zum CPU-Rechner sein, sonst Abbruch vor dem Training |
| Testdaten im Training (geschönte Werte) | Zusatztext nur aus dem Trainings-Bereich der Hash-Aufteilung; Prüfung aller 13-Token-Fenster der Test-Dokumente im gesamten Trainingstext; Beinahe-Duplikate zählen nicht |
| GitHub-Schlüssel falsch oder ohne Schreibrecht | Wird **in der ersten Minute** geprüft, nicht erst nach 7 Stunden |
| Falsche Lernrate | Kurze Suche über drei Werte vor dem Hauptlauf |
| GPU langsamer oder schneller als gedacht | Die Tokenzahl richtet sich nach dem gemessenen Tempo und der restlichen Budgetzeit |
| GPU-Speicher reicht nicht / Beschleunigung versagt | automatischer Rückfall auf die sparsame, auf der CPU getestete Variante |
| Training „explodiert“ | Erkennung; weiter ab dem letzten Speicherstand (≤ 30 min alt) mit halber Lernrate – kein teurer Neubeginn |
| Kosten laufen aus dem Ruder | **Kostenbremse:** ein Zähler misst die bezahlte Pod-Zeit (auch über Neustarts); bei **25 $** stoppt sich der Pod selbst. Das Training plant sein Ende so, dass Messung und Hochladen vorher fertig sind; Uploads werden nie in den Stopp hinein begonnen. Startet RunPod den Pod unbemerkt neu, schaltet spätestens der nächste Status-Aufruf die Bremse wieder ein (sie rechnet die Zeit seit dem Neustart mit) – deshalb die **Pflicht-Kontrolle spätestens 7 h nach dem Mieten** |
| Budget reicht nicht bis GPT-2-Niveau | Der letzte Stand vor dem Absinken der Lernrate wird als Fortsetzungs-Stand gesichert: von dort kann man später nahtlos weitertrainieren |
| Pod startet neu | Zustand alle 30 min gesichert; derselbe Startbefehl setzt fort; Pakete werden bei jedem Start geprüft. Ein Pod ohne laufendes Training stoppt sich nach 30 min selbst, sobald Status oder Befehl 3 einmal aufgerufen wurde |
| Doppelter Start | Ein zweiter Start erkennt den laufenden und beendet sich sofort |
| Lauf hängt, ohne abzubrechen | Status zeigt „Letzte Aktivität vor … min“ und warnt ab 60 min Stille; spätestens die Kostenbremse stoppt den Pod |
| Fehler, während du nicht schaust | Pod **stoppt sich nach 30 min selbst** (GPU kostet nichts mehr, Daten bleiben; nur die 100 GB Speicher kosten weiter ≈ 0,70 $/Tag) |
| Pod läuft nach dem Ende weiter | Pod löscht sich selbst — **nur** nachdem Ergebnisse und Modell nachweislich auf GitHub liegen |

---

## Schritt 1 – Konto, Guthaben, GitHub-Schlüssel (15 Minuten, einmalig)

1. **RunPod-Konto:** <https://www.runpod.io> → *Sign up* → E-Mail bestätigen.
2. **Guthaben:** **30 $** reichen (nichts weiter aufladen). Die **Kostenbremse** steht auf **25 $**; die übrigen 5 $
   sind Puffer, damit das Guthaben nie auf 0 fällt (bei 0 $ stoppt RunPod den Pod und kann die Daten löschen).
   - Anderes Guthaben? Dann vor Befehl 3 zusätzlich `export H100_MAX_USD=…` mit *Guthaben minus 5* eingeben.
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
2. Falls angeboten: **Secure Cloud** (nicht Community – zuverlässiger). Bei H100 SXM erkennbar am Preis von ~3,99 $/h.
3. GPU: **H100 SXM** (80 GB), Anzahl **1**. Falls nicht verfügbar: **H100 NVL** oder **H100 PCIe** (geht auch, etwas langsamer).
4. Template (Vorlage): **Runpod PyTorch**, neueste Version. Falls es einen Filter *CUDA Version* gibt: die zur Vorlage
   passende Version (oder neuer) wählen.
5. Speicher (*Edit Template* / Storage): **Container Disk 50 GB**, **Volume Disk 100 GB** (Pfad `/workspace`).
6. **Deploy On-Demand** (nicht „Spot“/„Interruptible“ – die können mitten im Lauf weggenommen werden).
7. Warten, bis der Pod **Running** zeigt (1–3 Minuten; nach 10 Minuten noch nicht → siehe Tabelle unten). Ab jetzt läuft
   die Uhr (4,01 $/h) – und die Kostenbremse rechnet diese Zeit mit. Also gleich mit Schritt 3 weitermachen.

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

   Es muss **„Lauf aktiv: ja“**, **„GitHub-Schlüssel geprüft: ja (Schreibrecht bestätigt …)“** und
   „Kosten bisher ≈ … $ von höchstens 25 $“ stehen. Steht dort
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
| **Haupttraining** (so viele Token, wie das Budget erlaubt) | **≈ 4–4,5 h** |
| Endmessung, Textproben, Hochladen | 10–20 min |
| **Gesamt** | **≈ 6 h (≤ 25 $)** |

## Schritt 5 – Am Ende (nach ca. 6–6,5 Stunden nachsehen – **spätestens 7 Stunden nach dem Mieten, das ist Pflicht**)

Warum Pflicht: 30 $ reichen für 7,5 Stunden Pod-Zeit. Hat RunPod den Pod zwischendurch unbemerkt neu gestartet, läuft
die Kostenbremse erst nach dem nächsten Status-Aufruf wieder – dieser Aufruf stoppt einen zu teuren Pod dann sofort.

**Fertig erkennst du daran:** Auf <https://github.com/erithy25/engramm/branches> gibt es einen Branch
`h100-results-…` (**nicht** `h100-results-20261012-1047` – das ist der alte Probelauf aus Schritt 1.4) **und** der Pod
ist aus der Liste unter *Pods* verschwunden. Dann:

1. Mir schreiben: **„H100 fertig“** – ich hole die Ergebnisse, rechne die Mischung mit dem Zählmodell und berichte.
2. Kontrolle unter *Billing*: es läuft nichts mehr.
3. Modell (`model_main_….pt`) und Fortsetzungs-Stand (`fortsetzen_main_….pt`) liegen privat unter
   <https://github.com/erithy25/engramm/releases> (Entwurf, nur für dich sichtbar).

**Ist der Pod noch da: NICHT sofort beenden**, erst Status aufrufen (Connect → Jupyter Lab → Terminal →
`bash /workspace/engramm/experiments/h100_status.sh`). Ist der Pod **gestoppt**: erst *Start*, dann sofort diesen
Status-Befehl – er schaltet auch den Kostenschutz für diese Sitzung ein.

| Status zeigt | Bedeutung → Was tun |
|---|---|
| „Lauf aktiv: ja“ | läuft noch → später wieder nachsehen. **Ausnahme:** Status meldet „ungewöhnlich lange still“ (über 60 min keine Aktivität) → Ausgabe an mich schicken, Pod **nicht** beenden |
| „KOSTENBREMSE hat gegriffen“ | Pod hat sich bei 25 $ selbst gestoppt (sollte nicht vorkommen – das Training endet vorher). Daten sind da → Ausgabe an mich. Herunterladen wie in 5b: nach der Grenze gibt es **insgesamt höchstens 30 min** (≈ 2 $, der Status zeigt die Restzeit), danach stoppt der Pod wieder |
| „Auf GitHub gesichert: JA“ | alles gesichert, nur die Selbstlöschung klappte nicht → Pod aufklappen → **Stop** → **Terminate** |
| „Auf GitHub gesichert: NEIN“ | → **Schritt 5b** |
| „FEHLER: …“ | Zeilen an mich schicken; Neustart siehe Tabelle unten |

### Schritt 5b – Ohne GitHub-Schlüssel oder wenn das Hochladen fehlschlug

1. In Jupyter Lab links im Dateibrowser in den Ordner `h100` wechseln → `h100_results.tgz`, `MODELL.pt` und
   `FORTSETZEN.pt` jeweils Rechtsklick → **Download**.
2. Erst danach den Pod beenden: *Pods* → aufklappen → **Stop** (Quadrat) → **Terminate** (Mülleimer) → bestätigen.
3. Mir Bescheid geben; ich sage dir, wie die kleine Datei `h100_results.tgz` ins Repository kommt.

Hinweis: Hat sich der Pod nach einem Fehler oder fehlgeschlagenem Hochladen selbst **gestoppt** (Kostenschutz nach 30 min),
sind alle Daten noch da: Pod → **Start** → Jupyter Lab → Terminal → **zuerst** `bash /workspace/engramm/experiments/h100_status.sh`
(schaltet den Kostenschutz ein) → wie oben herunterladen (oder Neustart, siehe unten) → danach sofort **Stop**.
- Ein gestoppter Pod kostet für die 100 GB Speicher weiter **≈ 0,70 $/Tag**. Nach einem Lauf bis zur Grenze bleiben vom
  Guthaben nur ~3–5 $ – also innerhalb weniger Tage herunterladen und dann **Terminate**.
- Startet ein gestoppter Pod nicht mehr oder ohne GPU (die GPU wurde inzwischen an jemand anderen vergeben): **niemals
  Terminate** – dort liegt die einzige Kopie. Bietet RunPod an, ohne GPU zu starten („0 GPUs“), das wählen: Zum
  Herunterladen (5b) und für das erneute Hochladen (Befehl 2 + 3, sobald das Training fertig war) reicht das. Sonst mir
  schreiben.

## Was tun, wenn …

| Situation | Lösung |
|---|---|
| Status zeigt „FEHLER: …“ oder „Lauf aktiv: NEIN“ (ohne „Lauf beendet“) | Zeilen an mich schicken. Neustart setzt fort: neues Terminal → **Befehl 2** (Schlüssel) → **Befehl 3** |
| Pod wurde neu gestartet / war gestoppt | Pod starten → Jupyter Lab → Terminal → **Befehl 2** → **Befehl 3** (Befehl 1 nicht nötig; Befehl 3 schaltet auch den Kostenschutz ein) |
| Ein **frisch gemieteter** Pod (Befehl 3 noch nie gelaufen) ist nach 10 Minuten nicht „Running“ / meldet „keine GPU“ | Pod beenden, neu mieten: CUDA-Filter passend zur Vorlage oder eine Vorlage mit älterem CUDA (z. B. PyTorch 2.4 / CUDA 12.4) |
| Ein **gestoppter** Pod (Lauf hatte schon begonnen) startet nicht oder ohne GPU | **Nie Terminate.** Siehe Hinweis unter Schritt 5b (ohne GPU starten, herunterladen, mir schreiben) |
| „torch zu alt“ | Pod beenden, neu mieten mit neuerer *Runpod PyTorch*-Vorlage |
| „zu wenig Platz“ beim **ersten** Start | Pod beenden, neu mieten mit Volume Disk 100 GB. Mitten im Lauf nicht beenden, sondern mir schreiben |
| H100 SXM nicht verfügbar | H100 NVL oder H100 PCIe nehmen; die Zeitgrenze kürzt notfalls die Tokenzahl |
| Guthaben wird knapp | Pod-Zeit ist auf 25 $ (+ höchstens 30 min zum Sichern ≈ 2 $) begrenzt. Danach nur noch Speicher ≈ 0,70 $/Tag, solange der Pod gestoppt herumsteht → bald **Terminate** |
| Du willst abbrechen | Erst Status: „Auf GitHub gesichert“? Sonst Schritt 5b. Dann Stop → Terminate |

## Technische Details (zum Nachprüfen)

- Skripte: `experiments/h100_run.sh` (Ablauf), `experiments/h100_data.py` (Daten), `experiments/h100_train.py`
  (Training, Endmessung), `experiments/h100_status.sh` (Status). Tests auf der CPU: `h100_train smoke` (mit/ohne
  torch.compile, bf16, beide Verlust-Varianten, Fortsetzen, Fortsetzen mit halber Lernrate, Kürzen auf die Zeitgrenze,
  keine Fortsetzung nach abgelaufener Zeit; schlägt fehl, wenn der Lauf still auf die Ersatz-Variante ausweicht oder das
  gespeicherte Modell nicht fp32 ist), `h100_data check-dedup` (reproduziert dedup.json exakt),
  echter Download + Tokenisierung + Zusammenführung + Kontaminationsprüfung von C4-Teil 1, Ablaufskript im Testmodus.
- Modell: Rezept fast-v1 aus dem CPU-Lauf, Größe GPT-2 small (d = 768, 12 Schichten, 12 Köpfe), Kontext 1.024,
  bf16, 524.288 Token je Schritt, AdamW (β₂ 0,95), WSD (300 Aufwärmschritte, Abnahme in den letzten 30 %).
- Daten: Basis (C4-Teil 0 + WikiText-103, 285 Mio. Token, bitgleich) + C4-Teile 1–36 (nur Trainings-Hash-Bereich),
  zusammen ≈ 6,4 Mrd. Token; trainiert wird, so viel das Budget erlaubt.
- Kostenbremse (`experiments/h100_meter.sh`, gestartet von `h100_run.sh` und `h100_status.sh`): zählt die Laufzeit jeder
  Pod-Sitzung (ab Container-Start) in `/workspace/h100/meter/`; bei `H100_MAX_USD` / `H100_PRICE` Stunden stoppt sie den
  Pod (runpodctl, ersatzweise die RunPod-API) und versucht es jede Minute erneut, bis er aus ist. Nach der Grenze gibt es
  insgesamt höchstens 30 min zum Sichern. Das Haupttraining bekommt als Frist „Grenze minus bisherige Laufzeit minus 30 min“ und
  setzt seine Tokenzahl nach gemessenem Durchsatz darauf (Obergrenze `H100_TOKENS`, 10 Mrd.; über 6,4 Mrd. hinaus
  wird der Text ein zweites Mal, neu gemischt, gelesen).
- Fortsetzungs-Stand: `state_main_predecay.pt` (im Release `fortsetzen_main_….pt`, auf dem Pod `FORTSETZEN.pt`) =
  Gewichte + Optimierer + Datenposition beim Übergang in die Abnahmephase der Lernrate (WSD); endete das Training wegen
  der Zeitgrenze schon vorher, ist es der letzte Stand. Weitertrainieren auf einem Rechner mit NVIDIA-GPU (≥ 16 GB),
  ≥ 32 GB Arbeitsspeicher und ~30 GB freiem Platz:
  1. Denselben Programmstand holen wie Befehl 1 (`git clone -b claude/optimistic-cannon-i0u0ap …` und `git checkout`
     derselben Nummer), eine Python-Umgebung anlegen und Pakete installieren (Ubuntu: ggf. vorher
     `sudo apt install python3-venv`):
     `python3 -m venv ~/engramm-env && . ~/engramm-env/bin/activate && pip install numpy torch tokenizers==0.23.2 pyarrow`
     (`. ~/engramm-env/bin/activate` in jedem neuen Terminal wiederholen). Dann Daten und Kontaminationsliste bauen:
     `python3 -m experiments.h100_data base && python3 -m experiments.h100_data extra --shards 36 && python3 -m experiments.h100_data merge --shards 36 && python3 -m experiments.h100_data contamination`
  2. Die Datei als `<ordner>/state_main.pt` ablegen (umbenennen).
  3. `python3 -m experiments.h100_train train --ckpt-dir <ordner> --tag main --extend-to <Token gesamt> --budget-hours 0 --lr $(python3 -c "import torch;print(torch.load('<ordner>/state_main.pt',map_location='cpu',weights_only=False)['meta']['args']['lr'])")`
     (Lernrate immer aus der Datei, nie `--allow-lr-change`). Im Protokoll muss „resumed main at … M tokens“ stehen,
     sonst sofort abbrechen. `<Token gesamt>` muss deutlich über dem bisherigen Stand liegen (der steht im Protokoll).
     Die Lernrate bleibt bis 70 % des neuen Ziels konstant, danach folgt die Abnahme – praktisch wie ein von Anfang an
     längerer Lauf; bei 70 % entsteht ein neuer Fortsetzungs-Stand. Die Zeile „Stage 1 …: test … bpb (extended
     (contamination.json); …)“ muss diesen Filter nennen – nur dieser Wert zählt.
  4. Auf einem gemieteten Pod gibt es dabei **keine** Kostenbremse – dort `--deadline <Unix-Zeit>` setzen oder mich fragen.
- Einstellungen per Umgebungsvariable: `H100_MAX_USD` (25), `H100_PRICE` (4.01), `H100_BUDGET_HOURS` (5.5), `H100_SHARDS` (36), `H100_TOKENS` (10000000000),
  `H100_AUTO_END` (`terminate` | `stop` | `none`), `export H100_NO_GITHUB=1` vor Befehl 3 (bewusst ohne Schlüssel), `touch /workspace/h100/KEEP`
  (setzt nur den 30-min-Stopp nach FEHLER/fehlgeschlagenem Hochladen für diese Sitzung aus – **nie** die 25-$-Bremse).
