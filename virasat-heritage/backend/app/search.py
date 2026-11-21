"""Search over heritage records, notes and OCR'd documents.

Hybrid ranking: word-level TF-IDF + character n-gram TF-IDF (robust to spelling variants such as
baoli/baori/vav and to Indic scripts) + domain synonym expansion. The `Embedder` hook lets a
sentence-embedding model (e.g. multilingual-e5, stored in pgvector) be blended in without changing callers.
"""
import unicodedata

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SYNONYMS = {
    "stepwell": "baoli baori bawdi vav vaav step well water tank kund",
    "water": "stepwell baoli baori vav well tank kund pond",
    "temple": "mandir shrine sanctum shikhara deity",
    "fort": "fortress citadel bastion rampart palace garh qila kila",
    "palace": "mahal fort royal wadiyar dome",
    "craft": "handicraft artisan rogan painting textile block printing",
    "folklore": "folk legend ballad story tale bard oral",
    "ancient": "medieval historic old solanki chandela vijayanagara",
    "carving": "carved sculpture sculptures jali pillar relief",
    "cave": "rock-cut rockcut murals buddhist",
    "sun": "surya konark modhera",
    "वाव": "बावड़ी बावली stepwell",
    "બાવડી": "વાવ stepwell",
    "mandir": "temple", "baoli": "stepwell", "baori": "stepwell", "vav": "stepwell",
}


def tokens(text):
    """Unicode-aware tokenizer: keeps letters, combining marks (Indic vowel signs) and digits."""
    out, cur = [], []
    for ch in text.lower():
        if unicodedata.category(ch)[0] in "LMN":
            cur.append(ch)
        elif cur:
            out.append("".join(cur)); cur = []
    if cur:
        out.append("".join(cur))
    return out


def expand(query):
    toks = tokens(query)
    extra = []
    for t in toks:
        extra += SYNONYMS.get(t, "").split()
    return toks, extra


class Embedder:
    """Optional dense retrieval. Subclass and return a numpy matrix from `encode`."""
    def encode(self, texts):  # pragma: no cover - plug-in point
        raise NotImplementedError


class SearchIndex:
    def __init__(self, embedder=None):
        self.embedder = embedder
        self.ids, self.cats = [], []
        self._w = self._c = None

    def build(self, corpus):
        """corpus: list of (id, category, text)."""
        self.ids = [c[0] for c in corpus]
        self.cats = [c[1] for c in corpus]
        texts = [c[2] for c in corpus]
        self._w = TfidfVectorizer(tokenizer=tokens, token_pattern=None, lowercase=False, sublinear_tf=True)
        self._c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
        self.Xw = self._w.fit_transform(texts)
        self.Xc = self._c.fit_transform(texts)
        self.Xe = self.embedder.encode(texts) if self.embedder else None
        return self

    def query(self, q, k=10, category=None):
        if not q or not q.strip() or self._w is None:
            return []
        toks, extra = expand(q)
        qw = self._w.transform([" ".join(toks + toks + extra)])      # original words weigh double
        qc = self._c.transform([q])
        score = 0.65 * cosine_similarity(qw, self.Xw)[0] + 0.35 * cosine_similarity(qc, self.Xc)[0]
        if self.Xe is not None:
            score = 0.6 * score + 0.4 * cosine_similarity(self.embedder.encode([q]), self.Xe)[0]
        ranked = sorted(zip(self.ids, self.cats, score), key=lambda x: -x[2])
        return [{"id": i, "score": round(float(s), 4)} for i, c, s in ranked
                if s > 0.05 and (not category or category == "All" or c == category)][:k]
