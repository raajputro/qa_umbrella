# # from __future__ import annotations

# # import re
# # from dataclasses import dataclass, field, asdict
# # from typing import Dict, List, Optional


# # # -----------------------------
# # # Data Models
# # # -----------------------------

# # @dataclass
# # class RequirementItem:
# #     item_id: str
# #     category: str
# #     text: str
# #     priority: Optional[str] = None
# #     source_chunk_index: Optional[int] = None
# #     source_line_index: Optional[int] = None
# #     tags: List[str] = field(default_factory=list)


# # @dataclass
# # class RequirementDocument:
# #     title: Optional[str]
# #     raw_text: str
# #     cleaned_text: str
# #     chunks: List[str]
# #     items: List[RequirementItem] = field(default_factory=list)

# #     def to_dict(self) -> Dict:
# #         return {
# #             "title": self.title,
# #             "raw_text": self.raw_text,
# #             "cleaned_text": self.cleaned_text,
# #             "chunks": self.chunks,
# #             "items": [asdict(item) for item in self.items],
# #         }


# # # -----------------------------
# # # Processor
# # # -----------------------------

# # class RequirementProcessor:
# #     """
# #     Converts raw requirement text into structured, normalized content
# #     that can later be passed to an LLM for test scenario generation.
# #     """

# #     def __init__(self, chunk_size: int = 2500, chunk_overlap: int = 250):
# #         if chunk_size <= 0:
# #             raise ValueError("chunk_size must be > 0")
# #         if chunk_overlap < 0:
# #             raise ValueError("chunk_overlap must be >= 0")
# #         if chunk_overlap >= chunk_size:
# #             raise ValueError("chunk_overlap must be smaller than chunk_size")

# #         self.chunk_size = chunk_size
# #         self.chunk_overlap = chunk_overlap

# #     # -----------------------------
# #     # Public API
# #     # -----------------------------

# #     def process(self, text: str, title: Optional[str] = None) -> RequirementDocument:
# #         if not text or not text.strip():
# #             raise ValueError("Requirement text is empty.")

# #         cleaned = self.clean_text(text)
# #         chunks = self.chunk_text(cleaned)
# #         items = self.extract_requirement_items(chunks)

# #         return RequirementDocument(
# #             title=title,
# #             raw_text=text,
# #             cleaned_text=cleaned,
# #             chunks=chunks,
# #             items=items,
# #         )

# #     def build_llm_ready_text(self, doc: RequirementDocument) -> str:
# #         """
# #         Build a concise but structured requirement summary for the LLM.
# #         """
# #         lines: List[str] = []

# #         if doc.title:
# #             lines.append(f"Document Title: {doc.title}")

# #         lines.append("Normalized Requirements Summary:")
# #         lines.append("")

# #         if doc.items:
# #             grouped = self.group_items_by_category(doc.items)
# #             for category, items in grouped.items():
# #                 lines.append(f"{category}:")
# #                 for item in items:
# #                     suffix = f" [priority={item.priority}]" if item.priority else ""
# #                     lines.append(f"- ({item.item_id}) {item.text}{suffix}")
# #                 lines.append("")
# #         else:
# #             lines.append(doc.cleaned_text)

# #         return "\n".join(lines).strip()

# #     def build_scenario_generation_prompt(self, doc: RequirementDocument) -> str:
# #         """
# #         Build the full prompt that your LLM client can send directly.
# #         """
# #         normalized = self.build_llm_ready_text(doc)

# #         return f"""
# # You are a senior QA analyst and test designer.

# # Your task is to read the requirement content below and generate high-quality structured test scenarios.

# # Requirements:
# # {normalized}

# # Instructions:
# # 1. Identify major business flows.
# # 2. Generate positive, negative, validation, boundary, and error-handling scenarios where applicable.
# # 3. Cover UI behavior, business rules, and integration expectations if implied.
# # 4. Avoid duplicates.
# # 5. Keep each scenario clear and testable.

# # Return output in this format:

# # [
# #   {{
# #     "scenario_name": "...",
# #     "scenario_type": "positive|negative|boundary|validation|integration",
# #     "preconditions": ["..."],
# #     "steps": ["..."],
# #     "expected_result": ["..."],
# #     "priority": "High|Medium|Low"
# #   }}
# # ]
# # """.strip()

