from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from .prompt_builder import (
    SYSTEM_PROMPT,
    build_iterative_instruction,
    build_retry_instruction,
    build_continuation_instruction,
)

load_dotenv()


class OllamaScenarioGenerator:
    """
    Generates test cases from an SRS prompt using Ollama's /api/chat endpoint.

    - Single-call generation — the model decides how many TCs to produce.
    - Automatic continuation if the model's JSON output is truncated.
    - Cumulative iterative generation: each run finds NEW test cases not yet
      covered by previous runs, and merges them with the existing set.
    - Deduplication against previously generated titles.
    """

    MAX_CONTINUATION_ATTEMPTS = 3
    MIN_TEST_CASES_PER_FEATURE = 10
    MAX_RETRY_FOR_MIN_COUNT = 2

    def __init__(
        self,
        model: Optional[str] = None,
        ollama_url: str = "http://localhost:11434/api/chat",
        timeout: Optional[int] = None,
        temperature: float = 0.2,
        force_json: bool = True,
    ):
        self.model = model or os.getenv("PPAI_LLM_MODEL", "gemma3:4b")
        self.ollama_url = ollama_url
        self.timeout = timeout or int(os.getenv("PPAI_LLM_TIMEOUT", "600"))
        self.temperature = temperature
        self.force_json = force_json

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_from_prompt(
        self,
        prompt: str,
        existing_test_cases: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate test cases for a feature prompt.

        If existing_test_cases is provided (from a previous run), the model is
        instructed to find ONLY new test cases that cover gaps. The new TCs are
        merged with the existing set and returned as the cumulative result.

        Returns dict with:
          - test_cases: the full cumulative list
          - new_test_case_count: how many NEW TCs were found this run
          - no_new_test_cases: True if the model found nothing new
        """
        existing = existing_test_cases or []
        existing_titles = [
            tc.get("title", "").strip()
            for tc in existing
            if isinstance(tc, dict) and tc.get("title", "").strip()
        ]

        # Build the prompt — if we have existing TCs, ask for gaps only
        if existing_titles:
            generation_prompt = self._build_iterative_prompt(prompt, existing_titles)
        else:
            generation_prompt = prompt

        # Generate
        parsed = self._generate_and_parse(generation_prompt)

        if parsed is None:
            if existing:
                # Return existing as-is, no new found
                return self._build_cumulative_result(existing, [], parsed_metadata={})
            return {
                "error": "Model did not return valid JSON.",
                "raw_output": "",
            }

        # Extract new TCs from model response
        new_tcs = parsed.get("test_cases", [])
        if not isinstance(new_tcs, list):
            new_tcs = []

        # Deduplicate new TCs against existing titles
        new_tcs = self._filter_duplicates(new_tcs, existing_titles)

        # If this is a first run and we got fewer than minimum, retry
        if not existing and len(new_tcs) < self.MIN_TEST_CASES_PER_FEATURE:
            print(
                f"  ⚠ Model generated only {len(new_tcs)} test cases (minimum is "
                f"{self.MIN_TEST_CASES_PER_FEATURE}). Re-reading SRS and retrying..."
            )
            parsed = self._retry_for_minimum(prompt, parsed)
            if parsed:
                new_tcs = parsed.get("test_cases", [])
                if not isinstance(new_tcs, list):
                    new_tcs = []
                # Deduplicate retry output against existing titles
                new_tcs = self._filter_duplicates(new_tcs, existing_titles)

        # Build cumulative result: existing + new (with final dedup)
        return self._build_cumulative_result(existing, new_tcs, parsed or {})

    # ------------------------------------------------------------------
    # Iterative prompt builder
    # ------------------------------------------------------------------

    def _get_covered_functional_summary(self, titles: List[str]) -> str:
        keywords = set()
        for t in titles:
            for word in ["date", "time", "project", "category", "description", "allocation", "draft", "archived", "error", "button", "popup", "validation", "mandatory", "zero", "empty"]:
                if word in t.lower():
                    keywords.add(word)
        if keywords:
            return "Functional areas already partially covered: " + ", ".join(sorted(keywords))
        return ""

    def _build_iterative_prompt(self, original_prompt: str, existing_titles: List[str]) -> str:
        """
        Wrap the original prompt with instructions to find ONLY new test cases.
        We cap the list of titles to the latest 15 to keep prompt size small,
        but summarize all covered functions.
        """
        latest_titles = existing_titles[-15:]
        covered_summary = self._get_covered_functional_summary(existing_titles)
        return f"{original_prompt}\n{build_iterative_instruction(latest_titles, covered_summary)}"

    # ------------------------------------------------------------------
    # Cumulative merge
    # ------------------------------------------------------------------

    def _build_cumulative_result(
        self,
        existing: List[Dict[str, Any]],
        new_tcs: List[Dict[str, Any]],
        parsed_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge existing + new TCs, deduplicate, enforce quality, renumber, build output."""
        # --- Pass 1: Exact title dedup ---
        seen_titles = set()
        merged = []
        for tc in list(existing) + list(new_tcs):
            if not isinstance(tc, dict):
                continue
            title = tc.get("title", "").strip()
            if not title:
                continue
            title_key = title.lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            merged.append(tc)

        # --- Pass 2: Semantic near-duplicate removal (word overlap) ---
        cumulative = []
        accepted_normalized = []  # list of word-sets for overlap check
        removed_dupes = 0

        for tc in merged:
            title = tc.get("title", "").strip().lower()
            # Strip common prefixes for comparison
            for prefix in ["verify that ", "ensure that ", "check that ",
                           "validate that ", "confirm that ", "assert that "]:
                if title.startswith(prefix):
                    title = title[len(prefix):]
                    break
            words = set(title.split())

            is_near_dup = False
            if len(words) > 3:
                for prev_words in accepted_normalized:
                    if len(prev_words) > 3:
                        overlap = len(words & prev_words) / min(len(words), len(prev_words))
                        if overlap > 0.90:
                            is_near_dup = True
                            removed_dupes += 1
                            break

            if not is_near_dup:
                cumulative.append(tc)
                accepted_normalized.append(words)

        if removed_dupes > 0:
            print(f"  Removed {removed_dupes} near-duplicate test case(s).")

        # --- Renumber all sequentially ---
        for i, tc in enumerate(cumulative, start=1):
            tc["test_case_id"] = f"TC-{i:03d}"

        # --- Calculate how many are genuinely new ---
        existing_title_set = set(
            tc.get("title", "").strip().lower()
            for tc in existing
            if isinstance(tc, dict) and tc.get("title", "").strip()
        )
        actual_new_count = sum(
            1 for tc in cumulative
            if tc.get("title", "").strip().lower() not in existing_title_set
        )

        no_new = parsed_metadata.get("no_new_test_cases", False)

        result = {
            "feature_id": parsed_metadata.get("feature_id", ""),
            "feature_name": parsed_metadata.get("feature_name", ""),
            "test_cases": cumulative,
            "generated_test_case_count": len(cumulative),
            "new_test_case_count": actual_new_count,
            "no_new_test_cases": no_new,
        }

        return result

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _filter_duplicates(
        self, new_tcs: List[Dict[str, Any]], existing_titles: List[str]
    ) -> List[Dict[str, Any]]:
        """Remove TCs from new_tcs whose titles match existing_titles."""
        existing_set = set(t.strip().lower() for t in existing_titles if t)
        unique = []
        for tc in new_tcs:
            if not isinstance(tc, dict):
                continue
            title = tc.get("title", "").strip()
            if not title:
                continue
            if title.lower() in existing_set:
                continue
            existing_set.add(title.lower())
            unique.append(tc)
        return unique

    # ------------------------------------------------------------------
    # Internal generation helpers
    # ------------------------------------------------------------------

    def _generate_and_parse(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Single call + continuation attempt. Returns parsed dict or None."""
        raw_output = self._call_ollama(prompt)
        parsed = self._parse_json_response(raw_output)

        if parsed is None:
            parsed = self._attempt_continuation(prompt, raw_output)

        return parsed

    def _retry_for_minimum(
        self,
        original_prompt: str,
        previous_output: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Retry when first-run generates fewer than MIN_TEST_CASES_PER_FEATURE."""
        best_output = previous_output

        for attempt in range(1, self.MAX_RETRY_FOR_MIN_COUNT + 1):
            existing_count = len(best_output.get("test_cases", []))
            existing_titles = [
                tc.get("title", "") for tc in best_output.get("test_cases", [])
                if isinstance(tc, dict)
            ]

            retry_prompt = (
                f"{original_prompt}\n\n"
                + build_retry_instruction(existing_count, self.MIN_TEST_CASES_PER_FEATURE, existing_titles)
            )

            print(f"  Retry attempt {attempt}/{self.MAX_RETRY_FOR_MIN_COUNT}...")
            retry_parsed = self._generate_and_parse(retry_prompt)

            if retry_parsed is None:
                continue

            retry_count = len(retry_parsed.get("test_cases", []))
            if retry_count > existing_count:
                best_output = retry_parsed
                print(f"  Retry produced {retry_count} test cases (up from {existing_count}).")

            if retry_count >= self.MIN_TEST_CASES_PER_FEATURE:
                print(f"  ✓ Minimum threshold met with {retry_count} test cases.")
                return best_output

        return best_output

    # ------------------------------------------------------------------
    # Ollama API call
    # ------------------------------------------------------------------

    def _call_ollama(self, prompt: str) -> str:
        """Call the Ollama /api/chat endpoint with system/user message split."""
        if "\n---\n" in prompt:
            system_msg, user_msg = prompt.split("\n---\n", 1)
        else:
            system_msg = SYSTEM_PROMPT
            user_msg = prompt

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg.strip()},
                {"role": "user", "content": user_msg.strip()},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }
        if self.force_json:
            payload["format"] = "json"

        try:
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.ollama_url}\n"
                f"Steps to fix:\n"
                f"  1. Run: python start_ollama.py\n"
                f"  2. Or manually start Ollama: ollama serve\n"
                f"  3. Ensure model '{self.model}' is installed: ollama pull {self.model}"
            ) from None
        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                f"Ollama timed out after {self.timeout} seconds while using model '{self.model}'.\n"
                f"Steps to fix:\n"
                f"  1. Restart Ollama\n"
                f"  2. Try a smaller/faster model in PPAI_LLM_MODEL\n"
                f"  3. Increase timeout for long test-case generation"
            ) from None
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise RuntimeError(
                    f"Ollama could not find model '{self.model}' at {self.ollama_url}\n"
                    f"Steps to fix:\n"
                    f"  1. Ensure Ollama is running: ollama serve\n"
                    f"  2. Pull the model: ollama pull {self.model}\n"
                    f"  3. Or set PPAI_LLM_MODEL in .env to an installed model"
                ) from None
            raise

        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    def _attempt_continuation(self, original_prompt: str, partial_output: str) -> Optional[Dict[str, Any]]:
        """
        If the model's output was truncated (incomplete JSON), ask it to continue.
        Returns parsed JSON or None if continuation also fails.
        """
        for attempt in range(self.MAX_CONTINUATION_ATTEMPTS):
            if not partial_output or not partial_output.strip().startswith("{"):
                return None

            continuation_prompt = build_continuation_instruction(partial_output)

            continuation_output = self._call_ollama(
                f"{SYSTEM_PROMPT}\n---\n{continuation_prompt}"
            )

            combined = partial_output.rstrip() + "\n" + continuation_output.lstrip()
            parsed = self._parse_json_response(combined)
            if parsed is not None:
                print(f"  Continuation attempt {attempt + 1} succeeded.")
                return parsed

            partial_output = combined

        return None

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        # 1. direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. extract fenced json block
        fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            candidate = fenced_match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 3. extract first {...} block
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            candidate = brace_match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        return None
