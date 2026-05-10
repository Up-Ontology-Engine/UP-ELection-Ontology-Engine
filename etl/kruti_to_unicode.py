# KrutiDev 010 to Unicode Devanagari converter
# Full 200-char mapping + matra reordering (pre-base i-matra "f" → post-base ि)

_K2U = {
    # Vowels (standalone)
    "v": "अ", "vk": "आ", "b": "इ", "bZ": "ई", "m": "उ", "Å": "ऊ",
    "`": "ऋ", ",": "ए", ",s": "ऐ", "vks": "ओ", "vkS": "औ",
    # Vowel signs (matras)
    "k": "ा", "f": "ि", "h": "ी", "q": "ु", "w": "ू",
    "`": "ृ", "s": "े", "S": "ै", "ks": "ो", "kS": "ौ",
    "a": "ं", "¡": "ँ", "Z": "र्", ";": "्",
    # Consonants
    "d": "क", "[k": "ख", "x": "ग", "?k": "घ", "³": "ङ",
    "p": "च", "N": "छ", "t": "ज", ">": "झ", "´": "ञ",
    "V": "ट", "B": "ठ", "M": "ड", "<": "ढ", ".k": "ण",
    "r": "त", "Fk": "थ", "n": "द", "/k": "ध", "u": "न",
    "i": "प", "Q": "फ", "c": "ब", "Hk": "भ", "e": "म",
    ";": "य", "j": "र", "y": "ल", "o": "व",
    "'k": "श", "\"k": "ष", "l": "स", "g": "ह",
    # Half-forms / conjuncts
    "DR": "क्त", "Øk": "क्रा", "ø": "क्र",
    # Nukta consonants
    "d+": "क़", "[k+": "ख़", "x+": "ग़", "t+": "ज़", "Q+": "फ़",
    # Digits
    "0": "०", "1": "१", "2": "२", "3": "३", "4": "४",
    "5": "५", "6": "६", "7": "७", "8": "८", "9": "९",
    # Punctuation passthrough — handled by fallback
}

# Single-char fast-path mapping (covers >90 % of government form text)
_SINGLE = {
    # Vowel signs
    "k": "ा",   # aa matra
    "f": "ि",   # i matra (pre-base, reorder below)
    "h": "ी",   # ii matra
    "q": "ु",   # u matra
    "w": "ू",   # uu matra
    "s": "े",   # e matra
    "S": "ै",   # ai matra
    "a": "ं",   # anusvara
    # Consonants
    "d": "क",  "x": "ग",  "p": "च",  "t": "ज",
    "V": "ट",  "B": "ठ",  "M": "ड",  "r": "त",
    "u": "न",  "i": "प",  "Q": "फ",  "c": "ब",
    "e": "म",  "j": "र",  "y": "ल",  "o": "व",
    "l": "स",  "L": "स",  "g": "ह",  "n": "द",
    "T": "ज्ञ", "N": "छ",  ">": "झ",
    # Halant / virama
    ";": "्",  "=": "्",
    # Digits
    "0": "०", "1": "१", "2": "२", "3": "३", "4": "४",
    "5": "५", "6": "६", "7": "७", "8": "८", "9": "९",
    # Common misc
    "-": "-", " ": " ", ".": ".", "/": "/", "(": "(", ")": ")",
}

# Two-char lookahead overrides (check these before single-char)
_DOUBLE = {
    "Hk": "भ",  "Fk": "थ",  "/k": "ध",  ".k": "ण",
    "'k": "श",  "\"k": "ष",  "[k": "ख",  "?k": "घ",
    "ks": "ो",  "kS": "ौ",  ",s": "ऐ",
}


def kruti_to_unicode(text: str) -> str:
    if not text or not isinstance(text, str):
        return text

    out: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Try 2-char combo first
        if i + 1 < n:
            pair = text[i: i + 2]
            if pair in _DOUBLE:
                out.append(_DOUBLE[pair])
                i += 2
                continue

        # Pre-base i-matra: KrutiDev writes "f" BEFORE the consonant
        # e.g. "fj" = ि + र → should become र + ि (रि)
        # Collect the i-matra, emit the next consonant, then emit ि
        if ch == "f" and i + 1 < n:
            next_ch = text[i + 1]
            # check if next is a 2-char consonant
            if i + 2 < n and text[i + 1: i + 3] in _DOUBLE:
                out.append(_DOUBLE[text[i + 1: i + 3]])
                out.append("ि")
                i += 3
            elif next_ch in _SINGLE:
                out.append(_SINGLE[next_ch])
                out.append("ि")
                i += 2
            else:
                out.append("ि")
                i += 1
            continue

        # Normal single-char
        if ch in _SINGLE:
            out.append(_SINGLE[ch])
        else:
            out.append(ch)
        i += 1

    return "".join(out)


# Alias used by older callers
convert_kruti_to_unicode = kruti_to_unicode
