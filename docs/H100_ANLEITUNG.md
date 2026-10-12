# Anleitung: ENGRAMM auf einer gemieteten H100 bis GPT-2-Niveau trainieren

Stand 12. Oktober 2026. Ziel (Stufe 1, PLAN §6/§10/§11): Test-Satz ≤ 1,04 Bits pro Byte, das Niveau von GPT-2 small,
gemessen genau wie im CPU-Lauf.

## Kurz gesagt

| | |
|---|---|
| Was du tust | Konto anlegen, Guthaben aufladen, eine GPU mieten, **drei Befehle** einfügen, am Ende prüfen, dass der Pod weg ist |
| Was automatisch passiert | Daten laden und prüfen, Lernrate suchen, trainieren, messen, Ergebnisse auf GitHub sichern, Pod löscht sich selbst |
| Dauer | ca. 6,5–7,5 Stunden, davon 15 Minuten mit dir |
| Kosten | ca. 25–30 $ (+ ggf. Steuer); Guthaben 50 $ aufladen, der Rest bleibt auf dem Konto |
| Ergebnis | Messwerte im Repository (Branch `h100-results-…`), das Modell (≈ 270 MB) als privater Entwurf unter „Releases“ |
| Ehrlich | GPT-2-Niveau ist wahrscheinlich (meine Schätzung ~70 %), nicht garantiert. Auch ohne Ziel sind alle Messungen gesichert |

## Was die Skripte für dich absichern

| Risiko | Schutz |
|---|---|
| Falsche oder kaputte Daten | Jede Quelldatei ist per SHA-256 festgelegt; die nachgebauten Prüfdaten müssen **bitgleich** zum CPU-Rechner sein, sonst Abbruch vor dem Training |
| Testdaten im Training (geschönte Werte) | Zusatztext nur aus dem Trainings-Bereich der Hash-Aufteilung; danach Prüfung aller 13-Token-Fenster der Test-Dokumente im gesamten Trainingstext (Prüfcode reproduziert die bisherige Liste exakt) |
| Falsche Lernrate | Kurze Suche über drei Werte vor dem Hauptlauf |
| Zu teuer, falls die GPU langsamer ist | Zeitgrenze 5,5 h für das Haupttraining; die Tokenzahl wird nach den ersten Minuten angepasst |
| Speicher der GPU reicht nicht | Teil-Batches werden automatisch halbiert |
| Training „explodiert“ | Erkennung; einmaliger Neustart mit halber Lernrate |
| Abbruch / Neustart des Pods | Zustand alle 30 min gesichert; derselbe Startbefehl setzt fort |
| Pod läuft nach dem Ende weiter und kostet | Pod löscht sich selbst — **nur** nachdem Ergebnisse und Modell nachweislich auf GitHub liegen |

---

## Schritt 1 – Konto und Guthaben (10 Minuten, einmalig)

1. **RunPod-Konto:** <https://www.runpod.io> → *Sign up* → E-Mail bestätigen.
2. **Guthaben:** links *Billing* → *Add Credits* → **50 $** (Kreditkarte).
   - Guthaben wird nicht erstattet, verfällt aber nicht. Erwartet sind ~25–30 $.
   - Wichtig: Fällt das Guthaben auf 0, löscht RunPod den Pod samt Daten. 50 $ decken auch den ungünstigsten Fall.
3. **GitHub-Schlüssel (dringend empfohlen, sonst musst du Ergebnisse von Hand herunterladen):**
   - <https://github.com/settings/personal-access-tokens/new> (*Settings → Developer settings → Personal access tokens →
     Fine-grained tokens → Generate new token*)
   - *Token name:* `engramm-h100` · *Expiration:* 7 days
   - *Repository access:* **Only select repositories** → `erithy25/engramm`
   - *Permissions → Repository permissions → Contents:* **Read and write**
   - *Generate token* → den Schlüssel (`github_pat_…`) kopieren und kurz in einer Notiz ablegen. Er wird nur einmal angezeigt.

