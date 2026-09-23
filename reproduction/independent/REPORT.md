# Independent reproduction of the ENGRAMM rebuild from SPEC_REBUILD.md

I rebuilt the classifier using only `SPEC_REBUILD.md` and the five raw archives in `data/`. I did not open, grep or import anything else from the repository. Everything ran with `/home/user/engramm/.venv/bin/python -I` (CPython 3.11.15, NumPy 2.4.1, OpenBLAS 0.3.30) and a clean environment (`env -u PYTHONPATH`). Seed 42, D = 10000.

## Summary

* **All 185 conformance checks pass**, 0 fail. This covers every applicable item of §14 plus a few internal cross-checks marked `impl`. It includes the two values the spec says it did not recompute itself (§15 items 7 and 8), both reproduced here from scratch:
  * the SHA-256 of all 60,000 MNIST training encodings;
  * the (d) T2 miss counts, 3,215 and 3,110.
* The four configurations ran on the full test sets. The predictions are in `out/<config>_predictions.npy` (int64, dataset label order).

## Results

| config | n_test | accuracy | macro-F1 | predictions_sha256 | T2 error per epoch (misses) | runtime (wall) |
|---|---|---|---|---|---|---|
| (a) WiLI 10-shot, T1 | 117500 | 0.8488510638297873 | 0.8517737694590454 | `feee1e1f3f48dca0755c58650b491fec5fe8fff0c926e12857e50ef16805d592` | – | 128.5 s (incl. 103.3 s test encoding) |
| (b) MNIST, T1 | 10000 | 0.8054 | 0.802902746307128 | `4ba1886c3c83a82390eed7b0f8b9aec484812f0326fdf05856cdc717d6efcd45` | – | 2.2 s + shared MNIST encoding 74.7 s |
| (c) MNIST, T1 + 2×T2, λe = 0 | 10000 | 0.8542 | 0.85215118003707 | `fbea206a4e913c96e7b61ff174d1ac1ba398e5cbade2d9ca52ab38cb1cd64f08` | [0.179117, 0.152083] (10747, 9125) | 5.9 s (T2 3.3 s) + encoding |
| (d) MNIST full pipeline | 10000 | 0.9488 | 0.9489597256813207 | `54a7785a8c6b30e55509c5074b5b5370b41dd8155dd7f1b60dd3355cb7fe96db` | [0.053583, 0.051833] (3215, 3110) | 1125.6 s (LOO retrieval 965.8 s, T2 4.9 s, test retrieval 152.0 s) + encoding |

* Macro-F1 is computed two ways: with the Appendix B pairwise sum and with `numpy.mean`. The two are bit-identical in all four runs.
* The predictions digests were recomputed independently from the saved `.npy` files, and they match.
* Other (a) fields:
  * `test_items_in_train` = 3147.
  * `accuracy_excluding_train_duplicates` = 0.8496235341442726.
* Other (d) values:
  * halvings: 0;
  * final max|A|: 7253 (the spec gives no value for this);
  * final utilities: 59,192 non-zero, range −8…8.
* Runtimes come from a shared 4-core machine that other jobs were loading heavily (load average 11–14 during (d)). They are only indicative.

## Implementation notes (how exactness was obtained)

* **RNG.** I used NumPy's own `default_rng`, `choice` and `permutation`. I checked them against a transcription of Appendix A for every call pattern used: all 235 WiLI `choice` calls, the thermometer `permutation(10000)`, and both T2 `permutation(60000)` calls. They agree.
* **Trigram encoder.** Packed uint64 XOR of the three rotated item vectors, then exact column bit-counts (SWAR byte lanes, in blocks of 255 rows). I checked this against a naive unpack-and-sum on random texts and on every §14.4 vector.
* **Thermometer encoder.** An exact float32 GEMM reformulation that uses the progressive-level structure: component j of level q is flipped iff q ≥ rank(j)//333 + 1. I checked it against the naive 784-way XOR sum and against every §14.5 digest.
* **Retrieval.** Exact float32 GEMM on ±1 vectors. The sort key is `(dist << 20) | rank`, selected with `argpartition` and then sorted. I cross-checked 5 queries against a brute-force popcount and Python sort.
* **T2 fused score.** The §11.4 formula in pure Python binary64, in retrieval order. §14.9's `5.856550000000001` is reproduced exactly.