# #     # -----------------------------
# #     # Cleaning
# #     # -----------------------------

# #     def clean_text(self, text: str) -> str:
# #         """
# #         Clean common PDF/doc extracted text issues without over-destroying meaning.
# #         """
# #         text = text.replace("\r\n", "\n").replace("\r", "\n")
# #         text = text.replace("\t", " ")

# #         # Remove repeated spaces
# #         text = re.sub(r"[ ]{2,}", " ", text)

# #         # Join broken words caused by line-break hyphenation: "applica-\ntion" -> "application"
# #         text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

# #         # Normalize too many blank lines
# #         text = re.sub(r"\n{3,}", "\n\n", text)

# #         # Remove page artifacts like "Page 2 of 10"
# #         text = re.sub(r"(?im)^page\s+\d+\s+(of\s+\d+)?\s*$", "", text)

# #         # Remove common header/footer separators
# #         text = re.sub(r"(?m)^[\-\_=]{3,}\s*$", "", text)

# #         # Trim line-by-line trailing spaces
# #         lines = [line.strip() for line in text.split("\n")]

# #         # Remove extremely noisy empty lines duplication again
# #         cleaned = "\n".join(lines)
# #         cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

# #         return cleaned.strip()

# #     # -----------------------------
# #     # Chunking
# #     # -----------------------------

# #     def chunk_text(self, text: str) -> List[str]:
# #         """
# #         Character-based chunking with overlap.
# #         Safer than naive line-only chunking for mixed PDF text.
# #         """
# #         if len(text) <= self.chunk_size:
# #             return [text]

# #         chunks: List[str] = []
# #         start = 0
# #         text_len = len(text)

# #         while start < text_len:
# #             end = min(start + self.chunk_size, text_len)
# #             chunk = text[start:end]

# #             # Try not to cut in middle of sentence/line when possible
# #             if end < text_len:
# #                 last_break = max(chunk.rfind("\n"), chunk.rfind(". "), chunk.rfind("; "))
# #                 if last_break > int(self.chunk_size * 0.6):
# #                     end = start + last_break + 1
# #                     chunk = text[start:end]

# #             chunks.append(chunk.strip())

# #             if end >= text_len:
# #                 break

# #             start = max(end - self.chunk_overlap, 0)

# #         return chunks

# #     # -----------------------------
# #     # Extraction
# #     # -----------------------------

# #     def extract_requirement_items(self, chunks: List[str]) -> List[RequirementItem]:
# #         """
# #         Extract candidate requirement lines using simple heuristics.
# #         This is intentionally deterministic and LLM-free.
# #         """
# #         items: List[RequirementItem] = []
# #         counter = 1

# #         for chunk_idx, chunk in enumerate(chunks):
# #             lines = [line.strip() for line in chunk.split("\n") if line.strip()]

# #             for line_idx, line in enumerate(lines):
# #                 normalized = self._normalize_line(line)

# #                 if not normalized or len(normalized) < 8:
# #                     continue

# #                 if self._is_requirement_line(normalized):
# #                     category = self._categorize_line(normalized)
# #                     priority = self._extract_priority(normalized)
# #                     tags = self._extract_tags(normalized)

# #                     item = RequirementItem(
# #                         item_id=f"REQ-{counter:03d}",
# #                         category=category,
# #                         text=normalized,
# #                         priority=priority,
# #                         source_chunk_index=chunk_idx,
# #                         source_line_index=line_idx,
# #                         tags=tags,
# #                     )
# #                     items.append(item)
# #                     counter += 1

# #         deduped = self._dedupe_items(items)
# #         return deduped

# #     def group_items_by_category(self, items: List[RequirementItem]) -> Dict[str, List[RequirementItem]]:
# #         grouped: Dict[str, List[RequirementItem]] = {}
# #         for item in items:
# #             grouped.setdefault(item.category, []).append(item)
# #         return grouped

# #     # -----------------------------
# #     # Internal helpers
# #     # -----------------------------

# #     def _normalize_line(self, line: str) -> str:
# #         line = re.sub(r"^[\-\*\u2022•]+\s*", "", line)
# #         line = re.sub(r"^\d+[\.\)]\s*", "", line)
# #         line = re.sub(r"^[A-Za-z]+\)\s*", "", line)
# #         line = re.sub(r"\s{2,}", " ", line)
# #         return line.strip(" -:;\t")