## Schritt 2 – GPU mieten (5 Minuten)

1. Links **Pods** → **Deploy**.
2. **Secure Cloud** wählen (nicht Community: zuverlässiger, ~1 $/h teurer).
3. GPU: **H100 SXM** (80 GB), Anzahl **1**. Falls nicht verfügbar: **H100 NVL** oder **H100 PCIe** (läuft auch, etwas langsamer).
4. Template (Vorlage): **Runpod PyTorch** in der **neuesten** Version (PyTorch 2.4 oder neuer).
5. *Edit Template* bzw. Speicher-Einstellungen: **Container Disk 50 GB**, **Volume Disk 100 GB** (Pfad `/workspace`).
6. **Deploy On-Demand** (nicht „Spot“/„Interruptible“ – die können mitten im Lauf weggenommen werden).
7. Warten, bis der Pod **Running** zeigt (1–3 Minuten). Ab jetzt läuft die Uhr (~4 $/h).

## Schritt 3 – Training starten (5 Minuten)

1. Beim Pod auf **Connect** → **Jupyter Lab** (öffnet sich im Browser) → dort *File → New → Terminal*.
2. **Befehl 1** einfügen (Rechtsklick → Einfügen oder Strg+Shift+V) und Enter:

   ```bash
   cd /workspace && git clone --depth 1 -b claude/optimistic-cannon-i0u0ap https://github.com/erithy25/engramm.git && cd engramm
   ```

3. **Befehl 2** (GitHub-Schlüssel; er wird beim Einfügen **nicht angezeigt** – das ist richtig) einfügen, Enter,
   dann den Schlüssel einfügen und noch einmal Enter:

   ```bash
   read -s -p "GitHub-Schlüssel einfügen, dann Enter: " GH_TOKEN; export GH_TOKEN; echo; echo "Schlüssel gesetzt (${#GH_TOKEN} Zeichen)"
   ```

   Es muss „Schlüssel gesetzt (93 Zeichen)“ o. ä. erscheinen (nicht 0).
4. **Befehl 3** – Start:

   ```bash
   setsid nohup bash experiments/h100_run.sh > /workspace/h100_console.log 2>&1 &
   ```

5. Nach 1–2 Minuten prüfen, dass es läuft:

   ```bash
   bash /workspace/engramm/experiments/h100_status.sh
   ```

   Es sollten „[x] Pakete“ und bald „[x] Basisdaten“ erscheinen. **Du kannst den Browser jetzt schließen** – der Lauf
   geht weiter.

## Schritt 4 – Während es läuft (optional)

Jederzeit: Pod → *Connect* → *Jupyter Lab* → Terminal → Status:

```bash
bash /workspace/engramm/experiments/h100_status.sh
```

Live-Protokoll (Strg+C beendet nur die Anzeige, nicht das Training): `tail -f /workspace/h100/run.log`

| Phase | Dauer (Schätzung) |
|---|---|
| Prüfungen, Pakete | 2–5 min |
| Basisdaten (Download 630 MB, Tokenisierung, Bit-Prüfung) | 10–20 min |
| Lernraten-Suche (GPU), gleichzeitig Zusatztext: 36 C4-Teile, ~11 GB Download (CPU) | 30–45 min |
| Zusammenführen und Kontaminationsprüfung | 5–15 min |
| **Haupttraining** (bis 6 Mrd. Token, Grenze 5,5 h) | **4,5–5,5 h** |
| Endmessung, Textproben, Hochladen | 10–20 min |
| **Gesamt** | **≈ 6,5–7,5 h** |

## Schritt 5 – Am Ende

**Mit GitHub-Schlüssel (Normalfall):** Im Protokoll steht „FERTIG. Ergebnisse und Modell sind auf GitHub gesichert. Der
Pod beendet sich in 2 Minuten selbst.“