## Conformance checklist results

Section numbers refer to the spec. `impl` rows are my own internal cross-checks. "(same)" means the obtained value equals the expected value. Some checks appear more than once because they were re-asserted inside the end-to-end runner, marked `[runner]`, or for each of (b), (c) and (d).

| # | § | check | result | value obtained | expected (spec) |
|---|---|---|---|---|---|
| 1 | 4 | rho^1 D=16 [C0,01] | PASS | `e000` | (same) |
| 2 | 4 | rho^2 D=16 [C0,01] | PASS | `7000` | (same) |
| 3 | 2 | packbits example | PASS | `8001` | (same) |
| 4 | 3 | IM(a) first 8 | PASS | `523f0c1100d43dbd` | (same) |
| 5 | 3 | IM(a) first 16 components | PASS | `0101001000111111` | (same) |
| 6 | 14.3 | IM(a) sha256 | PASS | `c80826456f683afcc9e1d6af917a07c9b228cb0700a10f9200c69c6dc3dd2a8b` | (same) |
| 7 | 14.3 | IM(a) popcount | PASS | `5011` | (same) |
| 8 | 4 | rho^2(IM(a)) first 8 | PASS | `148fc30440350f6f` | (same) |
| 9 | 4 | rho^1(IM(a)) first 8 | PASS | `291f8608806a1ede` | (same) |
| 10 | 14.3 | IM(\x00) first 8 | PASS | `7a70e7f7351608f6` | (same) |
| 11 | 14.3 | IM(h) first 8 | PASS | `d24986c03dfa12bb` | (same) |
| 12 | 14.3 | IM(pixel:0) first 8 | PASS | `afddd6de5311e14a` | (same) |
| 13 | 14.3 | IM(pixel:783) first 8 | PASS | `42abbd45d8903552` | (same) |
| 14 | 14.3 | IM(thermometer:base) first 8 | PASS | `cc20929fdacc2b2f` | (same) |
| 15 | 14.3 | IM(thermometer:base) sha256 | PASS | `33c85042f39eca24b790e477b9eb75bc4c68439ccbaba0e5915240a2681e9fa5` | (same) |
| 16 | 14.3 | IM(a) seed 7 first 8 | PASS | `763264777c3538a9` | (same) |
| 17 | 14.3 | 256 byte-symbol stack sha256 | PASS | `b8cfa6c95726d2c53273497c451580cf2fcd9b9e6260eaa52d8915fd39599036` | (same) |
| 18 | 14.3 | 784 position stack sha256 | PASS | `9171ffbabe0f3a0f955cb215a7c1fca24932ed6a50dfe62f5fc5857b3fa5d3e3` | (same) |
| 19 | 14.6 | proto stream '0' | PASS | `776ca019dfb2eabd` | (same) |
| 20 | 14.6 | proto stream '1' | PASS | `88eaba1c35868e7c` | (same) |
| 21 | 14.6 | proto stream 'ace' | PASS | `f98083b7a18ae24c` | (same) |
| 22 | 14.2 | PCG64 state | PASS | `0xcea44f6798798f2aacbc7c9d68860ac8` | (same) |
| 23 | 14.2 | PCG64 inc | PASS | `0xfa505436c9a8416e66caf2e28d25abff` | (same) |
| 24 | 14.2 | first 3 raw | PASS | `['0xc621fbcd16d92688', '0x705a5661a791ffc1', '0xdbcd12c26eda1624']` | (same) |
| 25 | A | appendix PCG64(42) first 3 raw | PASS | `['0xc621fbcd16d92688', '0x705a5661a791ffc1', '0xdbcd12c26eda1624']` | (same) |
| 26 | 14.2 | thermometer seed digest | PASS | `3b2dc15762e2d7bf` | (same) |
| 27 | 14.2 | thermometer seed int | PASS | `4264277003255076799` | (same) |
| 28 | 14.2 | order[0:10] | PASS | `[2562, 8813, 3284, 2626, 5087, 6837, 2256, 2241, 1915, 2629]` | (same) |
| 29 | 14.2 | order[330:336] | PASS | `[6610, 5863, 7506, 4645, 9618, 1941]` | (same) |
| 30 | A | appendix permutation(10000) == numpy | PASS | `True` | (same) |
| 31 | 14.2 | T2 epoch1 first 16 | PASS | `[3493, 57546, 8815, 19332, 15566, 22963, 21972, 22093, 1818, 46044, 31538, 36479, 9523,...` | (same) |
| 32 | 14.2 | T2 epoch2 first 16 | PASS | `[17284, 27577, 35294, 27278, 56928, 12169, 6580, 45132, 27388, 57966, 17348, 27607, 318...` | (same) |
| 33 | A | appendix two permutation(60000) == numpy | PASS | `True` | (same) |
| 34 | 14.1 | x_train.txt sha256 | PASS | `afac7e069450ec7ac2995c7b8203ae9445404a68dbc7a66fedb0f64d3720a12e` | (same) |
| 35 | 14.1 | x_train.txt size | PASS | `64085137` | (same) |
| 36 | 14.1 | y_train.txt sha256 | PASS | `bd0d63a9ab19cb15594588d1bb1b43c4b1b39d7f102656a391c259ca862e0753` | (same) |
| 37 | 14.1 | x_test.txt sha256 | PASS | `c06db2b42ae5a29428aca5ab9505c5117cbdeb82538eb1b087f55a6627c45556` | (same) |
| 38 | 14.1 | x_test.txt size | PASS | `65166417` | (same) |
| 39 | 14.1 | y_test.txt sha256 | PASS | `2fbc58bc6f34c8cea1587396d82986a2637adf5ecb2b5cbd8f2a20be0f81ad11` | (same) |
| 40 | 1.2 | x_train.txt ends with \n and splitlines == raw \n split | PASS | `True` | (same) |
| 41 | 1.2 | x_test.txt ends with \n and splitlines == raw \n split | PASS | `True` | (same) |
| 42 | 14.1 | line counts | PASS | `[117500, 117500, 117500, 117500]` | (same) |
| 43 | 14.1 | first five y_train | PASS | `est swe mai oci tha` | (same) |
| 44 | 14.1 | labels | PASS | `ace afr als amh ang ara arg arz asm ast ava aym azb aze bak bar bcl be-tarask bel ben b...` | (same) |
| 45 | 1.2 | shortest text bytes | PASS | `140` | (same) |
| 46 | 1.2 | longest train text bytes | PASS | `120424` | (same) |
| 47 | 1.2 | longest test text bytes / index | PASS | `(579350, 24169)` | (same) |
| 48 | 1.3 | test_items_in_train | PASS | `3147` | (same) |
| 49 | 1.3 | class 0 candidates first 5 / count | PASS | `([221, 645, 865, 914, 1063], 500)` | (same) |
| 50 | 14.2 | choice class 0 (returned order) | PASS | `[12688, 91494, 12915, 80191, 51818, 51210, 84232, 13622, 26676, 99986]` | (same) |
| 51 | 14.2 | choice class 1 (returned order) | PASS | `[95435, 48250, 42647, 79867, 100763, 20138, 54773, 62581, 69173, 110892]` | (same) |
| 52 | 14.2 | selected first 16 | PASS | `[87, 90, 135, 172, 222, 312, 352, 360, 366, 392, 438, 439, 460, 551, 602, 653]` | (same) |
| 53 | 14.2 | selected last 4 | PASS | `[117281, 117359, 117363, 117404]` | (same) |
| 54 | 14.2 | selected count / distinct | PASS | `(2350, 2350)` | (same) |
| 55 | 14.2 | selected sha256 (u64be) | PASS | `3694426073025dbb04a285b339e3319e5071c83f7950e3ffb9af5d1a3c652891` | (same) |
| 56 | 14.2 | labels of first five selected | PASS | `jbo por kor ina mdf` | (same) |
| 57 | A | appendix choice == numpy choice for all 235 classes | PASS | `True` | (same) |
| 58 | 14.1 | train images header | PASS | `000008030000ea600000001c0000001c` | (same) |
| 59 | 14.1 | test images header | PASS | `00000803000027100000001c0000001c` | (same) |
| 60 | 14.1 | train labels magic/count | PASS | `(2049, 60000)` | (same) |
| 61 | 14.1 | test labels magic/count | PASS | `(2049, 10000)` | (same) |
| 62 | 1.4 | decompressed sizes | PASS | `[47040016, 60008, 7840016, 10008]` | (same) |
| 63 | 14.1 | y_train[0:10] | PASS | `[5, 0, 4, 1, 9, 2, 1, 3, 1, 4]` | (same) |
| 64 | 14.1 | y_test[0:10] | PASS | `[7, 2, 1, 0, 4, 1, 4, 9, 5, 9]` | (same) |
| 65 | 14.1 | train class counts | PASS | `[5923, 6742, 5958, 6131, 5842, 5421, 5918, 6265, 5851, 5949]` | (same) |
| 66 | 14.1 | train pixels sha256 | PASS | `741c988805d008ac6e4c904b69001ba184c24b2c540a4ef403f4c71b676cf757` | (same) |
| 67 | 14.1 | test pixels sha256 | PASS | `6d87418db22cc8025d05968bec9bd5c3932904b23485740db143a061a2c9d161` | (same) |
| 68 | 14.4 | 'hello' bytes | PASS | `68656c6c6f` | (same) |
| 69 | 14.4 | 'hello' fast==reference sums | PASS | `True` | (same) |
| 70 | 14.4 | 'hello' trigrams | PASS | `3` | (same) |
| 71 | 14.4 | 'hello' T[0:8] | PASS | `[1, 1, -1, 1, -1, 1, 1, -1]` | (same) |
| 72 | 14.4 | 'hello' ties | PASS | `0` | (same) |
| 73 | 14.4 | 'hello' first 8 | PASS | `d636e7709d14afbb` | (same) |
| 74 | 14.4 | 'hello' sha256 | PASS | `90cea789dc0c80f9552aa026e0d60b339853eb1f336e1161cc6e546ab0834512` | (same) |
| 75 | 14.4 | 'hello!' bytes | PASS | `68656c6c6f21` | (same) |
| 76 | 14.4 | 'hello!' fast==reference sums | PASS | `True` | (same) |
| 77 | 14.4 | 'hello!' trigrams | PASS | `4` | (same) |
| 78 | 14.4 | 'hello!' T[0:8] | PASS | `[0, 0, 0, 0, 0, 2, 2, 0]` | (same) |
| 79 | 14.4 | 'hello!' ties | PASS | `3734` | (same) |
| 80 | 14.4 | 'hello!' first 8 | PASS | `a63ec5f19d14ff3b` | (same) |
| 81 | 14.4 | 'hello!' sha256 | PASS | `a92e43456c4fa1dba304c548654a0a0696c38f9fe423f23e04e1cfde0ec5a424` | (same) |
| 82 | 14.4 | 'abc' bytes | PASS | `616263` | (same) |
| 83 | 14.4 | 'abc' fast==reference sums | PASS | `True` | (same) |
| 84 | 14.4 | 'abc' trigrams | PASS | `1` | (same) |
| 85 | 14.4 | 'abc' T[0:8] | PASS | `[-1, 1, 1, 1, 1, 1, 1, -1]` | (same) |
| 86 | 14.4 | 'abc' ties | PASS | `0` | (same) |
| 87 | 14.4 | 'abc' first 8 | PASS | `7e8bad9e21c366ce` | (same) |
| 88 | 14.4 | 'Grüße, Welt' bytes | PASS | `4772c3bcc39f652c2057656c74` | (same) |
| 89 | 14.4 | 'Grüße, Welt' fast==reference sums | PASS | `True` | (same) |
| 90 | 14.4 | 'Grüße, Welt' trigrams | PASS | `11` | (same) |
| 91 | 14.4 | 'Grüße, Welt' T[0:8] | PASS | `[-3, -3, -1, 1, 5, -3, 1, -1]` | (same) |
| 92 | 14.4 | 'Grüße, Welt' ties | PASS | `0` | (same) |
| 93 | 14.4 | 'Grüße, Welt' first 8 | PASS | `1aac47d925c0a4a2` | (same) |
| 94 | 14.4 | hello! identity length | PASS | `2509` | (same) |
| 95 | 14.4 | hello! first tied components | PASS | `[0, 1, 2, 3, 4, 7, 12, 18]` | (same) |
| 96 | 14.4 | hello! stream bits at those | PASS | `[1, 0, 1, 0, 0, 0, 1, 0]` | (same) |
| 97 | impl | fast trigram counter == reference on random texts | PASS | `True` | (same) |
| 98 | 14.4 | train ex0 label/len/first8 | PASS | `('jbo', 211, '97e54740fa8cb897')` | (same) |
| 99 | 14.4 | train ex1 label/len/first8 | PASS | `('por', 243, '69d6836e5fb20815')` | (same) |
| 100 | 14.4 | all 2350 train encodings sha256 | PASS | `b6913b93826ffe119b63b4d66e5e2b16099a6053689c49212ee4a53980773628` | (same) |
| 101 | 14.4 | test0 label/len/first8 | PASS | `('mwl', 665, 'ab844237c3475c90')` | (same) |
| 102 | 14.4 | first 100 test encodings sha256 | PASS | `bc47359e3bc03f90628d3864a89eebd0dbdd1cd47110a829ce1cd886358c2f89` | (same) |
| 103 | 14.4 | first 100 test texts with a tie | PASS | `48` | (same) |
| 104 | 14.5 | L0 first8 | PASS | `cc20929fdacc2b2f` | (same) |
| 105 | 14.5 | L1 first8 | PASS | `cc20929f9acc0b2f` | (same) |
| 106 | 14.5 | L2 first8 | PASS | `ce20929f9acc1b2f` | (same) |
| 107 | 14.5 | L15 first8 | PASS | `0b95c7b6218091fc` | (same) |
| 108 | 14.5 | H(L0,L1),H(L7,L8),H(L0,L15) | PASS | `(333, 333, 4995)` | (same) |
| 109 | 14.5 | level table sha256 | PASS | `2aea6a170fd74c7f77664eeb0ba78104893511f46a6cd6c4e80520ac23e3eecf` | (same) |
| 110 | 14.5 | quantisation | PASS | `[0, 0, 1, 7, 8, 15]` | (same) |
| 111 | 14.5 | Pos0 xor L0 first8 | PASS | `63fd444189ddca65` | (same) |
| 112 | impl | thermometer GEMM sums == reference (sampled) | PASS | `True` | (same) |
| 113 | 14.5 | training 0 label/ties/T[0:8]/first8 | PASS | `(5, 271, [-14, 10, -24, -10, 12, 8, 2, 0], '4eed2e2f2d522685')` | (same) |
| 114 | 14.5 | training 1 label/ties/T[0:8]/first8 | PASS | `(0, 283, [-22, 18, -24, -10, 12, 34, -50, -12], '4cd81c063d123686')` | (same) |
| 115 | 14.5 | test 0 label/ties/T[0:8]/first8 | PASS | `(7, 272, [-32, 24, -24, -10, 12, 16, -10, 8], '4dc81d271c5234d7')` | (same) |
| 116 | 14.5 | test 1 label/ties/T[0:8]/first8 | PASS | `(2, 262, [18, 18, -24, -10, 12, 12, 0, -22], 'cec82e2f0c1636c7')` | (same) |
| 117 | 14.5 | first 1000 train encodings sha256 | PASS | `39efb3167dd91b99d60201ad8996d2363cccbe94bf02a8f5072c7de0ca0b25d2` | (same) |
| 118 | 14.5 | first 1000 test encodings sha256 | PASS | `24e8d4226032991db7d1534022b8f8868c160f70dc01aec9e7fa1edd6adc972c` | (same) |
| 119 | 14.7 | (a) model labels == dataset labels | PASS | `True` | (same) |
| 120 | 14.7 | (a) A sha256 (int16 LE) | PASS | `7d7fad7d6b95959531e7a2a780a9a0e3ecec7cfc99789b4ec6f88461a42496a3` | (same) |
| 121 | 14.7 | (a) P sha256 | PASS | `d6b6964c9a84b9aec50be9996aa0a61dc3fdc75dc40dd166f5a5f60328f8bcd7` | (same) |
| 122 | 14.7 | (a) zeros in A total / in ace | PASS | `(264024, 1132)` | (same) |
| 123 | 14.7 | (a) A[ace][0:8] | PASS | `[4, -2, -4, -4, -2, -2, 8, 8]` | (same) |
| 124 | 14.7 | (a) P[ace] first 8 | PASS | `83b10e5a29653b3f` | (same) |
| 125 | 14.7 | (a) halvings | PASS | `0` | (same) |
| 126 | impl | halve() | PASS | `[0, 1, -1, 1, -1, 8192, -8193, 3]` | (same) |
| 127 | 14.9 | id_0..id_2 | PASS | `['ab6dcd5d3aab77ec', '1cbfa3bd5d2d0c09', 'dab99623275d09ab']` | (same) |
| 128 | 14.7 | (a) A sha256 [runner] | PASS | `7d7fad7d6b95959531e7a2a780a9a0e3ecec7cfc99789b4ec6f88461a42496a3` | (same) |
| 129 | 14.7 | (a) P sha256 [runner] | PASS | `d6b6964c9a84b9aec50be9996aa0a61dc3fdc75dc40dd166f5a5f60328f8bcd7` | (same) |
| 130 | 14.4 | first 100 test encodings sha256 [runner] | PASS | `bc47359e3bc03f90628d3864a89eebd0dbdd1cd47110a829ce1cd886358c2f89` | (same) |
| 131 | 14.5 | first 1000 train encodings sha256 [runner] | PASS | `39efb3167dd91b99d60201ad8996d2363cccbe94bf02a8f5072c7de0ca0b25d2` | (same) |
| 132 | 14.5 | all 60000 train encodings sha256 | PASS | `c9ca644eac5c3a55dc8de32f9a73bf12c311f35ec7feed368bb90fb27f8dca79` | (same) |
| 133 | 14.5 | first 1000 test encodings sha256 [runner] | PASS | `24e8d4226032991db7d1534022b8f8868c160f70dc01aec9e7fa1edd6adc972c` | (same) |
| 134 | 14.7 | MNIST T1 A sha256 (b, 12 batches) | PASS | `b14227b9968fc12c5cd6eb50f11e9f27f9cefade3e5ffaf8aa88cd3c3912359a` | (same) |
| 135 | 14.7 | MNIST T1 P sha256 (b, 12 batches) | PASS | `60f9d66f0df01b577b953821eda4579aa3cc431aa117c17308a8f033a39eae32` | (same) |
| 136 | 14.7 | MNIST T1 zeros per class (b, 12 batches) | PASS | `[0, 1, 1, 0, 0, 0, 0, 0, 0, 0]` | (same) |
| 137 | 14.7 | MNIST T1 max/A/ (b, 12 batches) | PASS | `6742` | (same) |
| 138 | 14.7 | MNIST T1 A[0][0:8], P[0] first8 (b, 12 batches) | PASS | `([-4325, 3499, -5923, -5923, 5923, 4949, -3441, -3931], '4cc82f061d5236c7')` | (same) |
| 139 | 14.7 | MNIST T1 A[1][0:8], P[1] first8 (b, 12 batches) | PASS | `([-6580, 5954, -6742, -6742, 6742, 6552, -3234, -1210], '4ce90e0f1f5236d7')` | (same) |
| 140 | 14.7 | MNIST T1 A sha256 (c, one call) | PASS | `b14227b9968fc12c5cd6eb50f11e9f27f9cefade3e5ffaf8aa88cd3c3912359a` | (same) |
| 141 | 14.7 | MNIST T1 P sha256 (c, one call) | PASS | `60f9d66f0df01b577b953821eda4579aa3cc431aa117c17308a8f033a39eae32` | (same) |
| 142 | 14.7 | MNIST T1 zeros per class (c, one call) | PASS | `[0, 1, 1, 0, 0, 0, 0, 0, 0, 0]` | (same) |
| 143 | 14.7 | MNIST T1 max/A/ (c, one call) | PASS | `6742` | (same) |
| 144 | 14.7 | MNIST T1 A[0][0:8], P[0] first8 (c, one call) | PASS | `([-4325, 3499, -5923, -5923, 5923, 4949, -3441, -3931], '4cc82f061d5236c7')` | (same) |
| 145 | 14.7 | MNIST T1 A[1][0:8], P[1] first8 (c, one call) | PASS | `([-6580, 5954, -6742, -6742, 6742, 6552, -3234, -1210], '4ce90e0f1f5236d7')` | (same) |
| 146 | 14.8 | (c) T2 misses per epoch | PASS | `[10747, 9125]` | (same) |
| 147 | 14.8 | (c) t2_error_per_epoch | PASS | `[0.179117, 0.152083]` | (same) |
| 148 | 14.8 | (c) A sha256 after T2 | PASS | `6f84e91d2eb131ad90e2fd2fba4c165cb7de77fdd00155cd9474240e31d614b5` | (same) |
| 149 | 14.8 | (c) P sha256 after T2 | PASS | `a8b15f4c1e647d9066d4ee2a4ccc88a4db6c3c11fe8ed6d236553bfe78bc44b8` | (same) |
| 150 | 14.8 | (c) max/A/ / halvings / utilities all 0 | PASS | `(7015, 0, 0)` | (same) |
| 151 | 14.7 | MNIST T1 A sha256 (d) | PASS | `b14227b9968fc12c5cd6eb50f11e9f27f9cefade3e5ffaf8aa88cd3c3912359a` | (same) |
| 152 | 14.7 | MNIST T1 P sha256 (d) | PASS | `60f9d66f0df01b577b953821eda4579aa3cc431aa117c17308a8f033a39eae32` | (same) |
| 153 | 14.7 | MNIST T1 zeros per class (d) | PASS | `[0, 1, 1, 0, 0, 0, 0, 0, 0, 0]` | (same) |
| 154 | 14.7 | MNIST T1 max/A/ (d) | PASS | `6742` | (same) |
| 155 | 14.7 | MNIST T1 A[0][0:8], P[0] first8 (d) | PASS | `([-4325, 3499, -5923, -5923, 5923, 4949, -3441, -3931], '4cc82f061d5236c7')` | (same) |
| 156 | 14.7 | MNIST T1 A[1][0:8], P[1] first8 (d) | PASS | `([-6580, 5954, -6742, -6742, 6742, 6552, -3234, -1210], '4ce90e0f1f5236d7')` | (same) |
| 157 | 14.9 | ids sha256 (u64be) | PASS | `fba1c601bfefac706d3b860de5d6ac1fc10306ab02478eaae6a8db48653478e8` | (same) |
| 158 | 14.9 | ids distinct | PASS | `True` | (same) |
| 159 | 14.9 | smallest id episode / value | PASS | `(50981, '0001625fabf98577')` | (same) |
| 160 | 14.9 | rank[0:5] | PASS | `[40204, 6826, 51267, 54572, 22565]` | (same) |
| 161 | 14.9 | train ex0 LOO top-8 positions | PASS | `[32248, 18932, 30483, 26251, 21654, 31008, 52295, 46358]` | (same) |
| 162 | 14.9 | train ex0 LOO top-8 distances | PASS | `[934, 942, 951, 973, 989, 993, 998, 999]` | (same) |
| 163 | 14.9 | ex3493 label | PASS | `8` | (same) |
| 164 | 14.9 | ex3493 LOO top-8 positions | PASS | `[26720, 27579, 59277, 22703, 59015, 3499, 295, 58302]` | (same) |
| 165 | 14.9 | ex3493 LOO top-8 distances | PASS | `[735, 738, 759, 762, 803, 807, 809, 818]` | (same) |
| 166 | 14.9 | ex3493 32nd neighbour distance | PASS | `908` | (same) |
| 167 | 14.9 | ex3493 all 32 neighbours class 8 | PASS | `True` | (same) |
| 168 | impl | LOO retrieval == brute force popcount/sort (5 queries) | PASS | `True` | (same) |
| 169 | 14.9 | first T2 step example | PASS | `3493` | (same) |
| 170 | 14.9 | first step prototype sims | PASS | `[0.757, 0.8068, 0.8034, 0.7942, 0.7772, 0.7908, 0.7944, 0.7666, 0.8178, 0.781]` | (same) |
| 171 | 14.9 | first step sims exact repr | PASS | `['0.757', '0.8068', '0.8034', '0.7942', '0.7772', '0.7908', '0.7944', '0.7666', '0.8178...` | (same) |
| 172 | 14.9 | first step fused == sims for c != 8 | PASS | `True` | (same) |
| 173 | 14.9 | first step class-8 fused score repr | PASS | `5.856550000000001` | (same) |
| 174 | 14.9 | first step prediction | PASS | `8` | (same) |
| 175 | 14.9 | first step: all 32 neighbours util +1 | PASS | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,...` | (same) |
| 176 | 14.9 | after 1000 steps: misses | PASS | `48` | (same) |
| 177 | 14.9 | after 1000 steps: util sha256 | PASS | `be1fbcbf700aece0b4bd5de3872af95cdc61a698d70b03a6083460a05490e634` | (same) |
| 178 | 14.9 | after 1000 steps: util nonzero/min/max | PASS | `(22229, -3, 7)` | (same) |
| 179 | 14.9 | after 1000 steps: A sha256 | PASS | `3e2945a9642d97ca80600abccb09ab6d7e7fe166640d75122aac080713031713` | (same) |
| 180 | 14.9 | after 1000 steps: P sha256 | PASS | `d09d5b392ee3125771d0eaf59b39309a9fdb9a6339ed4578c5198c88932cfe58` | (same) |
| 181 | 14.9 | (d) T2 misses per epoch (recorded run) | PASS | `[3215, 3110]` | (same) |
| 182 | 14.9 | (d) t2_error_per_epoch (recorded run) | PASS | `[0.053583, 0.051833]` | (same) |
| 183 | 14.9 | test0 top-8 positions | PASS | `[53843, 27059, 47003, 38620, 14563, 16186, 44566, 15260]` | (same) |
| 184 | 14.9 | test0 top-8 distances | PASS | `[575, 638, 670, 673, 679, 681, 692, 694]` | (same) |
| 185 | 14.9 | test0 32nd neighbour distance | PASS | `749` | (same) |

Total checks: 185; pass 185; fail 0

## Where the spec was ambiguous, incomplete or wrong, and what I assumed

I found nothing wrong in the spec: every value it states that I could check matched. Nothing it leaves out affects predictions. The points below are the places where I had to assume something, or where the spec cannot be checked from what a reproducer is given.

1. **The (d) configuration exists only as a transcription (§0.2).**
   * The run reads `results/tuning/mnist_seed42.json`, which the isolation rules do not let me open.
   * I used the spec's transcribed values: k=32, θ0=0.2, λe=0.25, λp=1.0 (not read from the file), util_clip=8 (not read from the file), t2_local=false, 2 T2 epochs, encoder options `{}`.
   * The `test_split_used == false` abort guard cannot be exercised by a reproducer.
   * The §14.9 checks all matched: the class-8 fused score `5.856550000000001`, the state after 1,000 steps, and the 3,215 / 3,110 misses. Together they corroborate the transcription.
2. **§8.2: the content of a registered class's P row before its first binarisation is not specified.** I zero-filled it. It has no effect, because every class occurs in training in all four runs.
3. **§1.5 and §13, record-only fields, are underspecified.**
   * `artifacts_digest` depends on a trigram vocabulary with document frequencies, and on a per-pixel mean and standard deviation. The spec does not give their exact definitions or the digest format.
   * I did not reproduce `artifacts_digest`. A comparison of full schema-4 records, not just predictions and metrics, could not be done from the spec alone.
4. **§13 `accuracy_excluding_train_duplicates`: "text does not occur in the full training split".**
   * I assumed exact byte or string equality of the test line with any of the 117,500 full training lines, not just the 2,350 shots.
   * This is informative only. Under this reading `test_items_in_train` = 3147, which matches §1.3.
5. **§14.9 prints the first-step prototype sims in a rounded-looking form** (`0.757, 0.8068, …`). The spec does not say whether these are exact values. I checked them as exact Python `repr`s, and they are.
6. **§11.4 writes the utility weight with a literal `8.0` but defines it as `1 + u/util_clip`.** I used `float(util_clip)`. The two are identical for these runs.
7. **Provenance caveats in §15 (items 7 and 8) are now resolved.** My fresh computation reproduces:
   * the all-60k MNIST encoding digest, which the spec took from a cache;
   * the (d) T2 miss counts (3,215 / 3,110), which the spec took from a recorded run at another commit.
8. **Limits of this reproduction (not spec defects).**
   * My runs used the same interpreter, NumPy 2.4.1 build, OpenBLAS and machine type as the reference values. So this tests whether the spec is complete; it does not test cross-platform or cross-version robustness.
   * The spec's residual risks on those points remain unprobed: NumPy Generator stream stability across versions, FMA or extended precision in the (d) fusion, and the macOS arm64 / Python 3.13 reference environment.
   * Accumulator halving (§8.4) never fires. I implemented it as written and only unit-tested it on synthetic values.
