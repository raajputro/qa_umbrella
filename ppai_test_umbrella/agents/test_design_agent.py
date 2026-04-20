# from __future__ import annotations

# from pathlib import Path
# import re
# from typing import List

# from ppai_test_umbrella.shared.models import Requirement, Scenario, TestCase, AutomationCandidate
# from ppai_test_umbrella.shared.io_utils import read_text
 

# class RequirementParser:
#     def parse_file(self, path: str | Path) -> list[Requirement]:
#         text = read_text(path)
#         title = Path(path).stem.replace("_", " ").title()
#         blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
#         requirements: list[Requirement] = []
#         for idx, block in enumerate(blocks, start=1):
#             lines = [line.strip("- ") for line in block.splitlines() if line.strip()]
#             header = lines[0][:80]
#             description = " ".join(lines)
#             actors = self._extract_by_prefix(lines, ("actor:", "actors:"))
#             acceptance = self._extract_by_prefix(lines, ("acceptance:", "acceptance criteria:", "expected:"))
#             business_rules = self._extract_by_prefix(lines, ("rule:", "rules:", "validation:"))
#             requirements.append(Requirement(
#                 requirement_id=f"REQ-{idx:03d}",
#                 title=header or f"{title} Requirement {idx}",
#                 description=description,
#                 module=self._guess_module(description),
#                 actors=actors,
#                 business_rules=business_rules,
#                 acceptance_criteria=acceptance,
#                 source_path=str(Path(path).resolve()),
#             ))
#         if not requirements:
#             requirements.append(Requirement(
#                 requirement_id="REQ-001",
#                 title=title,
#                 description=text.strip(),
#                 module=self._guess_module(text),
#                 source_path=str(Path(path).resolve()),
#             ))
#         return requirements

#     def _extract_by_prefix(self, lines: list[str], prefixes: tuple[str, ...]) -> list[str]:
#         found = []
#         for line in lines:
#             low = line.lower()
#             for prefix in prefixes:
#                 if low.startswith(prefix):
#                     found.append(line.split(":", 1)[1].strip())
#         return found

#     def _guess_module(self, text: str) -> str:
#         low = text.lower()
#         if any(k in low for k in ["login", "sign in", "authentication"]):
#             return "authentication"
#         if any(k in low for k in ["member", "customer", "profile"]):
#             return "member_management"
#         if any(k in low for k in ["payment", "transaction", "checkout"]):
#             return "payments"
#         return "general"


# class ScenarioGenerator:
#     def generate(self, requirements: List[Requirement]) -> list[Scenario]:
#         scenarios: list[Scenario] = []
#         n = 1
#         for req in requirements:
#             base = req.title
#             flavors = [
#                 ("positive", f"Validate happy path for {base}", "high", ["smoke", req.module]),
#                 ("negative", f"Validate negative and validation rules for {base}", "high", ["negative", req.module]),
#                 ("boundary", f"Validate boundary and edge behavior for {base}", "medium", ["boundary", req.module]),
#             ]
#             for scenario_type, title, priority, tags in flavors:
#                 scenarios.append(Scenario(
#                     scenario_id=f"SCN-{n:03d}",
#                     requirement_id=req.requirement_id,
#                     title=title,
#                     objective=f"Ensure {base.lower()} behaves correctly under {scenario_type} conditions.",
#                     scenario_type=scenario_type,
#                     priority=priority,
#                     tags=tags,
#                 ))
#                 n += 1
#         return scenarios


# class TestCaseGenerator:
#     def generate(self, requirements: List[Requirement], scenarios: List[Scenario]) -> tuple[list[TestCase], list[AutomationCandidate]]:
#         req_map = {r.requirement_id: r for r in requirements}
#         testcases: list[TestCase] = []
#         candidates: list[AutomationCandidate] = []
#         t = 1
#         for scn in scenarios:
#             req = req_map[scn.requirement_id]
#             steps = [
#                 f"Open the relevant {req.module} page or entry point.",
#                 f"Prepare test data for scenario type: {scn.scenario_type}.",
#                 f"Execute the user flow described in requirement {req.requirement_id}.",
#                 "Verify UI, API, and data outcomes as applicable.",
#             ]
#             expected = [
#                 f"System behavior matches {scn.scenario_type} expectations.",
#                 "No unexpected error is shown.",
#             ]
#             automation_type = self._pick_automation_type(req.description)
#             testcase = TestCase(
#                 testcase_id=f"TC-{t:03d}",
#                 scenario_id=scn.scenario_id,
#                 title=scn.title,
#                 preconditions=["Test environment is reachable", "Required test data is available"],
#                 steps=steps,
#                 expected_results=expected,
#                 automation_candidate=True,
#                 automation_type=automation_type,
#             )
#             testcases.append(testcase)
#             candidates.append(AutomationCandidate(
#                 testcase_id=testcase.testcase_id,
#                 recommended_framework=automation_type,
#                 rationale=f"Recommended from requirement text in module '{req.module}'.",
#             ))
#             t += 1
#         return testcases, candidates

