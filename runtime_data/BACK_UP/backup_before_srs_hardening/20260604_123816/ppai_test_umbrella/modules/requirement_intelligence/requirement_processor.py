from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# =========================================================
# Data Models
# =========================================================

@dataclass
class ChunkRecord:
    chunk_id: str
    feature_id: Optional[str]
    feature_name: Optional[str]
    chunk_index_within_feature: int
    start_char: int
    end_char: int
    text: str
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FeatureRecord:
    feature_id: str
    feature_name: str
    raw_text: str
    heading_line_index: Optional[int] = None
    chunks: List[ChunkRecord] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "heading_line_index": self.heading_line_index,
            "raw_text": self.raw_text,
            "chunks": [c.to_dict() for c in self.chunks],
        }


@dataclass
class RequirementIndex:
    title: Optional[str]
    raw_text: str
    cleaned_text: str
    features: List[FeatureRecord] = field(default_factory=list)
    chunks: List[ChunkRecord] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "features": [f.to_dict() for f in self.features],
            "chunks": [c.to_dict() for c in self.chunks],
        }


@dataclass
class PromptIntent:
    feature_id: Optional[str] = None


# =========================================================
# Processor
# =========================================================

class RequirementKnowledgeProcessor:
    """
    Reads an SRS-like document, removes TOC/index noise, detects real feature
    sections, chunks those sections, indexes them, and supports prompt-aware
    retrieval for focused test generation.
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 150,
        min_feature_word_count: int = 40,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if min_feature_word_count < 1:
            raise ValueError("min_feature_word_count must be >= 1")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_feature_word_count = min_feature_word_count

    # =====================================================
    # Public API
    # =====================================================

    def build_index(self, text: str, title: Optional[str] = None) -> RequirementIndex:
        if not text or not text.strip():
            raise ValueError("Requirement text is empty.")

        cleaned = self.clean_text(text)
        cleaned = self.remove_table_of_contents(cleaned)

        features = self.extract_features(cleaned)
        all_chunks: List[ChunkRecord] = []

        for feature in features:
            feature.chunks = self.chunk_feature(feature)
            all_chunks.extend(feature.chunks)

        return RequirementIndex(
            title=title,
            raw_text=text,
            cleaned_text=cleaned,
            features=features,
            chunks=all_chunks,
        )


    # =====================================================
    # Cleaning
    # =====================================================

    def clean_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\t", " ")
        text = re.sub(r"[ ]{2,}", " ", text)
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?im)^page\s+\d+(\s+of\s+\d+)?\s*$", "", text)
        text = re.sub(r"(?m)^[\-\_=]{3,}\s*$", "", text)

        lines = [line.strip() for line in text.split("\n")]
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    # =====================================================
    # TOC / Index Handling
    # =====================================================

    def is_toc_line(self, line: str) -> bool:
        """
        Detect lines commonly found in a table of contents or index, such as:
        - 6. Member Setup .......... 24
        - Feature 7: Loan Approval ....... 30
        - 6 Member Setup 24
        """
        line = line.strip()
        if not line:
            return False

        patterns = [
            r"^\s*(feature\s*)?\d+(\.\d+)?[\.\:\-]?\s+.+?\.{3,}\s*\d+\s*$",
            r"^\s*(feature\s*)?\d+(\.\d+)?[\.\:\-]?\s+.+?\s+\.{2,}\s*\d+\s*$",
            r"^\s*(feature\s*)?\d+(\.\d+)?[\.\:\-]?\s+.+\s+\d+\s*$",
            r"^\s*[A-Za-z].+?\.{3,}\s*\d+\s*$",
        ]

        for pattern in patterns:
            if re.match(pattern, line, re.I):
                words = line.split()
                if len(words) <= 14:
                    return True

        return False

    def remove_table_of_contents(self, text: str) -> str:
        """
        Removes obvious TOC/Contents/Index blocks.
        """
        lines = text.splitlines()
        if not lines:
            return text

        cleaned: List[str] = []
        in_toc = False
        toc_started = False
        toc_noise_count = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()

            if re.match(r"^(table of contents|contents|index)$", stripped, re.I):
                in_toc = True
                toc_started = True
                toc_noise_count = 0
                continue

            if in_toc:
                if not stripped:
                    toc_noise_count += 1
                    continue

                if self.is_toc_line(stripped):
                    toc_noise_count += 1
                    continue

                # Leave TOC when meaningful paragraph-like content starts
                if self._looks_like_body_content(stripped):
                    in_toc = False
                    cleaned.append(line)
                    continue

                # extra tolerance for noisy pages
                if toc_noise_count >= 5 and self._word_count(stripped) > 12:
                    in_toc = False
                    cleaned.append(line)
                    continue

                continue

            cleaned.append(line)

        if not toc_started:
            # No explicit TOC heading found, but some docs have TOC-like lines at the beginning.
            return self._remove_leading_toc_like_block("\n".join(cleaned).strip())

        return "\n".join(cleaned).strip()

    def _remove_leading_toc_like_block(self, text: str) -> str:
        """
        Removes a TOC-like block at the beginning even when no 'Contents' heading exists.
        """
        lines = text.splitlines()
        if not lines:
            return text

        leading_toc_hits = 0
        body_start_idx = 0

        for idx, line in enumerate(lines[:80]):  # inspect first part of doc
            stripped = line.strip()
            if not stripped:
                continue

            if self.is_toc_line(stripped):
                leading_toc_hits += 1
                continue

            if leading_toc_hits >= 3 and self._looks_like_body_content(stripped):
                return "\n".join(lines[idx:]).strip()

            if leading_toc_hits == 0:
                break

        return text

    # =====================================================
    # Feature Extraction
    # =====================================================

    def extract_features(self, text: str) -> List[FeatureRecord]:
        """
        Detect sections like:
        - Feature 6: Member Setup
        - 6. Member Setup
        - 6: Member Setup
        - FR-06 Member Setup
        - 6.0 Member Setup

        Ignores TOC/index lines and validates with lookahead body content.
        """
        lines = text.split("\n")
        feature_positions: List[Tuple[int, str, str]] = []

        patterns = [
            re.compile(r"^\s*feature\s*[-:]?\s*(\d+)\s*[:\-]?\s*(.+?)\s*$", re.I),
            re.compile(r"^\s*fr[-_\s]?0*(\d+)\s*[:\-]?\s*(.+?)\s*$", re.I),
            re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$"),
            re.compile(r"^\s*(\d+)\s*[:\-]\s*(.+?)\s*$"),
            re.compile(r"^\s*(\d+\.\d+)\s+(.+?)\s*$"),
        ]

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            if self.is_toc_line(stripped):
                continue

            for pattern in patterns:
                match = pattern.match(stripped)
                if not match:
                    continue

                feature_id = match.group(1).strip()
                feature_name = match.group(2).strip()

                if not self._looks_like_feature_heading(feature_name):
                    continue

                # validate by looking ahead for real content
                next_lines = lines[idx + 1 : idx + 10]
                non_empty_next_lines = [x.strip() for x in next_lines if x.strip()]
                lookahead_text = "\n".join(non_empty_next_lines)

                # reject headings that don't have enough body under them
                if self._word_count(lookahead_text) < 12:
                    continue

                # reject cases where following lines are still just TOC-ish
                tocish_count = sum(1 for x in non_empty_next_lines[:5] if self.is_toc_line(x))
                if tocish_count >= 2:
                    continue

                feature_positions.append((idx, feature_id, feature_name))
                break

        if not feature_positions:
            return [
                FeatureRecord(
                    feature_id="1",
                    feature_name="Full Document",
                    raw_text=text,
                    heading_line_index=0,
                )
            ]

        features: List[FeatureRecord] = []

        for i, (start_idx, feature_id, feature_name) in enumerate(feature_positions):
            end_idx = feature_positions[i + 1][0] if i + 1 < len(feature_positions) else len(lines)
            feature_text = "\n".join(lines[start_idx:end_idx]).strip()

            if self._word_count(feature_text) < self.min_feature_word_count:
                # Very short sections are often false positives or broken headings.
                # Skip unless there are no other features.
                continue

            features.append(
                FeatureRecord(
                    feature_id=str(feature_id).strip(),
                    feature_name=feature_name,
                    raw_text=feature_text,
                    heading_line_index=start_idx,
                )
            )

        if not features:
            return [
                FeatureRecord(
                    feature_id="1",
                    feature_name="Full Document",
                    raw_text=text,
                    heading_line_index=0,
                )
            ]

        return features

    def _looks_like_feature_heading(self, text: str) -> bool:
        if not text or self._word_count(text) > 15:
            return False

        lower = text.lower().strip()

        weak_exact_words = {
            "page",
            "version",
            "revision",
            "date",
            "author",
            "contents",
            "table of contents",
            "index",
        }

        if lower in weak_exact_words:
            return False

        weak_substrings = [
            "page no",
            "revision history",
            "document control",
            "table of contents",
        ]
        if any(x in lower for x in weak_substrings):
            return False

        # Headings that are just dotted lines or mostly punctuation are not real
        if re.fullmatch(r"[\.\-\_\s\d]+", text):
            return False

        return True

    # =====================================================
    # Chunking
    # =====================================================

    def chunk_feature(self, feature: FeatureRecord) -> List[ChunkRecord]:
        text = feature.raw_text
        chunks: List[ChunkRecord] = []

        if len(text) <= self.chunk_size:
            return [
                ChunkRecord(
                    chunk_id=f"F{feature.feature_id}_C001",
                    feature_id=feature.feature_id,
                    feature_name=feature.feature_name,
                    chunk_index_within_feature=1,
                    start_char=0,
                    end_char=len(text),
                    text=text,
                    keywords=self.extract_keywords(text),
                )
            ]

        start = 0
        chunk_no = 1
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk = text[start:end]

            if end < text_len:
                last_break = max(
                    chunk.rfind("\n"),
                    chunk.rfind(". "),
                    chunk.rfind("; "),
                    chunk.rfind(": "),
                )
                if last_break > int(self.chunk_size * 0.6):
                    end = start + last_break + 1
                    chunk = text[start:end]

            chunks.append(
                ChunkRecord(
                    chunk_id=f"F{feature.feature_id}_C{chunk_no:03d}",
                    feature_id=feature.feature_id,
                    feature_name=feature.feature_name,
                    chunk_index_within_feature=chunk_no,
                    start_char=start,
                    end_char=end,
                    text=chunk.strip(),
                    keywords=self.extract_keywords(chunk),
                )
            )

            if end >= text_len:
                break

            start = max(end - self.chunk_overlap, 0)
            chunk_no += 1

        return chunks

    def get_feature_context(self, feature: FeatureRecord, max_chunks: int = 8) -> str:
        chunks = sorted(feature.chunks, key=lambda c: c.chunk_index_within_feature)
        selected = chunks[:max_chunks]

        return "\n\n".join(
            f"[Chunk {c.chunk_id}]\n{c.text}" for c in selected
        )

    # =====================================================
    # Prompt Understanding
    # =====================================================

    def parse_prompt(self, prompt: str) -> PromptIntent:
        lower = prompt.lower()

        feature_match = re.search(r"\bfeature\s+(\d+(?:\.\d+)?)\b", lower)
        if not feature_match:
            feature_match = re.search(r"\bfr[-_\s]?0*(\d+)\b", lower)

        feature_id = feature_match.group(1) if feature_match else None

        return PromptIntent(feature_id=feature_id)

    # =====================================================
    # Retrieval
    # =====================================================

    def get_feature_by_id(
        self,
        req_index: RequirementIndex,
        feature_id: Optional[str],
    ) -> Optional[FeatureRecord]:
        if feature_id is None:
            return None

        normalized = self._normalize_feature_id(feature_id)
        candidates: List[FeatureRecord] = []

        for feature in req_index.features:
            fid = self._normalize_feature_id(feature.feature_id)

            if fid == normalized:
                candidates.append(feature)
                continue

            # support cases like 6 vs 06, or 6 vs 6.0
            if fid.lstrip("0") == normalized.lstrip("0"):
                candidates.append(feature)
                continue

            if fid.startswith(normalized + ".") or normalized.startswith(fid + "."):
                candidates.append(feature)

        if not candidates:
            return None

        # Prefer richer body, because TOC-like matches are usually shorter
        candidates.sort(
            key=lambda f: (
                self._word_count(f.raw_text),
                len(f.raw_text),
                len(f.chunks),
            ),
            reverse=True,
        )
        return candidates[0]

    # =====================================================
    # Estimation Logic
    # =====================================================


    # =====================================================
    # Prompt Builder for LLM / Ollama
    # =====================================================

    def build_test_case_generation_prompt(
        self,
        feature: FeatureRecord,
        user_instruction: Optional[str] = None,
        srs_context: Optional[str] = None,
    ) -> str:
        from .prompt_builder import build_generation_rules, SYSTEM_PROMPT

        feature_context = self.get_feature_context(feature)

        instructions = []
        if user_instruction and user_instruction.strip() != SYSTEM_PROMPT.strip():
            instructions.append(f"{SYSTEM_PROMPT}\nInstruction: {user_instruction.strip()}")
            instructions.append("---")
        else:
            instructions.append(SYSTEM_PROMPT)
            instructions.append("---")

        instructions.append(f"Feature ID: {feature.feature_id}")
        instructions.append(f"Feature Name: {feature.feature_name}")

        if srs_context:
            instructions.append(f"\nSRS-Wide Feature Context (for cross-feature interdependencies and impacts):\n{srs_context}\n")

        instructions.append(f"Feature Requirement Details:\n{feature_context}\n")
        instructions.append("---")

        instructions.append(build_generation_rules(feature.feature_id, feature.feature_name))

        return "\n".join(instructions)

    # =====================================================
    # Keywords
    # =====================================================

    def extract_keywords(self, text: str) -> List[str]:
        stop_words = {
            "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at",
            "by", "with", "is", "are", "be", "as", "from", "that", "this", "will",
            "shall", "should", "can", "may", "must", "user", "system"
        }

        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text.lower())
        freq: Dict[str, int] = {}

        for token in tokens:
            if token in stop_words:
                continue
            freq[token] = freq.get(token, 0) + 1

        sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [token for token, _ in sorted_tokens[:15]]

    # =====================================================
    # Internal Helpers
    # =====================================================

    def _normalize_feature_id(self, feature_id: str) -> str:
        return str(feature_id).strip().lower()

    def _word_count(self, text: str) -> int:
        if not text:
            return 0
        return len(re.findall(r"\b\w+\b", text))

    def _looks_like_body_content(self, text: str) -> bool:
        if not text:
            return False

        if self.is_toc_line(text):
            return False

        word_count = self._word_count(text)
        if word_count >= 10:
            return True

        # Paragraph-like indicators
        if re.search(r"\b(shall|must|should|user|system|when|if|screen|field|button|validation)\b", text, re.I):
            return True

        return False
