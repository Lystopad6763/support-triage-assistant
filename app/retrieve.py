"""Find the chunks that answer a ticket: lexical, semantic, or both.

NO VECTOR STORE, ON PURPOSE
    A vector database sells approximate nearest neighbour - HNSW, IVF - which
    trades exactness for speed once scanning everything stops being possible.
    The larger index here is 131 vectors. Scanning all of them is one
    matrix-vector product, faster than building an approximate index would be,
    and exact, where the approximate answer could only ever lose a document
    that brute force would have found.

    The trade flips somewhere around a hundred thousand vectors. This is three
    orders of magnitude below it, so the whole index loads from a file and the
    search runs in-process.

BM25 READS THE SAME TEXT THAT WAS EMBEDDED
    scripts/build_kb.py embeds chunk["text"] - the title, the section heading
    and the body joined - so BM25 indexes that same string. Indexing the body
    alone would have made the two methods answer slightly different questions
    and their comparison meaningless.

WHY RRF AND NOT AN AVERAGE OF SCORES
    A BM25 score is unbounded and corpus-dependent; a cosine over normalised
    vectors lies in [-1, 1]. Averaging them lets BM25 decide the outcome by
    virtue of its scale alone. Reciprocal rank fusion uses only POSITION -
    1/(60 + rank), summed across the lists - so the scales never meet. The
    constant is the 60 of the original paper, and it damps the gap between
    first and second place so that one list cannot dictate the merge.

WHAT THIS MODULE DOES NOT DO
    It returns chunks, not documents. Rolling a section hit up to its article
    belongs to whatever is scoring, because the two chunkings have to be
    compared at document level and a retriever that silently deduplicated would
    hide the difference it is being measured on.
"""
from __future__ import annotations

import base64
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "data" / "kb"

# Robertson's defaults. They are not tuned here: tuning k1 and b on the same
# 430 queries the encoders are scored on would hand BM25 an advantage the
# encoders never got, and the comparison is the point of this module existing.
K1 = 1.5
B = 0.75
RRF_K = 60

# \w with re.UNICODE keeps Cyrillic, Greek and Arabic letters as word
# characters, which is what the non-English tickets need. It does NOT segment
# Chinese, Japanese or Thai, where words are not space-separated: those queries
# reach BM25 as one long token and it scores them near zero. Four tickets of
# 430 are affected, and the honest fix is a segmenter, not a regex - so the
# limitation is recorded and reported rather than papered over.
WORD = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class Hit:
    """One chunk that came back, with everything a citation needs."""

    chunk_id: str
    doc_id: str
    score: float
    rank: int
    title: str
    heading: str
    url: str
    url_is_page: bool
    text: str


def tokenise(text: str) -> list[str]:
    return WORD.findall(text.lower())