#     def _pick_automation_type(self, text: str) -> str:
#         low = text.lower()
#         if any(k in low for k in ["api", "endpoint", "service", "microservice"]):
#             return "pytest_httpx"
#         if any(k in low for k in ["database", "db", "table", "query"]):
#             return "pytest_db"
#         if any(k in low for k in ["load", "performance", "throughput"]):
#             return "k6"
#         return "playwright_pytest"

from __future__ import annotations

from pathlib import Path
import re
from typing import List

from ppai_test_umbrella.shared.models import (
    Requirement,
    Scenario,
    TestCase,
    AutomationCandidate,
    ActionStep,
)
from ppai_test_umbrella.shared.io_utils import read_text


class RequirementParser:
    def parse_file(self, path: str | Path) -> list[Requirement]:
        text = read_text(path)
        title = Path(path).stem.replace("_", " ").title()
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        requirements: list[Requirement] = []

        for idx, block in enumerate(blocks, start=1):
            lines = [line.strip("- ").strip() for line in block.splitlines() if line.strip()]
            header = lines[0][:120] if lines else f"{title} Requirement {idx}"
            description = " ".join(lines)
            actors = self._extract_by_prefix(lines, ("actor:", "actors:"))
            acceptance = self._extract_by_prefix(
                lines,
                ("acceptance:", "acceptance criteria:", "expected:")
            )
            business_rules = self._extract_by_prefix(
                lines,
                ("rule:", "rules:", "validation:")
            )

            requirements.append(
                Requirement(
                    requirement_id=f"REQ-{idx:03d}",
                    title=header or f"{title} Requirement {idx}",
                    description=description,
                    module=self._guess_module(description),
                    actors=actors,
                    business_rules=business_rules,
                    acceptance_criteria=acceptance,
                    source_path=str(Path(path).resolve()),
                )
            )

        if not requirements:
            requirements.append(
                Requirement(
                    requirement_id="REQ-001",
                    title=title,
                    description=text.strip(),
                    module=self._guess_module(text),
                    source_path=str(Path(path).resolve()),
                )
            )

        return requirements

    def _extract_by_prefix(self, lines: list[str], prefixes: tuple[str, ...]) -> list[str]:
        found = []
        for line in lines:
            low = line.lower()
            for prefix in prefixes:
                if low.startswith(prefix):
                    found.append(line.split(":", 1)[1].strip())
        return found

    def _guess_module(self, text: str) -> str:
        low = text.lower()
        if any(k in low for k in ["login", "sign in", "authentication", "password", "username"]):
            return "authentication"
        if any(k in low for k in ["member", "customer", "profile"]):
            return "member_management"
        if any(k in low for k in ["payment", "transaction", "checkout"]):
            return "payments"
        if any(k in low for k in ["api", "endpoint", "service", "microservice"]):
            return "api"
        return "general"


class ScenarioGenerator:
    def generate(self, requirements: List[Requirement]) -> list[Scenario]:
        scenarios: list[Scenario] = []
        n = 1

        for req in requirements:
            base = req.title
            flavors = [
                ("positive", f"Validate happy path for {base}", "high", ["smoke", req.module]),
                ("negative", f"Validate negative and validation rules for {base}", "high", ["negative", req.module]),
                ("boundary", f"Validate boundary and edge behavior for {base}", "medium", ["boundary", req.module]),
            ]

            for scenario_type, title, priority, tags in flavors:
                scenarios.append(
                    Scenario(
                        scenario_id=f"SCN-{n:03d}",
                        requirement_id=req.requirement_id,
                        title=title,
                        objective=f"Ensure {base.lower()} behaves correctly under {scenario_type} conditions.",
                        scenario_type=scenario_type,
                        priority=priority,
                        tags=tags,
                    )
                )
                n += 1

        return scenarios


