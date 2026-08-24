"""Phase 4K — policy retrieval.

**Why TF-IDF instead of a neural embedding model or FAISS:** the design
doc's Section 17 called for FAISS with dense embeddings — that requires
either an external embedding API call (a new network/credential
dependency this project has otherwise avoided) or a local embedding
model (`sentence-transformers`, which pulls in `torch` — a large,
heavy dependency for a ~20-chunk corpus). `sklearn.feature_extraction.text.TfidfVectorizer`
is already a project dependency (Phase 2), fully deterministic, fully
offline, and — at this corpus size (4 documents, ~15 chunks) — retrieves
correctly for the kind of short, keyword-bearing queries an investigation
agent actually issues (see docs/RAG_POLICY.md for the retrieval-accuracy
test set). This is a deliberate minimal-dependency substitution, not an
oversight — documented explicitly rather than silently deviating from
the design doc.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.rag.corpus import PolicyChunkRecord, load_policy_corpus


@dataclass(frozen=True)
class RetrievalResult:
    doc_id: str
    section_id: str
    text: str
    score: float


class PolicyCorpus:
    def __init__(self, chunks: list[PolicyChunkRecord]) -> None:
        self.chunks = chunks
        self._vectorizer = TfidfVectorizer(stop_words="english")
        corpus_texts = [f"{c.title}. {c.text}" for c in chunks]
        self._matrix = self._vectorizer.fit_transform(corpus_texts) if corpus_texts else None

    @classmethod
    def from_directory(cls, policy_dir: Path) -> "PolicyCorpus":
        return cls(load_policy_corpus(policy_dir))

    def retrieve(
        self, query: str, applies_to_pattern: str | None = None, top_k: int = 3, min_score: float = 0.05
    ) -> list[RetrievalResult]:
        if self._matrix is None or not self.chunks:
            return []

        candidate_indices = list(range(len(self.chunks)))
        if applies_to_pattern is not None:
            filtered = [
                i for i in candidate_indices
                if self.chunks[i].applies_to_pattern in (applies_to_pattern, "general")
            ]
            if filtered:
                candidate_indices = filtered
            # if the filter matches nothing at all, fall back to the full corpus
            # rather than returning zero results for a query that has a real answer

        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix[candidate_indices])[0]

        scored = sorted(zip(candidate_indices, sims), key=lambda x: -x[1])
        results = [
            RetrievalResult(
                doc_id=self.chunks[i].doc_id, section_id=self.chunks[i].section_id,
                text=self.chunks[i].text, score=float(score),
            )
            for i, score in scored[:top_k]
            if score >= min_score
        ]
        return results
