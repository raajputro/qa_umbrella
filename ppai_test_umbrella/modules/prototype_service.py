# from __future__ import annotations

# from pathlib import Path
# from typing import Any

# from ppai_test_umbrella.agents.rag_agent import LightweightRAG
# from ppai_test_umbrella.agents.test_design_agent import RequirementParser, ScenarioGenerator, TestCaseGenerator
# from ppai_test_umbrella.agents.automation_agent import AutomationGenerator
# from ppai_test_umbrella.shared.io_utils import write_json
# from ppai_test_umbrella.shared.settings import settings


# class PrototypeService:
#     def __init__(self) -> None:
#         self.rag = LightweightRAG()
#         self.parser = RequirementParser()
#         self.scenario_gen = ScenarioGenerator()
#         self.testcase_gen = TestCaseGenerator()
#         self.auto_gen = AutomationGenerator()

#     def ingest(self, path: str | Path) -> dict[str, Any]:
#         return self.rag.ingest_file(path)

#     def ask(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
#         return [hit.model_dump() for hit in self.rag.search(query, limit=limit)]

#     def generate_from_file(self, path: str | Path) -> dict[str, Any]:
#         requirements = self.parser.parse_file(path)
#         scenarios = self.scenario_gen.generate(requirements)
#         testcases, candidates = self.testcase_gen.generate(requirements, scenarios)

#         out = {
#             "requirements": [r.model_dump() for r in requirements],
#             "scenarios": [s.model_dump() for s in scenarios],
#             "testcases": [t.model_dump() for t in testcases],
#             "automation_candidates": [c.model_dump() for c in candidates],
#         }
#         stem = Path(path).stem.lower().replace(" ", "_")
#         output_path = settings.generated_dir / f"{stem}_generated.json"
#         write_json(output_path, out)

#         for tc in testcases[:3]:
#             if tc.automation_type == "playwright_pytest":
#                 self.auto_gen.generate_playwright_skeleton(tc)
#             elif tc.automation_type == "pytest_httpx":
#                 self.auto_gen.generate_api_skeleton(tc)
#         return {"output_path": str(output_path), **out}

from __future__ import annotations

from pathlib import Path
from typing import Any

from ppai_test_umbrella.agents.rag_agent import LightweightRAG
from ppai_test_umbrella.agents.test_design_agent import (
    RequirementParser,
    ScenarioGenerator,
    TestCaseGenerator,
)
from ppai_test_umbrella.agents.automation_agent import AutomationGenerator
from ppai_test_umbrella.shared.io_utils import write_json, read_text
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

    def parse_requirements(self, path: str | Path) -> list[dict[str, Any]]:
        requirements = self.parser.parse_file(path)
        return [r.model_dump() for r in requirements]

    def list_features(self, path: str | Path) -> list[dict[str, Any]]:
        requirements = self.parser.parse_file(path)
        items: list[dict[str, Any]] = []

        for idx, req in enumerate(requirements, start=1):
            items.append(
                {
                    "feature_id": str(idx),
                    "requirement_id": req.requirement_id,
                    "title": req.title,
                    "module": req.module,
                    "description": req.description,
                    "actors": list(req.actors),
                    "business_rules": list(req.business_rules),
                    "acceptance_criteria": list(req.acceptance_criteria),
                    "source_path": req.source_path,
                }
            )

        return items

    def get_feature(self, path: str | Path, feature_id: str) -> dict[str, Any]:
        features = self.list_features(path)

        for item in features:
            if item["feature_id"] == str(feature_id):
                return item

        raise ValueError(f"Feature not found: {feature_id}")

    def count_possible_test_scenarios(
        self,
        path: str | Path,
        feature_id: str,
    ) -> dict[str, Any]:
        requirements = self.parser.parse_file(path)
        feature_index = int(feature_id) - 1

        if feature_index < 0 or feature_index >= len(requirements):
            raise ValueError(f"Feature not found: {feature_id}")

        req = requirements[feature_index]
        scenarios = self.scenario_gen.generate([req])

        return {
            "feature_id": str(feature_id),
            "requirement_id": req.requirement_id,
            "feature_name": req.title,
            "scenario_count_estimate": len(scenarios),
            "scenario_titles": [s.title for s in scenarios],
            "scenarios": [s.model_dump() for s in scenarios],
        }

    def generate_test_cases_for_feature(
        self,
        path: str | Path,
        feature_id: str,
        count: int = 10,
    ) -> dict[str, Any]:
        requirements = self.parser.parse_file(path)
        feature_index = int(feature_id) - 1

        if feature_index < 0 or feature_index >= len(requirements):
            raise ValueError(f"Feature not found: {feature_id}")

        req = requirements[feature_index]
        scenarios = self.scenario_gen.generate([req])
        testcases, candidates = self.testcase_gen.generate([req], scenarios)

        limited_cases = testcases[: max(1, count)]
        limited_candidates = [
            c for c in candidates if c.testcase_id in {tc.testcase_id for tc in limited_cases}
        ]

        out = {
            "feature_id": str(feature_id),
            "requirement_id": req.requirement_id,
            "feature_name": req.title,
            "scenario_count_estimate": len(scenarios),
            "scenarios": [s.model_dump() for s in scenarios],
            "testcases": [t.model_dump() for t in limited_cases],
            "automation_candidates": [c.model_dump() for c in limited_candidates],
        }

        stem = Path(path).stem.lower().replace(" ", "_")
        output_path = settings.generated_dir / f"{stem}_feature_{feature_id}_generated.json"
        write_json(output_path, out)

        return {
            "output_path": str(output_path),
            **out,
        }

    def list_generated_outputs(self) -> list[str]:
        return sorted(
            [str(p) for p in settings.generated_dir.glob("**/*") if p.is_file()]
        )

    def read_generated_output(self, name: str) -> str:
        path = settings.generated_dir / name
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Generated output not found: {name}")
        return read_text(path)

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