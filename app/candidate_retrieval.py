"""Exploration documentaire large; aucun candidat n'est une preuve validée."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .db import get_documents
from .rag import canonical, key_terms, chunks


def retrieve_candidates(claim, limit=10):
    wanted = key_terms(claim)
    if len(wanted) < 2:
        return []
    names = re.findall(r'\b[A-ZÀ-ÖØ-Ý][\wÀ-ÿ]*-[A-ZÀ-ÖØ-Ý][\wÀ-ÿ]*\b', claim)
    rows = []
    for doc in get_documents():
        content = doc.get('content') or ''
        if len(content) < 50:
            continue
        combined = canonical((doc.get('title') or '') + ' ' + content)
        if any(canonical(name) not in combined for name in names):
            continue
        doc_chunks = chunks(content, size=1150, stride=800)
        for passage in doc_chunks:
            terms = key_terms((doc.get('title') or '') + ' ' + passage)
            overlap = len(terms & wanted)
            # Minimum topical overlap; permit semantic substitutions later in Gemini.
            if overlap < 2:
                continue
            rows.append((doc, passage))
    if not rows:
        return []
    corpus = [canonical(claim)] + [canonical(d['title'] + ' ' + p) for d, p in rows]
    try:
        word = TfidfVectorizer(ngram_range=(1, 2), max_features=18000, sublinear_tf=True)
        char = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=18000)
        a = word.fit_transform(corpus)
        b = char.fit_transform(corpus)
        scores = .70*cosine_similarity(a[:1], a[1:]).ravel() + .30*cosine_similarity(b[:1], b[1:]).ravel()
    except ValueError:
        return []
    candidates = []
    seen = set()
    for ix in scores.argsort()[::-1]:
        doc, passage = rows[int(ix)]
        score = float(scores[ix])
        if doc['url'] in seen or score < 0.055:
            continue
        seen.add(doc['url'])
        candidates.append({
            'document_id': doc['id'], 'title': doc['title'],
            'source_name': doc.get('source_name') or 'Source non classée',
            'url': doc['url'], 'published_at': doc.get('published_at'),
            'retrieved_at': doc.get('fetched_at'), 'passage': passage,
            'relevance': round(score, 3), 'trusted': bool(doc.get('trusted')),
        })
        if len(candidates) >= limit:
            break
    return candidates
