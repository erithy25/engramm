//! Message normalisation, identical to `engramm/chat/bank.py::normalise`: lower case, straight
//! apostrophes, no form of address, no end punctuation, chat spelling expanded and (optionally)
//! no leading fillers such as "well, so, ok, please".

use regex::Regex;
use std::collections::HashMap;
use std::sync::OnceLock;

struct Rules {
    address: Regex,
    spaces: Regex,
    end: Regex,
    filler: Regex,
    slang: HashMap<&'static str, &'static str>,
}

const SLANG: &[(&str, &str)] = &[
    ("u", "you"), ("r", "are"), ("ur", "your"), ("pls", "please"), ("plz", "please"), ("thx", "thanks"),
    ("im", "i'm"), ("ive", "i've"), ("youre", "you're"), ("dont", "don't"), ("cant", "can't"), ("wont", "won't"),
    ("didnt", "didn't"), ("doesnt", "doesn't"), ("isnt", "isn't"), ("wasnt", "wasn't"), ("whats", "what's"),
    ("hows", "how's"), ("wheres", "where's"), ("whos", "who's"), ("thats", "that's"), ("theres", "there's"),
    ("lets", "let's"), ("gonna", "going to"), ("wanna", "want to"), ("gotta", "got to"), ("idk", "i don't know"),
    ("rn", "right now"), ("abt", "about"), ("cuz", "because"), ("coz", "because"), ("tho", "though"),
    ("fav", "favourite"), ("fave", "favourite"), ("favorite", "favourite"), ("color", "colour"), ("colors", "colours"),
    ("b4", "before"), ("2day", "today"), ("gr8", "great"), ("ok.", "ok"), ("k.", "k"),
];

fn rules() -> &'static Rules {
    static RULES: OnceLock<Rules> = OnceLock::new();
    RULES.get_or_init(|| Rules {
        address: Regex::new(r"(?i)(^|[\s,])(engramm|bot|buddy)([\s,!.?]|$)").expect("address pattern"),
        spaces: Regex::new(r"\s+").expect("space pattern"),
        end: Regex::new(r"[\s.!?…,;:]+$").expect("end pattern"),
        // Python adds the lookahead (?=\S); the input never ends in white space at this point,
        // so a match that ends in \s+ is always followed by a non-space character.
        filler: Regex::new(
            r"^(?:(?:um+|uh+|er+|erm|well|so|oh|ah|hmm+|hey|ok|okay|alright|and|but|also|now|then|please|pls|plz)\s*[,.!]?\s+)+",
        )
        .expect("filler pattern"),
        slang: SLANG.iter().copied().collect(),
    })
}

/// Python's `str.strip(chars)` for a set of ASCII characters.
fn strip_chars<'a>(s: &'a str, chars: &[char]) -> &'a str {
    s.trim_matches(|c| chars.contains(&c))
}

/// Python's `str.strip()` without arguments (Unicode white space as Python defines it).
fn py_strip(s: &str) -> &str {
    s.trim_matches(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
}

fn straight_quotes(text: &str) -> String {
    text.chars()
        .map(|c| match c {
            '\u{2019}' | '\u{2018}' | '`' | '\u{b4}' => '\'',
            '\u{201c}' | '\u{201d}' => '"',
            other => other,
        })
        .collect()
}

/// The normalised form of a message (see the module documentation).
pub fn normalise(text: &str, fillers: bool) -> String {
    let r = rules();
    let straight = straight_quotes(text);
    let mut s = py_strip(&straight).to_lowercase();
    s = r.address.replace_all(&s, " ").into_owned();
    s = r.spaces.replace_all(&s, " ").into_owned();
    s = strip_chars(&s, &[' ', ',']).to_string();
    s = r.end.replace(&s, "").into_owned();
    let words: Vec<&str> = s.split(' ').map(|w| r.slang.get(w).copied().unwrap_or(w)).collect();
    let n_words = words.len();
    s = words.join(" ");
    if fillers && n_words > 1 {
        s = r.filler.replace(&s, "").into_owned();
    }
    strip_chars(&s, &[' ', ',']).to_string()
}

#[cfg(test)]
mod tests {
    use super::normalise;

    #[test]
    fn examples() {
        assert_eq!(normalise("Hey ENGRAMM, how r u?", true), "how are you");
        assert_eq!(normalise("  Well, so what’s up!!! ", true), "what's up");
        assert_eq!(normalise("ok", true), "ok");
        assert_eq!(normalise("ok thanks", false), "ok thanks");
        assert_eq!(normalise("ok thanks", true), "thanks");
        assert_eq!(normalise("idk tbh", true), "i don't know tbh");
        assert_eq!(normalise("", true), "");
    }
}
