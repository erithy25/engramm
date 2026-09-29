//! ENGRAMM runtime core, version 0.
//!
//! The Python package is the reference ("the factory"): it builds packs, trains the counted
//! models and answers. This crate holds the parts of the runtime that the desktop app needs
//! in native code, each conformant with the Python reference:
//!
//! * [`pack`]: knowledge-pack manifests, verification of every file by size and SHA-256,
//!   and the plan of what a download still has to fetch;
//! * [`choose`]: the deterministic reply variant (SHAKE-256, no immediate repeats), as in
//!   `engramm/chat/bank.py::choose`;
//! * [`normalise`]: the message normalisation the conversation router matches against, as in
//!   `engramm/chat/bank.py::normalise`;
//! * [`fetch`] (feature `fetch`): downloading a pack with resume, pinned manifest and checks.

pub mod choose;
#[cfg(feature = "fetch")]
pub mod fetch;
pub mod normalise;
pub mod pack;

pub use choose::choose;
pub use normalise::normalise;
