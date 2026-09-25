# SPEC — ENGRAMM-LM (Stand v1.3/LM, 2026-09-25)

Technische Spezifikation des Sprachmodells aus `engramm/lm/`. Sie beschreibt, was der Code
tut, so genau, dass eine unabhängige Implementierung dieselben Zahlen liefern kann. Die
Kriterien stehen in `docs/PREREG_LM.md`, die Messwerte in `docs/EXPECTATIONS.md` (E12).

## 1. Daten und Tokens

| Schritt | Definition | Code |
|---|---|---|
| Korpus | C4-en Shard 0 (ein JSON = ein Dokument, Schlüssel URL) + WikiText-103-raw Train (Artikel = Zeilen ab `" = Titel = "`, WikiText-Tokenisierung zurückgebaut) | `data/lm_corpus.py` |
| Split | `SHAKE-256("engramm-lm/split/v1\0" ‖ Quelle ‖ "\0" ‖ Schlüssel)`, erste 8 Byte big-endian: `mod 10000` < 9930 train, < 9950 val-A, < 9970 val-B, sonst test; Hälfte = niedrigstes Bit | `split_of`, `split_half` |
| Tokenizer | Byte-Level-BPE, V = 32.768, ID 0 = `<\|eos\|>`, gelernt auf den ersten 256 MB Train-Text in Stromreihenfolge; Datei `data/lm_tokenizer.json`, SHA-256 `637745134e61…513d`; der Text „<\|eos\|>" ist gewöhnlicher Text | `engramm/lm/tokenizer.py` |
| Strom | `[EOS] d₁ [EOS] d₂ … [EOS]`, `uint16`; Train nach Split-Hash sortiert; Pilot = alle Dokumente, die ganz in die ersten 30 M Tokens passen | `engramm/lm/stream.py` |
| Near-Duplicate | Val/Test-Dokument ausgeschlossen, wenn ≥ 20 % seiner 13-Token-Fenster im vollen Train-Strom vorkommen | `experiments/lm_suffix.py` |

## 2. Komponenten

**Geschichte.** Jede Vorhersage sieht nur den eigenen Dokumentanfang: die Tokens nach dem
letzten `EOS` einschließlich dieses `EOS`.

### 2.1 KN5 — `engramm/lm/ngram.py`

Interpoliertes modified Kneser-Ney (Chen & Goodman 1998), Ordnung 5.
- Gültige n-Gramme: `EOS` nur an erster (Dokumentanfang) oder letzter Stelle (Ende).
- Angepasste Zählungen: höchste Ordnung roh; darunter Fortsetzungszählung N₁₊(•v), außer v beginnt mit `EOS` (dann roh).
- Discounts D₁, D₂, D₃₊ je Ordnung aus n₁…n₄ (Formel 26), Fallback (0,5; 1; 1,5), wenn ein nₖ = 0 ist oder ein D außerhalb (0, k) liegt.
- **Pruning** ab Ordnung 3: Einträge mit angepasster Zählung 1 fallen weg; der Backoff-Faktor wird γ'(h) = (N₁ + D₂N₂ + D₃N₃₊)/A(h) mit unbeschnittenen Kontextstatistiken. Die Verteilung bleibt exakt normiert. Kontexte ohne verbleibenden Eintrag fallen weg (γ' = 1).
- Unigramm interpoliert mit 1/V.
- Ein nicht gefundener Kontext überspringt die Ordnung.
- Schlüssel: Tokens zu je 15 Bit gepackt, erstes Token höchstwertig.

### 2.2 INF — `engramm/lm/suffix.py`

- Suffix-Array (divsufsort über das big-endian-Bytebild, nur gerade Offsets).
- h′ = längstes Suffix der Geschichte (≤ 128 Tokens) mit Vorkommen.
- p = count(h′w) / (Vorkommen von h′ mit Nachfolger).
- Ohne Treffer: p_KN.

### 2.3 CACHE — `engramm/lm/topic.py`

- Unigramm-Verteilung der bisherigen Dokument-Tokens.
- Leere Geschichte: p_KN.

### 2.4 Bedeutungsvektoren — `engramm/lm/semantic.py`

- D_s = 2.048 Bit. Kontextwörter: die 8.192 häufigsten vorkommenden Nicht-EOS-Tokens.
- Index-Vektor r_c = `ItemMemory(seed, 2048).vector("lm:ctx:<id>")`.
- **eng:** für o ∈ {−2, −1, 1, 2} die Paare (w bei i, c bei i+o) im selben Dokument. PPMI-Stufe L = #{k∈0..3 : c(w,c)·N > 2ᵏ·c(w)·c(c)}, mit N, c(w), c(c) aus der Matrix dieses Offsets. Dann S = Σ_o L_o·ρᵒ(r) (ρ = zyklische Rotation um o Bit).
- **weit:** alle |o| ≤ 16 in einer Matrix, ohne Rotation.
- Bit = S > 0. Für S = 0 gilt die Tie-Regel `TieContext.for_prototype(2048, "sem:{eng|weit}:<id>", seed)`.
- Tokens mit < 5 Vorkommen bekommen `vector("lm:rare:{kind}:<id>")`.
- IDF: größtes k ≤ 16 mit 2ᵏ·(df+1) ≤ #Dokumente, mindestens 1.
- **Wortklassen:** Hamming-k-Majority auf den eng-Vektoren, 511 Zentren.
  - Start: die 511 häufigsten Tokens.
  - Zuweisung zum nächsten Zentrum, bei Gleichstand das kleinste Zentrum.
  - Neues Zentrum = bitweise Mehrheit der Mitglieder mit ≥ 5 Vorkommen; bei Gleichstand bleibt das alte Bit.
  - ≤ 10 Runden. Klasse 0 = Dokumentgrenze.