class Index:
    """One chunking of the knowledge base, with its BM25 statistics."""

    def __init__(self, variant: str, chunks: list[dict], fingerprint: str):
        self.variant = variant
        self.chunks = chunks
        self.fingerprint = fingerprint
        self.tokens = [tokenise(c["text"]) for c in chunks]
        self.lengths = np.array([len(t) for t in self.tokens], dtype=np.float32)
        self.avgdl = float(self.lengths.mean())
        self.freqs = [Counter(t) for t in self.tokens]
        df: Counter = Counter()
        for token_set in ({t for t in doc} for doc in self.tokens):
            df.update(token_set)
        n = len(chunks)
        self.idf = {
            term: math.log(1 + (n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

    @classmethod
    def load(cls, variant: str) -> "Index":
        data = json.loads((KB / "index.json").read_text(encoding="utf-8"))
        block = data["variants"][variant]
        return cls(variant, block["chunks"], block["fingerprint"])

    def bm25(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.chunks), dtype=np.float32)
        terms = tokenise(query)
        if not terms:
            return scores
        norm = K1 * (1 - B + B * self.lengths / self.avgdl)
        for term in set(terms):
            idf = self.idf.get(term)
            if idf is None:
                continue
            freq = np.array([f.get(term, 0) for f in self.freqs],
                            dtype=np.float32)
            scores += idf * (freq * (K1 + 1)) / (freq + norm)
        return scores


class Vectors:
    """The embeddings of one chunking under one encoder."""

    def __init__(self, model: str, variant: str, ids: list[str],
                 matrix: np.ndarray, fingerprint: str):
        self.model = model
        self.variant = variant
        self.ids = ids
        self.matrix = matrix
        self.fingerprint = fingerprint

    @classmethod
    def load(cls, variant: str, model: str, index: Index | None = None
             ) -> "Vectors":
        slug = model.replace("/", "-")
        path = KB / f"vectors__{variant}__{slug}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = base64.b64decode(data["vectors_b64"])
        matrix = np.frombuffer(raw, dtype=np.float32).reshape(
            data["count"], data["dims"])
        vectors = cls(data["model"], data["variant"], data["ids"], matrix,
                      data["fingerprint"])
        if index is not None:
            vectors.check(index)
        return vectors

    def check(self, index: Index) -> None:
        """Vectors built from a different index are the silent RAG failure.

        Nothing errors when stale vectors meet a fresh index: ids still line up
        by position, scores still come back, and the ranking is simply wrong
        for reasons no log will mention. The fingerprint covers the chunk ids
        and their text, so a rebuild that changed either is caught here.
        """
        if self.fingerprint != index.fingerprint:
            raise SystemExit(
                f"{self.model} vectors were built from a different "
                f"{self.variant} index ({self.fingerprint[:16]} != "
                f"{index.fingerprint[:16]}). Re-run scripts/build_kb.py.")
        if [c["id"] for c in index.chunks] != self.ids:
            raise SystemExit(f"{self.model}: chunk order differs from the index")

    def dense(self, query_vector: np.ndarray) -> np.ndarray:
        """Cosine similarity, which is a dot product here.

        Both sides are L2-normalised already - the encoders return unit vectors
        and build_kb.py stores them unchanged - so normalising again would cost
        a pass over the matrix to divide by one.
        """
        return self.matrix @ query_vector.astype(np.float32)


def ranking(scores: np.ndarray, chunks: list[dict], top: int) -> list[str]:
    """Chunk ids ordered by score, best first, ties broken by index order."""
    order = np.argsort(-scores, kind="stable")[:top]
    return [chunks[i]["id"] for i in order if scores[i] > 0]


def rrf(rankings: list[list[str]], top: int, k: int = RRF_K) -> list[str]:
    """Merge rankings by position. Scores never meet, so scales cannot clash."""
    points: dict[str, float] = {}
    for ranked in rankings:
        for position, chunk_id in enumerate(ranked, start=1):
            points[chunk_id] = points.get(chunk_id, 0.0) + 1.0 / (k + position)
    return sorted(points, key=lambda c: -points[c])[:top]


def hits(chunk_ids: list[str], index: Index,
         scores: dict[str, float] | None = None) -> list[Hit]:
    by_id = {c["id"]: c for c in index.chunks}
    out = []
    for rank, chunk_id in enumerate(chunk_ids, start=1):
        c = by_id[chunk_id]
        out.append(Hit(
            chunk_id=chunk_id, doc_id=c["doc_id"],
            score=(scores or {}).get(chunk_id, 0.0), rank=rank,
            title=c["title"], heading=c.get("heading", ""), url=c["url"],
            url_is_page=bool(c.get("url_is_page")), text=c["text"]))
    return out


def search(query: str, index: Index, method: str, top: int = 5,
           vectors: Vectors | None = None,
           query_vector: np.ndarray | None = None) -> list[Hit]:
    """One query, one method.

    The query vector arrives as an argument rather than being embedded here, so
    that a benchmark can embed 430 queries once per encoder and reuse them
    across both chunkings and both methods that need them - 1,290 calls instead
    of 14 x 430.
    """
    if method == "bm25":
        scores = index.bm25(query)
        return hits(ranking(scores, index.chunks, top), index,
                    dict(zip([c["id"] for c in index.chunks], scores)))

    if vectors is None or query_vector is None:
        raise ValueError(f"method {method!r} needs vectors and a query vector")

    dense_scores = vectors.dense(query_vector)
    if method == "dense":
        return hits(ranking(dense_scores, index.chunks, top), index,
                    dict(zip([c["id"] for c in index.chunks], dense_scores)))

    if method == "hybrid":
        # Fused from deeper lists than are returned: a document that RRF should
        # promote has to appear in at least one list first, and cutting both to
        # five before merging would throw away exactly the evidence fusion is
        # supposed to use.
        deep = max(top * 4, 20)
        lexical = ranking(index.bm25(query), index.chunks, deep)
        semantic = ranking(dense_scores, index.chunks, deep)
        return hits(rrf([lexical, semantic], top), index)

    raise ValueError(f"unknown method {method!r}")


def documents(found: list[Hit]) -> list[str]:
    """Chunk hits rolled up to documents, first appearance winning.

    Article and section have to be compared at document level or they are not
    comparable at all: a section index can spend three of its five slots inside
    one article and still have found exactly one document.
    """
    seen: list[str] = []
    for hit in found:
        if hit.doc_id not in seen:
            seen.append(hit.doc_id)
    return seen
