# Sela-2: Chat-, Basis- und Mischmodelle im Vergleich

Regel: docs/PREREG_SELA2.md §5 (festgelegt vor dieser Messung). M5 über drei Seeds, M7 mit Orakel-Absatz, M6 gegen das Basismodell, M3 gepoolt über sechs Aufgaben.

| Kandidat | M3 gepoolt | Δ zur Basis [95 %] | Schleifen | Limit | Rollen-Leck | Median | IFEval loose (Δ Basis) | HasAns-F1 | NoAns | Prüfungen |
|---|---|---|---|---|---|---|---|---|---|---|
| chat (früher) | 41.6 % | -4.0 [-4.9, -3.0] | 0.0 % ✓ | 10.0 % ✗ | 0.0 % ✓ | 36 ✓ | 18.3 (+4.8) ✗ | 34.7 ✗ | 47.6 % ✗ | 3/7 |
| base (früher) | 45.5 % | – | 0.0 % ✓ | 14.3 % ✗ | 0.0 % ✓ | 35 ✓ | 13.5 (+0.0) ✗ | 52.9 ✓ | 32.2 % ✗ | 4/7 |
| **mix30** (früher) | 45.7 % | +0.2 [-0.4, +0.8] | 0.3 % ✓ | 28.7 % ✗ | 0.0 % ✓ | 59 ✓ | 15.5 (+2.0) ✗ | 63.9 ✓ | 31.4 % ✗ | 4/7 |
| mix50 (früher) | 44.6 % | -0.9 [-1.6, -0.2] | 0.3 % ✓ | 25.0 % ✗ | 0.0 % ✓ | 50 ✓ | 15.7 (+2.2) ✗ | 60.3 ✓ | 31.6 % ✗ | 4/7 |
| mix70 (früher) | 43.4 % | -2.1 [-3.0, -1.3] | 0.0 % ✓ | 19.0 % ✗ | 0.0 % ✓ | 46 ✓ | 16.5 (+3.0) ✗ | 53.0 ✓ | 34.2 % ✗ | 4/7 |
| s21lr03 | 45.5 % | -0.0 [-0.5, +0.4] | 0.0 % ✓ | 12.7 % ✗ | 0.0 % ✓ | 40 ✓ | 13.1 (-0.4) ✗ | 53.7 ✓ | 31.8 % ✗ | 4/7 |
| s21lr10 | 45.0 % | -0.6 [-1.2, -0.0] | 0.0 % ✓ | 9.0 % ✗ | 0.0 % ✓ | 36 ✓ | 16.3 (+2.8) ✗ | 57.9 ✓ | 31.2 % ✗ | 4/7 |

Wiederholung der registrierten M5-Messung (Chat-Modell, Seed-Versatz 0): identisch

**Auswahl nach der Regel:** mix30

Die App bekommt `sela2-mix30.npz` statt `sela2-chat.npz`.

Kandidaten mit „(früher)“ stammen aus `results/sela2/variants` (früherer Lauf, gleiche Regel).
