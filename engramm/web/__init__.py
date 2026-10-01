"""ENGRAMM Atlas: private web knowledge without a neural network and without servers
(docs/SPEC_ATLAS.md). Three channels, each off until the user switches it on:

* ``shelf``     — fixed-size buckets of open texts (Wikipedia …) from static release files;
* ``feeds``     — RSS/Atom feeds fetched on a schedule, independent of questions;
* ``messenger`` — a page the local wayfinder chose, fetched over Tor.

All traffic goes through ``egress.Egress``; nothing in this package ever sends a question.
"""
