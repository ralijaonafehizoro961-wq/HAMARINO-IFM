import re
import unicodedata

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .db import get_documents

STOP = {
    "le", "la", "les", "un", "une", "des", "de", "du",
    "au", "aux", "en", "et", "est", "sont", "pour",
    "par", "sur", "dans", "que", "qui", "son", "sa",
    "ses", "avec", "plus", "moins", "ce", "cette",
    "ces", "pas", "se", "ne", "il", "elle", "ont",
    "ete", "etre", "a", "avait", "affirme",
    "information", "annonce", "selon"
}


def normalize(text):
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def canonical(text):
    value = normalize(text)

    rules = [
        (
            r"\bpresident de l assemblee nationale\b",
            "presidentassemblee",
        ),
        (
            r"\b(?:president de la republique|"
            r"president de madagascar|chef de l etat)\b",
            "presidentetat",
        ),
        (
            r"\b(?:s est rendu|s est rendue|"
            r"est alle|est allee|s est deplace|"
            r"a effectue un deplacement|"
            r"deplacement|voyage)\b",
            "voyage",
        ),
        (
            r"\b(?:moscou)\b",
            "russie",
        ),
        (
            r"\b(?:cooperations|cooperation)\b",
            "cooperation",
        ),
    ]

    for pattern, replacement in rules:
        value = re.sub(pattern, replacement, value)

    return value


def key_terms(text):
    return {
        word
        for word in canonical(text).split()
        if len(word) >= 3 and word not in STOP
    }


def chunks(text, size=900, stride=600):
    clean = re.sub(r"\s+", " ", str(text)).strip()
    if not clean:
        return []

    output = []
    for position in range(0, len(clean), stride):
        output.append(clean[position:position + size])
        if position + size >= len(clean):
            break

    return output


def fact_gate(claim, article):
    claim_normal = normalize(claim)
    article_normal = normalize(article)

    if not claim_normal or not article_normal:
        return False

    special_names = re.findall(
        r"\b[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+-"
        r"[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+\b",
        claim,
    )

    for name in special_names:
        if normalize(name) not in article_normal:
            return False

    wanted = key_terms(claim)
    found = key_terms(article)

    if len(wanted) < 2:
        return False

    shared = wanted & found

    if len(shared) < 2:
        return False

    if len(shared) / len(wanted) < 0.40:
        return False

    if "presidentetat" in wanted:
        if "presidentetat" not in found:
            return False

    if "voyage" in wanted and "russie" in wanted:
        if not {"voyage", "russie"}.issubset(found):
            return False

    return True


def retrieve(claim: str, limit=5):
    docs = get_documents()
    passage_rows = []

    for doc in docs:
        if not doc.get("content"):
            continue

        for passage in chunks(doc["content"]):
            if len(passage) >= 50:
                passage_rows.append((doc, passage))

    if not passage_rows or not key_terms(claim):
        return []

    corpus = [canonical(claim)]

    for doc, passage in passage_rows:
        corpus.append(
            canonical(doc["title"] + " " + passage)
        )

    try:
        word = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=15000,
            sublinear_tf=True,
        )
        char = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=20000,
            sublinear_tf=True,
        )

        x = word.fit_transform(corpus)
        y = char.fit_transform(corpus)

        scores = (
            0.7 * cosine_similarity(x[:1], x[1:]).ravel()
            + 0.3 * cosine_similarity(y[:1], y[1:]).ravel()
        )

    except ValueError:
        return []

    selected = []
    seen = set()

    for index in scores.argsort()[::-1]:
        score = float(scores[index])
        doc, passage = passage_rows[int(index)]

        if doc["url"] in seen:
            continue

        if score < 0.08:
            continue

        if not fact_gate(
            claim,
            doc["title"] + " " + passage,
        ):
            continue

        seen.add(doc["url"])

        selected.append({
            "document_id": doc["id"],
            "title": doc["title"],
            "source_name": doc["source_name"] or "Source non classée",
            "url": doc["url"],
            "published_at": doc["published_at"],
            "retrieved_at": doc["fetched_at"],
            "passage": passage,
            "relevance": round(score, 3),
            "trusted": bool(doc["trusted"]),
        })

        if len(selected) >= limit:
            break

    return selected
