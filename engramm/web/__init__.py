"""ENGRAMM Atlas: web knowledge without a neural network and without servers of our own
(docs/SPEC_ATLAS.md). Three channels, each off until the user switches it on:

* ``shelf``  — fixed-size buckets of open texts (Wikipedia …) from static release files;
* ``feeds``  — RSS/Atom feeds fetched on a schedule, independent of questions;
* ``search`` — a web search: the question goes to a search engine, the best result pages are
  read here. "google …" searches once even with the channel off (the user asked for it).

All traffic goes through ``egress.Egress`` and shows up in the network log.
"""