class TestCaseGenerator:
    def generate(
        self,
        requirements: List[Requirement],
        scenarios: List[Scenario],
    ) -> tuple[list[TestCase], list[AutomationCandidate]]:
        req_map = {r.requirement_id: r for r in requirements}
        testcases: list[TestCase] = []
        candidates: list[AutomationCandidate] = []
        t = 1

        for scn in scenarios:
            req = req_map[scn.requirement_id]
            automation_type = self._pick_automation_type(req.description)
            action_steps = self._build_action_steps(req, scn, automation_type)

            testcase = TestCase(
                testcase_id=f"TC-{t:03d}",
                scenario_id=scn.scenario_id,
                title=scn.title,
                preconditions=["Test environment is reachable", "Required test data is available"],
                steps=[self._humanize_action_step(step) for step in action_steps],
                expected_results=self._build_expected_results(req, scn, automation_type),
                automation_candidate=True,
                automation_type=automation_type,
                action_steps=action_steps,
            )

            testcases.append(testcase)
            candidates.append(
                AutomationCandidate(
                    testcase_id=testcase.testcase_id,
                    recommended_framework=automation_type,
                    rationale=f"Recommended from requirement text in module '{req.module}'.",
                )
            )
            t += 1

        return testcases, candidates

    def _pick_automation_type(self, text: str) -> str:
        low = text.lower()
        if any(k in low for k in ["api", "endpoint", "service", "microservice"]):
            return "pytest_httpx"
        return "playwright_pytest"

    def _build_expected_results(
        self,
        req: Requirement,
        scn: Scenario,
        automation_type: str,
    ) -> list[str]:
        base = [
            f"System behavior matches {scn.scenario_type} expectations.",
            "No unexpected error is shown.",
        ]
        if automation_type == "playwright_pytest":
            if req.module == "authentication":
                if scn.scenario_type == "positive":
                    base.append("User should be redirected to dashboard or landing page.")
                else:
                    base.append("Validation or authentication error should be displayed.")
        elif automation_type == "pytest_httpx":
            if scn.scenario_type == "positive":
                base.append("API should return success response.")
            else:
                base.append("API should return validation/client error response.")
        return base

    def _build_action_steps(
        self,
        req: Requirement,
        scn: Scenario,
        automation_type: str,
    ) -> list[ActionStep]:
        if automation_type == "pytest_httpx":
            return self._build_api_steps(req, scn)
        return self._build_ui_steps(req, scn)

    def _build_ui_steps(self, req: Requirement, scn: Scenario) -> list[ActionStep]:
        module = req.module

        if module == "authentication":
            username = "valid_user"
            password = "valid_pass"

            if scn.scenario_type == "negative":
                password = "wrong_pass"
            elif scn.scenario_type == "boundary":
                username = ""
                password = ""

            steps = [
                ActionStep(action="goto", url="{{BASE_URL}}/login", description="Open login page"),
                ActionStep(action="fill", selector="{{LOGIN_USERNAME_SELECTOR}}", value=username, description="Enter username"),
                ActionStep(action="fill", selector="{{LOGIN_PASSWORD_SELECTOR}}", value=password, description="Enter password"),
                ActionStep(action="click", selector="{{LOGIN_SUBMIT_SELECTOR}}", description="Click login"),
            ]

            if scn.scenario_type == "positive":
                steps.append(
                    ActionStep(
                        action="assert_url_contains",
                        expected="{{LOGIN_SUCCESS_URL_CONTAINS}}",
                        description="Verify successful login redirect",
                    )
                )
            else:
                steps.append(
                    ActionStep(
                        action="assert_text_visible",
                        selector="{{LOGIN_ERROR_SELECTOR}}",
                        expected="{{LOGIN_ERROR_TEXT}}",
                        description="Verify error message",
                    )
                )

            return steps

        # generic UI fallback
        return [
            ActionStep(action="goto", url="{{BASE_URL}}", description="Open base URL"),
            ActionStep(action="wait", timeout_ms=2000, description="Wait for page to settle"),
            ActionStep(
                action="assert_url_contains",
                expected="{{BASE_URL_PATH_HINT}}",
                description="Verify target page opened",
            ),
        ]

    def _build_api_steps(self, req: Requirement, scn: Scenario) -> list[ActionStep]:
        endpoint = "{{API_BASE_URL}}/health"
        method = "GET"
        expected_status = "200"

        if scn.scenario_type == "negative":
            endpoint = "{{API_BASE_URL}}/invalid"
            expected_status = "404"

        return [
            ActionStep(
                action="api_request",
                description="Send API request",
                meta={
                    "method": method,
                    "url": endpoint,
                    "headers": {},
                    "json": {},
                },
            ),
            ActionStep(
                action="assert_status_code",
                expected=expected_status,
                description="Verify response status code",
            ),
        ]

    def _humanize_action_step(self, step: ActionStep) -> str:
        if step.action == "goto":
            return f"Open URL: {step.url}"
        if step.action == "fill":
            return f"Fill {step.selector} with {step.value}"
        if step.action == "click":
            return f"Click {step.selector}"
        if step.action == "assert_url_contains":
            return f"Verify current URL contains {step.expected}"
        if step.action == "assert_text_visible":
            return f"Verify text '{step.expected}' is visible in {step.selector}"
        if step.action == "api_request":
            return f"Send API request to {step.meta.get('url')}"
        if step.action == "assert_status_code":
            return f"Verify response status code is {step.expected}"
        if step.action == "wait":
            return f"Wait for {step.timeout_ms} ms"
        return step.description or step.action