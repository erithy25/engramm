//! Deterministic choice of a reply variant, identical to `engramm/chat/bank.py::choose`.

use sha3::digest::{ExtendableOutput, Update, XofReader};
use sha3::Shake256;

/// The first 8 bytes of SHAKE-256 over `key \0 salt \0 index`.
fn rank(key: &str, salt: &str, index: usize) -> [u8; 8] {
    let mut h = Shake256::default();
    h.update(key.as_bytes());
    h.update(b"\x00");
    h.update(salt.as_bytes());
    h.update(b"\x00");
    h.update(index.to_string().as_bytes());
    let mut out = [0u8; 8];
    h.finalize_xof().read(&mut out);
    out
}

/// The order in which the variants are tried for this key (a stable sort by the 8-byte hash).
pub fn order(n: usize, key: &str, salt: &str) -> Vec<usize> {
    let mut idx: Vec<(usize, [u8; 8])> = (0..n).map(|i| (i, rank(key, salt, i))).collect();
    idx.sort_by(|a, b| a.1.cmp(&b.1));
    idx.into_iter().map(|(i, _)| i).collect()
}

/// The variant for `key`: the first one in SHAKE-256 order that is not among `recent`;
/// if every variant was used recently, the first in that order. Empty input gives "".
pub fn choose<'a>(options: &'a [String], key: &str, recent: &[String], salt: &str) -> &'a str {
    match options.len() {
        0 => "",
        1 => options[0].as_str(),
        n => {
            let ord = order(n, key, salt);
            for &i in &ord {
                if !recent.iter().any(|r| r == &options[i]) {
                    return options[i].as_str();
                }
            }
            options[ord[0]].as_str()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn opts(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn empty_and_single() {
        assert_eq!(choose(&[], "k", &[], ""), "");
        assert_eq!(choose(&opts(&["only"]), "k", &opts(&["only"]), ""), "only");
    }

    #[test]
    fn deterministic_and_skips_recent() {
        let o = opts(&["a", "b", "c", "d"]);
        let first = choose(&o, "conv|greet|0", &[], "");
        assert_eq!(first, choose(&o, "conv|greet|0", &[], ""));
        let second = choose(&o, "conv|greet|0", &[first.to_string()], "");
        assert_ne!(first, second);
        let all = opts(&["a", "b", "c", "d"]);
        assert_eq!(choose(&o, "conv|greet|0", &all, ""), first);
    }

    #[test]
    fn order_is_a_permutation() {
        let mut ord = order(7, "x", "y");
        ord.sort();
        assert_eq!(ord, (0..7).collect::<Vec<_>>());
    }
}
