"""Normalização lexical e métricas puras, com guarda explícita de vazios."""

import unicodedata


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join("".join(c if c.isalnum() else " " for c in plain).split()) or None


def levenshtein_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return 1 - previous[-1] / max(len(left), len(right))


def jaro_winkler_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    radius = max(max(len(left), len(right)) // 2 - 1, 0)
    a_matches, b_matches = set(), set()
    for i, char in enumerate(left):
        for j in range(max(0, i - radius), min(i + radius + 1, len(right))):
            if j not in b_matches and char == right[j]:
                a_matches.add(i)
                b_matches.add(j)
                break
    count = len(a_matches)
    if not count:
        return 0.0
    a = [left[i] for i in sorted(a_matches)]
    b = [right[j] for j in sorted(b_matches)]
    transpositions = sum(x != y for x, y in zip(a, b)) / 2
    score = (count / len(left) + count / len(right) + (count - transpositions) / count) / 3
    prefix = 0
    for x, y in zip(left[:4], right[:4]):
        if x != y:
            break
        prefix += 1
    return score + prefix * 0.1 * (1 - score) if score > 0.7 else score


def token_similarity(left: str, right: str) -> float:
    a, b = set(left.split()), set(right.split())
    return len(a & b) / len(a | b) if a and b else 0.0


def text_similarity(left: str, right: str, metric: str) -> float:
    return {
        "LEVENSHTEIN_NORM": levenshtein_similarity,
        "JARO_WINKLER": jaro_winkler_similarity,
        "TOKEN_HYBRID": token_similarity,
    }[metric](left, right)


def acronym_identity(value: str | None, table: dict[str, str]) -> str | None:
    normalized = normalize_text(value)
    mapping = {normalize_text(k): normalize_text(v) for k, v in table.items()}
    return mapping.get(normalized, normalized)


_ROLES = {
    "ouvinte": "OUVINTE",
    "palestrante": "PALESTRANTE",
    "conferencista": "PALESTRANTE",
    "apresentador": "APRESENTADOR",
    "apresentacao de trabalho": "APRESENTADOR",
    "organizador": "ORGANIZADOR",
    "comissao organizadora": "ORGANIZADOR",
    "participante": "PARTICIPANTE",
    "congressista": "PARTICIPANTE",
}


def normalize_role(raw: str | None) -> str | None:
    return _ROLES.get(normalize_text(raw))
