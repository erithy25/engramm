    # Fakt-Extraktion: (Schluessel, Wert) — Schluessel steuert den Abruf.
    FACT_PATTERNS = [
        (re.compile(r"\bmy ([\w ]{2,30}?) (?:is|are|is called|is named) ([\w .'&-]{1,40})", re.I), "en"),
        (re.compile(r"\bi (?:work at|work for) ([\w .'&-]{2,40})", re.I), "work"),
        (re.compile(r"\bi live in ([\w .'-]{2,40})", re.I), "live"),
        (re.compile(r"\bi (?:like|love|prefer) ([\w .'-]{2,40})", re.I), "like"),
        (re.compile(r"\bich arbeite bei ([\w .'&-]{2,40})", re.I), "work"),
        (re.compile(r"\bich wohne (?:in|zwischen) ([\w äöü.'&-]+?)(?:\s+und\s+bin\b|\s+und\s+\d|\s+bin\b|[.!?]|$)", re.I), "live"),
        (re.compile(r"\bich (?:mag|liebe) ([\w .'-]{2,40})", re.I), "like"),
        (re.compile(r"\bich (?:heiße|bin) ([\w .'-]{2,40})", re.I), "name"),
        (re.compile(r"\bmy name is ([\w .'-]{2,40})", re.I), "name"),
        (re.compile(r"\b(?:er|sie|es|he|she|it) (?:heißt|is called|is named) ([\w .'-]{1,40})", re.I), "en"),
        (re.compile(r"\bmein(?:e)? ([\w ]{2,30}?) (?:ist|heißt|sind) ([\w .'-]{1,40})", re.I), "de"),
    ]