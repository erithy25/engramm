"""ENGRAMM's language foundations (Chat v3, phase 2) — averaged perceptrons, no neural network.

* ``pos``    — part-of-speech tagger (Universal Dependencies UPOS), greedy left to right;
* ``parse``  — dependency parser, arc-hybrid transitions with a dynamic oracle;
* ``intent`` — assistant-command intents (MASSIVE, 60 intents), bag of word and letter n-grams.

All three learn by counting corrections (the averaged perceptron): weights are sums of +1/−1
updates, averaged over time. Training is deterministic (fixed order from SHAKE-256 of the
example ids), models are JSON files.
"""
