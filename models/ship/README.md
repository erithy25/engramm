# Models shipped in every knowledge pack

Small counted models the chat needs, kept in git so CI can build packs from scratch
(`.github/workflows/release.yml`). None is a neural network.

| File | What | Built by |
|---|---|---|
| `codebook.npz` | HDC word classes and meaning vectors of the tokenizer | ENGRAMM-LM main run (`models/lm/main/model`) |
| `spanperc_ens7.json`, `spanperc_nq.json` | answer-span perceptrons (questions, search-box queries) | `experiments/chat_v2_perceptron` (Chat v14) |
| `confperc14.json` | answer confidence calibrator | Chat v13/v14 |
| `capstats.json` | capitalisation statistics | Chat v9 |
| `intent.json` | MASSIVE intent classifier (device requests) | `experiments/nlp_train --test` (E29) |
