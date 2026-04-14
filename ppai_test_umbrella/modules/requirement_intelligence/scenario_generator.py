# import json


# class ScenarioGenerator:
#     def __init__(self, llm_client):
#         self.llm_client = llm_client

#     def generate_from_prompt(self, prompt: str) -> dict:
#         raw = self.llm_client.generate(prompt)

#         try:
#             return json.loads(raw)
#         except json.JSONDecodeError:
#             return {
#                 "raw_output": raw,
#                 "error": "Model did not return valid JSON."
#             }

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class OllamaScenarioGenerator:
    def __init__(
        self,
        model: Optional[str] = None,
        ollama_url: str = "http://localhost:11434/api/generate",
        timeout: Optional[int] = None,
        temperature: float = 0.2,
        num_predict: Optional[int] = None,
        batch_size: int = 10,
        force_json: bool = True,
    ):
        self.model = model or os.getenv("PPAI_LLM_MODEL", "qwen2.5-coder:7b")
        self.ollama_url = ollama_url
        self.timeout = timeout or int(os.getenv("PPAI_LLM_TIMEOUT", "600"))
        self.temperature = temperature
        self.num_predict = num_predict or int(os.getenv("PPAI_LLM_NUM_PREDICT", "4096"))
        self.batch_size = batch_size
        self.force_json = force_json

    def generate_from_prompt(
        self,
        prompt: str,
        expected_count: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        batch_size = batch_size or self.batch_size

        if expected_count and expected_count > batch_size:
            return self._generate_batched(prompt, expected_count, batch_size)

        return self._generate_single(prompt)

    def _generate_single(self, prompt: str) -> Dict[str, Any]:
        raw_output = self._call_ollama(prompt)
        parsed = self._parse_json_response(raw_output)

        if parsed is not None:
            return parsed

        return {
            "error": "Model did not return valid JSON.",
            "raw_output": raw_output,
        }

    def _generate_batched(
        self,
        prompt: str,
        expected_count: int,
        batch_size: int,
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {
            "test_cases": [],
            "requested_test_case_count": expected_count,
            "generation_batches": [],
        }
        partial_errors: List[Dict[str, Any]] = []

        for start in range(1, expected_count + 1, batch_size):
            end = min(start + batch_size - 1, expected_count)
            current_count = end - start + 1
            batch_prompt = self._build_batch_prompt(
                prompt=prompt,
                batch_count=current_count,
                start_index=start,
                end_index=end,
                total_count=expected_count,
            )

            batch_output = self._generate_single(batch_prompt)
            if "error" in batch_output:
                partial_errors.append(
                    {
                        "start_index": start,
                        "end_index": end,
                        "error": batch_output,
                    }
                )
                break

            self._copy_metadata(merged, batch_output)
            test_cases = batch_output.get("test_cases", [])
            if not isinstance(test_cases, list):
                partial_errors.append(
                    {
                        "start_index": start,
                        "end_index": end,
                        "error": "Batch response did not include a test_cases list.",
                        "raw_output": batch_output,
                    }
                )
                break

            merged["test_cases"].extend(test_cases)
            merged["generation_batches"].append(
                {
                    "start_index": start,
                    "end_index": end,
                    "received_count": len(test_cases),
                }
            )

        merged["test_cases"] = self._renumber_test_cases(
            merged.get("test_cases", []),
            expected_count,
        )
        merged["generated_test_case_count"] = len(merged["test_cases"])

        if partial_errors:
            merged["generation_errors"] = partial_errors

        if len(merged["test_cases"]) != expected_count:
            merged["generation_warning"] = (
                f"Expected {expected_count} test cases, but generated "
                f"{len(merged['test_cases'])}."
            )

        return merged

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
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
        return data.get("response", "").strip()

    def _build_batch_prompt(
        self,
        prompt: str,
        batch_count: int,
        start_index: int,
        end_index: int,
        total_count: int,
    ) -> str:
        batch_prompt = re.sub(
            r"Write exactly \d+ strong test cases\..*",
            f"Write exactly {batch_count} strong test cases for this batch.",
            prompt,
        )

        return f"""
{batch_prompt}

Batch instructions:
- This is a batched generation request.
- Generate only test cases {start_index} through {end_index} of {total_count}.
- Return exactly {batch_count} test cases in this response.
- Number test_case_id globally as TC-{start_index:03d} through TC-{end_index:03d}.
- Do not include test cases outside this range.
- Return only valid JSON. Do not wrap it in markdown.
""".strip()

    def _copy_metadata(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        for key in [
            "feature_id",
            "feature_name",
            "possible_test_scenario_count",
        ]:
            if key in source and key not in target:
                target[key] = source[key]

    def _renumber_test_cases(
        self,
        test_cases: List[Any],
        expected_count: int,
    ) -> List[Any]:
        renumbered = test_cases[:expected_count]
        for index, test_case in enumerate(renumbered, start=1):
            if isinstance(test_case, dict):
                test_case["test_case_id"] = f"TC-{index:03d}"
        return renumbered

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