# #     def _is_requirement_line(self, line: str) -> bool:
# #         lower = line.lower()

# #         requirement_patterns = [
# #             r"\bshall\b",
# #             r"\bmust\b",
# #             r"\bshould\b",
# #             r"\bcan\b",
# #             r"\bmay\b",
# #             r"\buser can\b",
# #             r"\bsystem shall\b",
# #             r"\bsystem must\b",
# #             r"\bthe system\b",
# #             r"\bvalidation\b",
# #             r"\berror message\b",
# #             r"\blogin\b",
# #             r"\bsign in\b",
# #             r"\bsubmit\b",
# #             r"\bsave\b",
# #             r"\bsearch\b",
# #             r"\bcreate\b",
# #             r"\bupdate\b",
# #             r"\bdelete\b",
# #             r"\bupload\b",
# #             r"\bdownload\b",
# #             r"\bmandatory\b",
# #             r"\brequired\b",
# #             r"\bfield\b",
# #             r"\bexpected\b",
# #             r"\bacceptance criteria\b",
# #             r"\bprecondition\b",
# #             r"\bbusiness rule\b",
# #         ]

# #         if any(re.search(pattern, lower) for pattern in requirement_patterns):
# #             return True

# #         # Also allow moderate-length bullets with action-oriented wording
# #         action_verbs = [
# #             "display", "allow", "prevent", "show", "hide", "validate",
# #             "redirect", "generate", "capture", "record", "notify",
# #             "calculate", "filter", "sort", "select", "enter"
# #         ]
# #         if len(line.split()) >= 5 and any(lower.startswith(v) for v in action_verbs):
# #             return True

# #         return False

# #     def _categorize_line(self, line: str) -> str:
# #         lower = line.lower()

# #         if any(x in lower for x in ["login", "sign in", "logout", "password", "authentication"]):
# #             return "Authentication"
# #         if any(x in lower for x in ["role", "permission", "access", "authorization"]):
# #             return "Authorization"
# #         if any(x in lower for x in ["search", "filter", "sort"]):
# #             return "SearchAndFilter"
# #         if any(x in lower for x in ["create", "save", "submit", "add new"]):
# #             return "Create"
# #         if any(x in lower for x in ["update", "edit", "modify"]):
# #             return "Update"
# #         if any(x in lower for x in ["delete", "remove"]):
# #             return "Delete"
# #         if any(x in lower for x in ["upload", "attachment", "file", "document"]):
# #             return "FileHandling"
# #         if any(x in lower for x in ["error", "validation", "mandatory", "required", "invalid"]):
# #             return "Validation"
# #         if any(x in lower for x in ["report", "export", "download", "pdf", "excel", "csv"]):
# #             return "Reporting"
# #         if any(x in lower for x in ["api", "integration", "service", "third-party", "webhook"]):
# #             return "Integration"
# #         if any(x in lower for x in ["performance", "timeout", "response time", "concurrent"]):
# #             return "Performance"

# #         return "General"

# #     def _extract_priority(self, line: str) -> Optional[str]:
# #         lower = line.lower()
# #         if "high priority" in lower or "critical" in lower or "must" in lower:
# #             return "High"
# #         if "medium priority" in lower or "should" in lower:
# #             return "Medium"
# #         if "low priority" in lower or "may" in lower or "nice to have" in lower:
# #             return "Low"
# #         return None

# #     def _extract_tags(self, line: str) -> List[str]:
# #         lower = line.lower()
# #         tags: List[str] = []

# #         keyword_map = {
# #             "ui": ["screen", "page", "button", "field", "form", "ui", "dropdown"],
# #             "api": ["api", "endpoint", "service", "json", "request", "response"],
# #             "db": ["database", "db", "table", "record", "stored"],
# #             "security": ["password", "otp", "authentication", "authorization", "session"],
# #             "file": ["upload", "download", "pdf", "excel", "csv", "attachment"],
# #             "workflow": ["approval", "submit", "review", "status", "transition"],
# #         }

