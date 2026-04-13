from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import math
import re
from typing import List

from ppai_test_umbrella.shared.io_utils import read_json, write_json, read_text
from ppai_test_umbrella.shared.models import RetrievalHit
from ppai_test_umbrella.shared.settings import settings

TOKEN_RE = re.compile(r"[A-Za-z0-9_/-]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


@dataclass(slots=True)
class LightweightRAG:
    index_path: Path = settings.knowledge_dir / "index.json"

    def load_index(self) -> dict:
        return read_json(self.index_path, {"documents": []})

    def save_index(self, data: dict) -> None:
        write_json(self.index_path, data)

    def ingest_file(self, path: str | Path) -> dict:
        source_path = str(Path(path).resolve())
        text = read_text(path)
        chunks = chunk_text(text)
        payload = self.load_index()
        docs = [d for d in payload["documents"] if d.get("source_path") != source_path]
        for i, chunk in enumerate(chunks, start=1):
            docs.append({
                "id": f"{Path(path).stem}-chunk-{i}",
                "source_path": source_path,
                "chunk": chunk,
                "tokens": tokenize(chunk),
            })
        payload["documents"] = docs
        self.save_index(payload)
        return {"source_path": source_path, "chunks_added": len(chunks)}

    def search(self, query: str, limit: int = 5) -> List[RetrievalHit]:
        q = tokenize(query)
        q_counts = Counter(q)
        payload = self.load_index()
        hits: list[RetrievalHit] = []
        for doc in payload["documents"]:
            d_counts = Counter(doc.get("tokens", []))
            score = self._cosine(q_counts, d_counts)
            if score <= 0:
                continue
            hits.append(RetrievalHit(
                source_id=doc["id"],
                score=round(score, 4),
                preview=doc["chunk"][:240],
                metadata={"source_path": doc["source_path"]},
            ))
        hits.sort(key=lambda x: x.score, reverse=True)
        return hits[:limit]

    @staticmethod
    def _cosine(a: Counter, b: Counter) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        numerator = sum(a[t] * b[t] for t in common)
        denom_a = math.sqrt(sum(v * v for v in a.values()))
        denom_b = math.sqrt(sum(v * v for v in b.values()))
        if not denom_a or not denom_b:
            return 0.0
        return numerator / (denom_a * denom_b)