### 2.5 KNN — `engramm/lm/knn.py`

- Speicher: alle Train-Positionen p ≥ 1, sortiert nach (Klassenschlüssel der 6 Vortokens, jüngstes zuerst, 9 Bit je Klasse; p).
- Kandidaten:
  - Tiefste Präfixtiefe d ∈ 6…1 mit ≥ 64 Positionen (bei d = 1 immer).
  - Bei mehr als 16.384 Positionen: die 16.384 um die Einfügestelle des eigenen Schlüssels.
- Distanz d = Σⱼ wⱼ·ham(eng[qⱼ], eng[cⱼ]) + 2·8·ham₂₅₆(sig_q, sig_seg(p)).
  - w = (8, 4, 2, 1, 1, 1); nach dem Dokumentanfang Token 0.
  - Segment-Signatur: 256-Bit-Bündel (erste 4 Wörter der weit-Vektoren, idf-gewichtet, Tie-Break-Vektor bei gerader Summe) je 128-Token-Segment.
  - Abfrage-Signatur: letzte ≤ 128 Tokens bis zum letzten 16er-Anker.
- p_knn(w) = Σ_{t[p]=w} K(d−d_min) / Σ K, mit K(Δ) = exp(−Δ/τ) aus der gespeicherten Tabelle.

### 2.6 TOPIC — `engramm/lm/topic.py`

- T = Bündel der weit-Vektoren der letzten ≤ 256 Tokens, idf-gewichtet, Anker alle 16 Tokens.
- p ∝ p_uni(w)·exp(β·(1024 − ham(T, weit[w]))/1024), mit Tabelle.
- Aktiv ab 16 Tokens Geschichte.

### 2.7 Mischung — `engramm/lm/mixture.py`

- Eimer = KN-Klasse (längster gefundener Kontext: ≤ 2, 3, 4, 5) × INF-Länge (≤ 4, 5–7, 8–15, ≥ 16) × KNN-d_min (Quartilsgrenzen auf val-A; ohne Kandidaten = Klasse 3).
- EM: 100 Iterationen ab Gleichverteilung auf val-A (Near-Duplicate-gefiltert).
- Systeme:

| System | Komponenten | Eimer |
|---|---|---|
| KN-5 | KN | — |
| KN-5+Cache | KN, CACHE | 4 |
| Null-Modell | KN, INF, CACHE | 16 |
| ENGRAMM-LM | alle fünf | 64 |

## 3. Nutzer-Stufe, Vergessen, Log — `engramm/lm/model.py`, `log.py`

- **learn_text / learn_texts:** Die Nutzer-Stufe ist eine Funktion der lebenden Texte, sortiert nach Quelle.
  - Tokens beginnen je Text auf einer eigenen 128er-Segmentgrenze.
  - Eigenes Suffix-Array; alle Nutzer-Positionen sind KNN-Kandidaten.
  - n-Gramm-Zählungen (Kontext 1–4) werden als ganzzahlige Summen geführt.
  - KN wird angepasst mit p′ = (c_u(h_k,w) + 2·p_KN)/(c_u(h_k) + 2) für den längsten Nutzerkontext h_k.
  - INF addiert Basis- und Nutzerzählungen bei gleicher Treffer-Länge.
- **forget:**
  - Nutzertext: wird entfernt, die Stufe neu gebildet. Der Digest ist identisch zu „nie gelernt".
  - Basisdokument: Tombstone. Nie mehr KNN-Kandidat, INF-Zählungen innerhalb des Dokuments werden abgezogen, nicht mehr zitiert.
  - `consolidate()` baut die Basis ohne Tombstones und mit den Nutzertexten neu (Epoche + 1).
- **Log:** L2-Rahmung, Arten H/T/F/E; Replay gegen denselben Basis-Digest.

## 4. Schreiben — `engramm/lm/generate.py`

- u_t = SHAKE-256(seed ‖ SHA-256(Prompt-IDs) ‖ t), 64 Bit.
- Temperatur; top-p über (−p, ID).
- Ziehung als ganzzahlige inverse CDF über ⌊p·2⁴⁰⌋.
- Verboten sind:
  - Tokens, die ein 4-Gramm des Texts wiederholen;
  - Fortsetzungen eines 32-Token-Zitats (Basis oder Nutzer).
- `why`: längste wörtliche Quelle und die nächsten ähnlichen Kontexte mit demselben Folgetoken.

## 5. Messung — `engramm/lm/evaluate.py`

- BPB = Σ −log₂p / Σ(UTF-8-Bytes + 1).
- Jedes Dokument einzeln, Kontext ab `EOS`.
- Bootstrap: 2.000 Replikate, Seed 42, über Dokumente; Verhältnisse gepaart.