# #         for tag, words in keyword_map.items():
# #             if any(word in lower for word in words):
# #                 tags.append(tag)

# #         return tags

# #     def _dedupe_items(self, items: List[RequirementItem]) -> List[RequirementItem]:
# #         seen = set()
# #         result: List[RequirementItem] = []

# #         for item in items:
# #             key = re.sub(r"\s+", " ", item.text.strip().lower())
# #             if key in seen:
# #                 continue
# #             seen.add(key)
# #             result.append(item)

# #         return result

# from __future__ import annotations

# import re
# from dataclasses import dataclass, field, asdict
# from typing import Dict, List, Optional, Tuple


# # =========================================================
# # Data Models
# # =========================================================

# @dataclass
# class ChunkRecord:
#     chunk_id: str
#     feature_id: Optional[str]
#     feature_name: Optional[str]
#     chunk_index_within_feature: int
#     start_char: int
#     end_char: int
#     text: str
#     keywords: List[str] = field(default_factory=list)

#     def to_dict(self) -> Dict:
#         return asdict(self)


# @dataclass
# class FeatureRecord:
#     feature_id: str
#     feature_name: str
#     raw_text: str
#     chunks: List[ChunkRecord] = field(default_factory=list)

#     def to_dict(self) -> Dict:
#         return {
#             "feature_id": self.feature_id,
#             "feature_name": self.feature_name,
#             "raw_text": self.raw_text,
#             "chunks": [c.to_dict() for c in self.chunks],
#         }


# @dataclass
# class RequirementIndex:
#     title: Optional[str]
#     raw_text: str
#     cleaned_text: str
#     features: List[FeatureRecord] = field(default_factory=list)
#     chunks: List[ChunkRecord] = field(default_factory=list)

#     def to_dict(self) -> Dict:
#         return {
#             "title": self.title,
#             "raw_text": self.raw_text,
#             "cleaned_text": self.cleaned_text,
#             "features": [f.to_dict() for f in self.features],
#             "chunks": [c.to_dict() for c in self.chunks],
#         }


# @dataclass
# class PromptIntent:
#     action: str
#     feature_id: Optional[str] = None
#     requested_test_case_count: int = 10


# # =========================================================
# # Processor
# # =========================================================

# class RequirementKnowledgeProcessor:
#     """
#     Reads an SRS-like document, detects feature sections, chunks them,
#     indexes them, and supports prompt-aware retrieval.
#     """

#     def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 150):
#         if chunk_size <= 0:
#             raise ValueError("chunk_size must be > 0")
#         if chunk_overlap < 0:
#             raise ValueError("chunk_overlap must be >= 0")
#         if chunk_overlap >= chunk_size:
#             raise ValueError("chunk_overlap must be smaller than chunk_size")

#         self.chunk_size = chunk_size
#         self.chunk_overlap = chunk_overlap

#     # =====================================================
#     # Public API
#     # =====================================================

#     def build_index(self, text: str, title: Optional[str] = None) -> RequirementIndex:
#         if not text or not text.strip():
#             raise ValueError("Requirement text is empty.")

#         cleaned = self.clean_text(text)
#         features = self.extract_features(cleaned)
#         all_chunks: List[ChunkRecord] = []

#         for feature in features:
#             feature.chunks = self.chunk_feature(feature)
#             all_chunks.extend(feature.chunks)

#         return RequirementIndex(
#             title=title,
#             raw_text=text,
#             cleaned_text=cleaned,
#             features=features,
#             chunks=all_chunks,
#         )

#     def answer_prompt(self, req_index: RequirementIndex, prompt: str) -> Dict:
#         intent = self.parse_prompt(prompt)

#         if intent.action == "feature_test_estimate_and_generate":
#             feature = self.get_feature_by_id(req_index, intent.feature_id)
#             if not feature:
#                 raise ValueError(f"Could not find feature {intent.feature_id}")

#             possible_count = self.estimate_possible_test_scenarios(feature)
#             relevant_chunks = [c.text for c in feature.chunks]

#             return {
#                 "feature_id": feature.feature_id,
#                 "feature_name": feature.feature_name,
#                 "possible_test_scenario_count": possible_count,
#                 "retrieved_chunk_count": len(feature.chunks),
#                 "retrieved_chunks": relevant_chunks,
#                 "test_case_generation_prompt": self.build_test_case_generation_prompt(
#                     feature=feature,
#                     requested_count=intent.requested_test_case_count,
#                     possible_scenario_count=possible_count,
#                 ),
#             }

