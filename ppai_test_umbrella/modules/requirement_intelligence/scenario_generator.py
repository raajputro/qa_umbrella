from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from .prompt_builder import SYSTEM_PROMPT, build_continuation_instruction, build_iterative_instruction
from .quality_gate import filter_and_deduplicate, testcase_signature, similarity

load_dotenv()


class OllamaScenarioGenerator:
    """
    Evidence-first Ollama testcase generator.

    Important behavior:
    - No forced minimum testcase count.
    - Deterministic generation options for local models.
    - Every testcase must pass the quality gate.
    - Duplicate checks use behavior signatures, not title-only matching.
    """

    MAX_CONTINUATION_ATTEMPTS = 2

    def __init__(
        self,
        model: Optional[str] = None,
        ollama_url: str = "http://localhost:11434/api/chat",
        timeout: Optional[int] = None,
        temperature: float = 0.0,
        force_json: bool = True,
    ):
        self.model = model or os.getenv("PPAI_LLM_MODEL", "qwen2.5-coder:7b")
        self.ollama_url = ollama_url
        self.timeout = timeout or int(os.getenv("PPAI_LLM_TIMEOUT", "1800"))
        self.temperature = float(os.getenv("PPAI_LLM_TEMPERATURE", str(temperature)))
        self.force_json = force_json
        self.num_ctx = int(os.getenv("PPAI_LLM_NUM_CTX", "8192"))
        self.seed = int(os.getenv("PPAI_LLM_SEED", "42"))

    def generate_from_prompt(
        self,
        prompt: str,
        existing_test_cases: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        existing = existing_test_cases or []
        existing_titles = [
            tc.get("title", "").strip()
            for tc in existing
            if isinstance(tc, dict) and tc.get("title", "").strip()
        ]

        generation_prompt = self._build_iterative_prompt(prompt, existing_titles) if existing_titles else prompt
        parsed = self._generate_and_parse(generation_prompt)

        if parsed is None:
            if existing:
                return self._build_cumulative_result(existing, [], {}, [])
            return {"error": "Model did not return valid JSON.", "raw_output": ""}

        new_tcs = parsed.get("test_cases", [])
        if not isinstance(new_tcs, list):
            new_tcs = []

        # Use the prompt itself as source text because it contains the feature requirement details.
        valid_new_tcs, rejected = filter_and_deduplicate(
            new_tcs,
            source_text=prompt,
            existing=existing,
            similarity_threshold=0.75,
        )

        if rejected:
            print(f"\n  Quality gate rejected {len(rejected)} unsupported/duplicate testcase(s).")
            for item in rejected[:5]:
                bad = item.get("test_case", {})
                title = bad.get("title", "<missing title>") if isinstance(bad, dict) else str(bad)
                print(f"    - {title}: {', '.join(item.get('reasons', []))}")

        return self._build_cumulative_result(existing, valid_new_tcs, parsed, rejected)

    def _get_covered_functional_summary(self, titles: List[str]) -> str:
        keywords = set()
        for title in titles:
            for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", title.lower()):
                if word not in {"verify", "ensure", "validate", "that", "with", "from", "should", "user", "system"}:
                    keywords.add(word)
        if keywords:
            return "Functional keywords already covered: " + ", ".join(sorted(keywords)[:80])
        return ""

    def _build_iterative_prompt(self, original_prompt: str, existing_titles: List[str]) -> str:
        # Give more than 15 titles; duplicates are worse than a slightly longer prompt.
        latest_titles = existing_titles[-80:]
        covered_summary = self._get_covered_functional_summary(existing_titles)
        return f"{original_prompt}\n{build_iterative_instruction(latest_titles, covered_summary)}"

    def _build_cumulative_result(
        self,
        existing: List[Dict[str, Any]],
        new_tcs: List[Dict[str, Any]],
        parsed_metadata: Dict[str, Any],
        rejected: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        cumulative = list(existing) + list(new_tcs)

        for i, tc in enumerate(cumulative, start=1):
            tc["test_case_id"] = f"TC-{i:03d}"

        existing_sigs = {testcase_signature(tc) for tc in existing if isinstance(tc, dict)}
        actual_new_count = sum(1 for tc in cumulative if testcase_signature(tc) not in existing_sigs)

        return {
            "feature_id": parsed_metadata.get("feature_id", ""),
            "feature_name": parsed_metadata.get("feature_name", ""),
            "test_cases": cumulative,
            "generated_test_case_count": len(cumulative),
            "new_test_case_count": actual_new_count,
            "no_new_test_cases": bool(parsed_metadata.get("no_new_test_cases", False)),
            "clarification_needed": parsed_metadata.get("clarification_needed", []),
        }

    def _generate_and_parse(self, prompt: str) -> Optional[Dict[str, Any]]:
        raw_output = self._call_ollama(prompt)
        parsed = self._parse_json_response(raw_output)
        if parsed is None:
            parsed = self._attempt_continuation(prompt, raw_output)
        return parsed

    def _call_ollama(self, prompt: str) -> str:
        if "\n---\n" in prompt:
            system_msg, user_msg = prompt.split("\n---\n", 1)
        else:
            system_msg = SYSTEM_PROMPT
            user_msg = prompt

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg.strip()},
                {"role": "user", "content": user_msg.strip()},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": 0.2,
                "repeat_penalty": 1.1,
                "num_ctx": self.num_ctx,
                "seed": self.seed,
            },
        }
        if self.force_json:
            payload["format"] = "json"

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.ollama_url}\n"
                f"Run: ollama serve\n"
                f"Then ensure model is installed: ollama pull {self.model}"
            ) from None
        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                f"Ollama timed out after {self.timeout} seconds with model '{self.model}'.\n"
                f"Suggestion: Reduce scope to one feature or increase PPAI_LLM_TIMEOUT."
            ) from None
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise RuntimeError(
                    f"Ollama could not find model '{self.model}'. Run: ollama pull {self.model}"
                ) from None
            raise

        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    def _attempt_continuation(self, original_prompt: str, partial_output: str) -> Optional[Dict[str, Any]]:
        for attempt in range(self.MAX_CONTINUATION_ATTEMPTS):
            if not partial_output or not partial_output.strip().startswith("{"):
                return None
            continuation_prompt = build_continuation_instruction(partial_output)
            continuation_output = self._call_ollama(f"{SYSTEM_PROMPT}\n---\n{continuation_prompt}")
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
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        return None
