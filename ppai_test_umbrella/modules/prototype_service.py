from __future__ import annotations

from pathlib import Path
from typing import Any

from ppai_test_umbrella.agents.rag_agent import LightweightRAG
from ppai_test_umbrella.agents.test_design_agent import RequirementParser, ScenarioGenerator, TestCaseGenerator
from ppai_test_umbrella.agents.automation_agent import AutomationGenerator
from ppai_test_umbrella.shared.io_utils import write_json
from ppai_test_umbrella.shared.settings import settings


class PrototypeService:
    def __init__(self) -> None:
        self.rag = LightweightRAG()
        self.parser = RequirementParser()
        self.scenario_gen = ScenarioGenerator()
        self.testcase_gen = TestCaseGenerator()
        self.auto_gen = AutomationGenerator()

    def ingest(self, path: str | Path) -> dict[str, Any]:
        return self.rag.ingest_file(path)

    def ask(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return [hit.model_dump() for hit in self.rag.search(query, limit=limit)]

    def generate_from_file(self, path: str | Path) -> dict[str, Any]:
        requirements = self.parser.parse_file(path)
        scenarios = self.scenario_gen.generate(requirements)
        testcases, candidates = self.testcase_gen.generate(requirements, scenarios)

        out = {
            "requirements": [r.model_dump() for r in requirements],
            "scenarios": [s.model_dump() for s in scenarios],
            "testcases": [t.model_dump() for t in testcases],
            "automation_candidates": [c.model_dump() for c in candidates],
        }
        stem = Path(path).stem.lower().replace(" ", "_")
        output_path = settings.generated_dir / f"{stem}_generated.json"
        write_json(output_path, out)

        for tc in testcases[:3]:
            if tc.automation_type == "playwright_pytest":
                self.auto_gen.generate_playwright_skeleton(tc)
            elif tc.automation_type == "pytest_httpx":
                self.auto_gen.generate_api_skeleton(tc)
        return {"output_path": str(output_path), **out}
