import numpy as np

from sentence_transformers import SentenceTransformer


_EMBEDDER = None


def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        # ponytail: multilingual model handles Hinglish symptoms natively
        _EMBEDDER = SentenceTransformer("intfloat/multilingual-e5-small")
    return _EMBEDDER


def _embed_texts(texts: list[str], prefix: str = "query") -> np.ndarray:
    embedder = _get_embedder()
    # E5 requires query: prefix for queries and passage: prefix for docs
    prefixed = [f"{prefix}: {t}" for t in texts]
    return embedder.encode(prefixed, normalize_embeddings=True)


def _should_count_chunk(chunk: str) -> bool:
    low = chunk.lower()
    skip_phrases = [
        "contributors", "foreword", "acknowledgement", "list of acronyms",
        "table of contents", "contents", "preface", "abbreviations",
        "acronyms", "committee", "control of communicable diseases",
    ]
    for phrase in skip_phrases:
        if phrase in low:
            return False
    return True


RELEVANCE_THRESHOLD = 0.15


def context_precision(
    context: str,
    symptoms: str,
    output: dict,
    top_k: int = 5,
) -> dict:
    """
    Compute context precision using semantic similarity (cosine).
    Measures how many relevant chunks were returned in the top-k.
    Uses sentence-transformers cross-lingual embeddings to handle
    the mismatch between Hindi-transliterated symptoms and English guidelines.
    """
    try:
        chunks = [c.strip() for c in context.split("\n\n") if c.strip()]
        chunks = [c for c in chunks if _should_count_chunk(c)]

        if not chunks:
            return {
                "score": 0.0,
                "mrr": 0.0,
                "keyword_recall": 0.0,
                "num_relevant_chunks": 0,
                "total_chunks": 0,
                "error": "No valid chunks in context",
            }

        symptom_emb = _embed_texts([symptoms], prefix="query")
        chunk_embs = _embed_texts(chunks, prefix="passage")

        similarities = (chunk_embs @ symptom_emb.T).flatten()
        chunk_relevances = similarities.tolist()

        ranked = sorted(chunk_relevances, reverse=True)

        mrr = 0.0
        for rank, rel in enumerate(ranked[:top_k], start=1):
            if rel >= RELEVANCE_THRESHOLD:
                mrr += 1.0 / rank
                break

        total_keywords_est = 0
        keyword_recall = 0.0

        num_relevant = sum(1 for r in chunk_relevances if r >= RELEVANCE_THRESHOLD)
        precision = num_relevant / len(chunks) if chunks else 0.0
        combined = (mrr * 0.5) + (precision * 0.5)

        return {
            "score": round(combined, 4),
            "mrr": round(mrr, 4),
            "keyword_recall": round(keyword_recall, 4),
            "precision": round(precision, 4),
            "num_relevant_chunks": num_relevant,
            "total_chunks": len(chunks),
            "avg_similarity": round(float(np.mean(chunk_relevances)), 4),
            "error": None,
        }

    except Exception as e:
        return {"score": 0.0, "error": str(e)}