#         raise ValueError(f"Unsupported prompt intent: {intent.action}")

#     # =====================================================
#     # Cleaning
#     # =====================================================

#     def clean_text(self, text: str) -> str:
#         text = text.replace("\r\n", "\n").replace("\r", "\n")
#         text = text.replace("\t", " ")
#         text = re.sub(r"[ ]{2,}", " ", text)
#         text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
#         text = re.sub(r"\n{3,}", "\n\n", text)
#         text = re.sub(r"(?im)^page\s+\d+(\s+of\s+\d+)?\s*$", "", text)
#         text = re.sub(r"(?m)^[\-\_=]{3,}\s*$", "", text)

#         lines = [line.strip() for line in text.split("\n")]
#         cleaned = "\n".join(lines)
#         cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
#         return cleaned.strip()

#     # =====================================================
#     # Feature Extraction
#     # =====================================================

#     def extract_features(self, text: str) -> List[FeatureRecord]:
#         """
#         Detects sections like:
#         - Feature 6: Member Setup
#         - 6. Member Setup
#         - 6 Member Setup
#         - Feature-6 Member Setup
#         """

#         lines = text.split("\n")
#         feature_positions: List[Tuple[int, str, str]] = []

#         patterns = [
#             re.compile(r"^\s*feature\s*[-:]?\s*(\d+)\s*[:\-]?\s*(.+?)\s*$", re.I),
#             re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$"),
#             re.compile(r"^\s*(\d+)\s*[:\-]\s*(.+?)\s*$"),
#         ]

#         for idx, line in enumerate(lines):
#             stripped = line.strip()
#             if not stripped:
#                 continue

#             for pattern in patterns:
#                 match = pattern.match(stripped)
#                 if match:
#                     feature_id = match.group(1).strip()
#                     feature_name = match.group(2).strip()
#                     if self._looks_like_feature_heading(feature_name):
#                         feature_positions.append((idx, feature_id, feature_name))
#                         break

#         if not feature_positions:
#             return [
#                 FeatureRecord(
#                     feature_id="1",
#                     feature_name="Full Document",
#                     raw_text=text,
#                 )
#             ]

#         features: List[FeatureRecord] = []

#         for i, (start_idx, feature_id, feature_name) in enumerate(feature_positions):
#             end_idx = feature_positions[i + 1][0] if i + 1 < len(feature_positions) else len(lines)
#             feature_text = "\n".join(lines[start_idx:end_idx]).strip()

#             features.append(
#                 FeatureRecord(
#                     feature_id=feature_id,
#                     feature_name=feature_name,
#                     raw_text=feature_text,
#                 )
#             )

#         return features

#     def _looks_like_feature_heading(self, text: str) -> bool:
#         if len(text.split()) > 15:
#             return False

#         weak_words = {"page", "version", "revision", "date", "author", "contents"}
#         lower = text.lower()

#         if any(word == lower for word in weak_words):
#             return False

#         return True

#     # =====================================================
#     # Chunking
#     # =====================================================

#     def chunk_feature(self, feature: FeatureRecord) -> List[ChunkRecord]:
#         text = feature.raw_text
#         chunks: List[ChunkRecord] = []

#         if len(text) <= self.chunk_size:
#             return [
#                 ChunkRecord(
#                     chunk_id=f"F{feature.feature_id}_C001",
#                     feature_id=feature.feature_id,
#                     feature_name=feature.feature_name,
#                     chunk_index_within_feature=1,
#                     start_char=0,
#                     end_char=len(text),
#                     text=text,
#                     keywords=self.extract_keywords(text),
#                 )
#             ]

#         start = 0
#         chunk_no = 1
#         text_len = len(text)

#         while start < text_len:
#             end = min(start + self.chunk_size, text_len)
#             chunk = text[start:end]

#             if end < text_len:
#                 last_break = max(chunk.rfind("\n"), chunk.rfind(". "), chunk.rfind("; "))
#                 if last_break > int(self.chunk_size * 0.6):
#                     end = start + last_break + 1
#                     chunk = text[start:end]

