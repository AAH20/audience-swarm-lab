"""Small, source-aware lexical retrieval baseline; GraphRAG is an adapter target."""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN = re.compile(r"[\w]+", re.UNICODE)


def _terms(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def retrieve(question: str, documents: list[dict], limit: int = 3) -> list[dict]:
    """Return BM25-ranked document excerpts with source and license.

    This is a transparent local control arm, not an LLM or a GraphRAG index.
    """
    if not documents:
        return []
    query = set(_terms(question))
    if not query:
        return []
    counts = [Counter(_terms(d["text"])) for d in documents]
    lengths = [sum(c.values()) for c in counts]
    average = sum(lengths) / len(lengths) or 1
    scored = []
    for doc, terms, length in zip(documents, counts, lengths):
        score = 0.0
        for term in query:
            frequency = terms[term]
            if not frequency:
                continue
            document_frequency = sum(1 for other in counts if other[term])
            inverse_frequency = math.log(1 + (len(documents) - document_frequency + 0.5) / (document_frequency + 0.5))
            score += inverse_frequency * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / average))
        if score:
            scored.append({"document_id": doc["id"], "source": doc["source"], "license": doc["license"], "score": round(score, 6), "excerpt": doc["text"][:500]})
    return sorted(scored, key=lambda item: (-item["score"], item["document_id"]))[:limit]