1. Schreib mir einfach **„H100 fertig“** – ich hole die Ergebnisse (Branch `h100-results-…`), rechne die Mischung mit
   dem Zählmodell und berichte.
2. **Kontrolle (wichtig, 1 Minute):** RunPod → *Pods*: Der Pod darf nicht mehr da sein. Falls doch: aufklappen →
   **Stop** (Quadrat) → **Terminate** (Mülleimer) → bestätigen. Unter *Billing* darf nichts mehr laufen.
3. Das Modell liegt privat (nur für dich sichtbar) unter <https://github.com/erithy25/engramm/releases> als Entwurf.

**Ohne GitHub-Schlüssel:** Im Protokoll steht „FERTIG. JETZT: Archiv und Modell herunterladen …“.

1. In Jupyter Lab links im Dateibrowser: `h100/h100_results.tgz` und `h100/ckpt/model_main.pt` → Rechtsklick → **Download**.
2. Danach Pod **beenden**: *Pods* → aufklappen → **Stop** → **Terminate** → bestätigen. **Sonst kostet er weiter (~4 $/h).**
3. Mir Bescheid geben; die Ergebnisse müssen dann noch ins Repository (ich sage dir wie).

## Was tun, wenn …

| Situation | Lösung |
|---|---|
| Status zeigt „FEHLER: …“ | Die Zeilen an mich schicken. Meist reicht derselbe Startbefehl (Schritt 3, Befehl 3); er setzt fort |
| Pod wurde neu gestartet / Terminal zeigt nichts | Terminal öffnen, `cd /workspace/engramm`, Befehl 2 (Schlüssel) und Befehl 3 wiederholen – es geht beim letzten Stand weiter |
| „keine GPU“ / „torch zu alt“ | Pod beenden, neu mieten mit neuerem *Runpod PyTorch*-Template |
| „zu wenig Platz“ | Pod beenden, neu mieten mit Volume Disk 100 GB |
| H100 SXM nicht verfügbar | H100 NVL oder H100 PCIe nehmen; die Zeitgrenze kürzt notfalls die Tokenzahl |
| Guthaben wird knapp | Unter *Billing* nachladen (Lauf läuft weiter) |
| Du willst abbrechen | *Pods* → Stop → Terminate. Bereits Gesichertes auf GitHub bleibt erhalten |

## Technische Details (für mich / zum Nachprüfen)

- Skripte: `experiments/h100_run.sh` (Ablauf), `experiments/h100_data.py` (Daten), `experiments/h100_train.py`
  (Training, Endmessung), `experiments/h100_status.sh` (Status). CPU-Tests: `h100_train smoke`, `h100_data check-dedup`.
- Modell: Rezept fast-v1 aus dem CPU-Lauf, Größe GPT-2 small (d = 768, 12 Schichten, 12 Köpfe), Kontext 1.024 von Anfang an,
  bf16, 524.288 Token je Schritt, AdamW (β₂ 0,95), WSD (300 Aufwärmschritte, Abnahme in den letzten 30 %).
- Daten: Basis (C4-Teil 0 + WikiText-103, 285 Mio. Token, bitgleich) + C4-Teile 1–36 (nur Trainings-Hash-Bereich),
  zusammen ≈ 6 Mrd. Token.
- Messung: wie PLAN §10 (Fenster 1.024 / Schritt 512, gefiltert, gepaarter Bootstrap gegen GPT-2 small), zusätzlich mit
  der erweiterten Duplikat-Liste des Zusatztexts. Die Mischung mit dem Zählmodell rechne ich danach auf dem CPU-Rechner
  aus den gespeicherten Token-Wahrscheinlichkeiten.
- Einstellungen per Umgebungsvariable: `H100_BUDGET_HOURS` (5.5), `H100_SHARDS` (36), `H100_TOKENS` (6000000000),
  `H100_AUTO_END` (`terminate` | `stop` | `none`).