#             chunks.append(
#                 ChunkRecord(
#                     chunk_id=f"F{feature.feature_id}_C{chunk_no:03d}",
#                     feature_id=feature.feature_id,
#                     feature_name=feature.feature_name,
#                     chunk_index_within_feature=chunk_no,
#                     start_char=start,
#                     end_char=end,
#                     text=chunk.strip(),
#                     keywords=self.extract_keywords(chunk),
#                 )
#             )

#             if end >= text_len:
#                 break

#             start = max(end - self.chunk_overlap, 0)
#             chunk_no += 1

#         return chunks

#     # =====================================================
#     # Prompt Understanding
#     # =====================================================

#     def parse_prompt(self, prompt: str) -> PromptIntent:
#         lower = prompt.lower()

#         feature_match = re.search(r"\bfeature\s+(\d+)\b", lower)
#         feature_id = feature_match.group(1) if feature_match else None

#         count_match = re.search(r"\bwrite\s+me\s+(\d+)\s+test\s+cases\b", lower)
#         if not count_match:
#             count_match = re.search(r"\b(\d+)\s+test\s+cases\b", lower)

#         requested_count = int(count_match.group(1)) if count_match else 10

#         if "count possible test scenarios" in lower and "test case" in lower:
#             return PromptIntent(
#                 action="feature_test_estimate_and_generate",
#                 feature_id=feature_id,
#                 requested_test_case_count=requested_count,
#             )

#         return PromptIntent(
#             action="feature_test_estimate_and_generate",
#             feature_id=feature_id,
#             requested_test_case_count=requested_count,
#         )

#     # =====================================================
#     # Retrieval
#     # =====================================================

#     def get_feature_by_id(self, req_index: RequirementIndex, feature_id: Optional[str]) -> Optional[FeatureRecord]:
#         if feature_id is None:
#             return None

#         for feature in req_index.features:
#             if str(feature.feature_id) == str(feature_id):
#                 return feature
#         return None

#     # =====================================================
#     # Estimation Logic
#     # =====================================================

#     def estimate_possible_test_scenarios(self, feature: FeatureRecord) -> int:
#         """
#         Heuristic estimate of how many distinct test scenarios may exist.
#         This is not the final generated count from an LLM.
#         It estimates based on functional points + validations + conditions.
#         """

#         text = feature.raw_text.lower()

#         action_patterns = [
#             r"\blogin\b",
#             r"\bsign in\b",
#             r"\bcreate\b",
#             r"\badd\b",
#             r"\bsave\b",
#             r"\bsubmit\b",
#             r"\bupdate\b",
#             r"\bedit\b",
#             r"\bdelete\b",
#             r"\bremove\b",
#             r"\bsearch\b",
#             r"\bfilter\b",
#             r"\bupload\b",
#             r"\bdownload\b",
#             r"\bapprove\b",
#             r"\breject\b",
#             r"\bview\b",
#             r"\bprint\b",
#         ]

#         validation_patterns = [
#             r"\brequired\b",
#             r"\bmandatory\b",
#             r"\bvalidation\b",
#             r"\berror\b",
#             r"\binvalid\b",
#             r"\bmust\b",
#             r"\bshould\b",
#             r"\bmax(?:imum)?\b",
#             r"\bmin(?:imum)?\b",
#             r"\blength\b",
#             r"\bformat\b",
#         ]

#         condition_patterns = [
#             r"\bif\b",
#             r"\bwhen\b",
#             r"\bonly\b",
#             r"\bdepending on\b",
#             r"\brole\b",
#             r"\bpermission\b",
#             r"\bstatus\b",
#             r"\bactive\b",
#             r"\binactive\b",
#         ]

#         actions = sum(len(re.findall(p, text)) for p in action_patterns)
#         validations = sum(len(re.findall(p, text)) for p in validation_patterns)
#         conditions = sum(len(re.findall(p, text)) for p in condition_patterns)

#         # Weighted estimate
#         estimated = (actions * 2) + validations + conditions

#         # Minimum sensible floor
#         if estimated < 8:
#             estimated = 8

#         return estimated

#     # =====================================================
#     # Prompt Builder for LLM
#     # =====================================================

