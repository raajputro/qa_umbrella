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
import re
from typing import Any, Dict, Optional

import requests


class OllamaScenarioGenerator:
    def __init__(
        self,
        model: str = "qwen2.5-coder:latest",
        ollama_url: str = "http://localhost:11434/api/generate",
        timeout: int = 180,
        temperature: float = 0.2,
    ):
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.temperature = temperature

    def generate_from_prompt(self, prompt: str) -> Dict[str, Any]:
        raw_output = self._call_ollama(prompt)
        parsed = self._parse_json_response(raw_output)

        if parsed is not None:
            return parsed

        return {
            "error": "Model did not return valid JSON.",
            "raw_output": raw_output,
        }

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"❌ Cannot connect to Ollama at {self.ollama_url}\n"
                f"Steps to fix:\n"
                f"  1. Run: python start_ollama.py\n"
                f"  2. Or manually start Ollama: ollama serve\n"
                f"  3. Ensure model '{self.model}' is installed: ollama pull {self.model}"
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise RuntimeError(
                    f"❌ Ollama endpoint not found at {self.ollama_url}\n"
                    f"Steps to fix:\n"
                    f"  1. Ensure Ollama is running: ollama serve\n"
                    f"  2. Pull the model: ollama pull {self.model}\n"
                    f"  3. Run: python start_ollama.py"
                )
            raise

        data = response.json()
        return data.get("response", "").strip()

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