#     def build_test_case_generation_prompt(
#         self,
#         feature: FeatureRecord,
#         requested_count: int,
#         possible_scenario_count: int,
#     ) -> str:
#         return f"""
# You are a senior QA analyst.

# Read the requirement for the following feature and produce a structured answer.

# Feature ID: {feature.feature_id}
# Feature Name: {feature.feature_name}
# Estimated Possible Test Scenarios: {possible_scenario_count}

# Requirement Text:
# {feature.raw_text}

# Your tasks:
# 1. Confirm the feature name.
# 2. Estimate how many possible test scenarios can be derived from this feature.
# 3. Write exactly {requested_count} strong test cases.
# 4. Cover positive, negative, validation, boundary, workflow, and error handling where applicable.
# 5. Keep test cases specific to this feature only.

# Return JSON in this format:
# {{
#   "feature_id": "{feature.feature_id}",
#   "feature_name": "{feature.feature_name}",
#   "possible_test_scenario_count": {possible_scenario_count},
#   "test_cases": [
#     {{
#       "test_case_id": "TC-001",
#       "title": "",
#       "type": "positive|negative|boundary|validation|workflow",
#       "preconditions": [],
#       "steps": [],
#       "expected_result": []
#     }}
#   ]
# }}
# """.strip()

#     # =====================================================
#     # Keywords
#     # =====================================================

#     def extract_keywords(self, text: str) -> List[str]:
#         stop_words = {
#             "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at",
#             "by", "with", "is", "are", "be", "as", "from", "that", "this", "will",
#             "shall", "should", "can", "may", "must", "user", "system"
#         }

#         tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text.lower())
#         freq: Dict[str, int] = {}

#         for token in tokens:
#             if token in stop_words:
#                 continue
#             freq[token] = freq.get(token, 0) + 1

#         sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
#         return [token for token, _ in sorted_tokens[:15]]

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
    action: str
    feature_id: Optional[str] = None
    requested_test_case_count: Optional[int] = None


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

    def answer_prompt(self, req_index: RequirementIndex, prompt: str) -> Dict:
        intent = self.parse_prompt(prompt)

        if intent.action == "feature_test_estimate_and_generate":
            feature = self.get_feature_by_id(req_index, intent.feature_id)
            if not feature:
                raise ValueError(f"Could not find feature {intent.feature_id}")

            possible_count = self.estimate_possible_test_scenarios(feature)
            feature_context = self.get_feature_context(feature)
            requested_count = intent.requested_test_case_count or possible_count

            return {
                "feature_id": feature.feature_id,
                "feature_name": feature.feature_name,
                "possible_test_scenario_count": possible_count,
                "requested_test_case_count": requested_count,
                "retrieved_chunk_count": len(feature.chunks),
                "retrieved_chunks": [c.text for c in feature.chunks],
                "feature_context": feature_context,
                "test_case_generation_prompt": self.build_test_case_generation_prompt(
                    feature=feature,
                    requested_count=requested_count,
                    possible_scenario_count=possible_count,
                ),
            }

        raise ValueError(f"Unsupported prompt intent: {intent.action}")

    def debug_feature_selection(
        self,
        req_index: RequirementIndex,
        feature_id: str,
        max_preview_chars: int = 1500,
    ) -> str:
        feature = self.get_feature_by_id(req_index, feature_id)
        if not feature:
            return f"Feature {feature_id} not found."

        context = self.get_feature_context(feature)
        preview = context[:max_preview_chars]

        return (
            f"{'=' * 180}\n"
            f"FEATURE SELECTED: {feature.feature_id} - {feature.feature_name}\n"
            f"FEATURE WORD COUNT: {self._word_count(feature.raw_text)}\n"
            f"FEATURE CHAR LENGTH: {len(feature.raw_text)}\n"
            f"CHUNK COUNT: {len(feature.chunks)}\n"
            f"CONTEXT PREVIEW:\n{preview}\n"
            f"{'=' * 180}"
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
                body_start_idx = idx + 1
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

        wants_all = bool(
            re.search(r"\b(all|every|complete|full)\s+(possible\s+)?test\s+cases\b", lower)
            or re.search(r"\bwrite\s+me\s+all\b", lower)
            or re.search(r"\bgenerate\s+all\b", lower)
        )

        count_match = re.search(
            r"\b(?:write|generate|create|give|make|prepare|produce)\s+(?:me\s+)?(\d+)\s+(?:test\s+)?cases\b",
            lower,
        )
        if not count_match:
            count_match = re.search(r"\b(\d+)\s+(?:test\s+)?cases\b", lower)
        if not count_match:
            count_match = re.search(
                r"\b(?:write|generate|create|give|make|prepare|produce)\s+(?:me\s+)?(\d+)\b",
                lower,
            )

        requested_count = None if wants_all else 10
        if count_match:
            requested_count = int(count_match.group(1))

        return PromptIntent(
            action="feature_test_estimate_and_generate",
            feature_id=feature_id,
            requested_test_case_count=requested_count,
        )

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

    def estimate_possible_test_scenarios(self, feature: FeatureRecord) -> int:
        """
        Heuristic estimate of distinct test scenarios.
        """
        text = feature.raw_text.lower()

        action_patterns = [
            r"\blogin\b",
            r"\bsign in\b",
            r"\bcreate\b",
            r"\badd\b",
            r"\bsave\b",
            r"\bsubmit\b",
            r"\bupdate\b",
            r"\bedit\b",
            r"\bdelete\b",
            r"\bremove\b",
            r"\bsearch\b",
            r"\bfilter\b",
            r"\bupload\b",
            r"\bdownload\b",
            r"\bapprove\b",
            r"\breject\b",
            r"\bview\b",
            r"\bprint\b",
            r"\bselect\b",
            r"\benter\b",
            r"\bvalidate\b",
        ]

        validation_patterns = [
            r"\brequired\b",
            r"\bmandatory\b",
            r"\bvalidation\b",
            r"\berror\b",
            r"\binvalid\b",
            r"\bmust\b",
            r"\bshould\b",
            r"\bmax(?:imum)?\b",
            r"\bmin(?:imum)?\b",
            r"\blength\b",
            r"\bformat\b",
            r"\bnot allow\b",
            r"\bnot permitted\b",
        ]

        condition_patterns = [
            r"\bif\b",
            r"\bwhen\b",
            r"\bonly\b",
            r"\bdepending on\b",
            r"\brole\b",
            r"\bpermission\b",
            r"\bstatus\b",
            r"\bactive\b",
            r"\binactive\b",
            r"\bsuccess\b",
            r"\bfailure\b",
        ]

        actions = sum(len(re.findall(p, text)) for p in action_patterns)
        validations = sum(len(re.findall(p, text)) for p in validation_patterns)
        conditions = sum(len(re.findall(p, text)) for p in condition_patterns)

        estimated = (actions * 2) + validations + conditions

        if estimated < 8:
            estimated = 8

        return estimated

    # =====================================================
    # Prompt Builder for LLM / Ollama
    # =====================================================

    def build_test_case_generation_prompt(
        self,
        feature: FeatureRecord,
        requested_count: int,
        possible_scenario_count: int,
    ) -> str:
        feature_context = self.get_feature_context(feature)

        return f"""
You are a senior QA analyst.

Read the requirement for the following feature and produce a structured answer.

Feature ID: {feature.feature_id}
Feature Name: {feature.feature_name}
Estimated Possible Test Scenarios: {possible_scenario_count}

Feature Requirement Details:
{feature_context}

Your tasks:
1. Confirm the exact feature name from the requirement details.
2. Estimate how many possible test scenarios can be derived from this feature.
3. Write exactly {requested_count} strong test cases. This count is derived from the estimated possible scenarios when the user asks for all test cases.
4. Cover positive, negative, validation, boundary, workflow, and error handling where applicable.
5. Do not stop at 10 unless the requested count is 10.
6. Use only this feature's details, not other features.

Return JSON in this format:
{{
  "feature_id": "{feature.feature_id}",
  "feature_name": "{feature.feature_name}",
  "possible_test_scenario_count": {possible_scenario_count},
  "test_cases": [
    {{
      "test_case_id": "TC-001",
      "title": "",
      "type": "positive|negative|boundary|validation|workflow|error-handling",
      "preconditions": [],
      "steps": [],
      "expected_result": []
    }}
  ]
}}
""".strip()

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
