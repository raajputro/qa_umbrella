# from __future__ import annotations

# from pathlib import Path

# from ppai_test_umbrella.shared.models import TestCase
# from ppai_test_umbrella.shared.settings import settings


# class AutomationGenerator:
#     def generate_playwright_skeleton(self, testcase: TestCase) -> Path:
#         path = settings.generated_dir / f"{testcase.testcase_id.lower()}_playwright.py"
#         code = f'''from playwright.sync_api import Page\n\n\ndef test_{testcase.testcase_id.lower()}(page: Page):\n    # Auto-generated starter from PPAI prototype\n    # Title: {testcase.title}\n    page.goto("https://example.com")\n    # TODO: replace selectors and steps\n'''
#         for step in testcase.steps:
#             code += f"    # - {step}\n"
#         code += "    assert page is not None\n"
#         path.write_text(code, encoding="utf-8")
#         return path

#     def generate_api_skeleton(self, testcase: TestCase) -> Path:
#         path = settings.generated_dir / f"{testcase.testcase_id.lower()}_api_test.py"
#         code = f'''import httpx\n\n\ndef test_{testcase.testcase_id.lower()}():\n    # Auto-generated API starter\n    response = httpx.get("https://example.com/health")\n    assert response.status_code in (200, 204)\n'''
#         path.write_text(code, encoding="utf-8")
#         return path

from __future__ import annotations

from pathlib import Path

from ppai_test_umbrella.shared.models import TestCase
from ppai_test_umbrella.shared.settings import settings


class AutomationGenerator:
    def generate_playwright_skeleton(self, testcase: TestCase) -> Path:
        path = settings.generated_dir / f"{testcase.testcase_id.lower()}_playwright.py"

        lines: list[str] = [
            "from playwright.sync_api import Page",
            "import pytest",
            "",
            "",
            f"def test_{self._safe_name(testcase.testcase_id.lower())}(page: Page):",
            "    # Auto-generated starter from PPAI prototype",
            f"    # TestCase ID: {testcase.testcase_id}",
            f"    # Title: {testcase.title}",
            f"    preconditions = {testcase.preconditions!r}",
            f"    steps = {testcase.steps!r}",
            f"    expected_results = {testcase.expected_results!r}",
            "",
            "    # TODO: replace with actual target URL",
            '    page.goto("https://example.com")',
            "",
            "    # Preconditions",
        ]

        for pre in testcase.preconditions:
            lines.append(f"    # - {pre}")

        lines.extend(
            [
                "",
                "    # Steps",
            ]
        )
        for step in testcase.steps:
            lines.append(f"    # - {step}")

        lines.extend(
            [
                "",
                "    # Expected results",
            ]
        )
        for expected in testcase.expected_results:
            lines.append(f"    # - {expected}")

        lines.extend(
            [
                "",
                "    # Placeholder assertion so file is runnable",
                "    assert page is not None",
            ]
        )

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def generate_api_skeleton(self, testcase: TestCase) -> Path:
        path = settings.generated_dir / f"{testcase.testcase_id.lower()}_api_test.py"

        lines: list[str] = [
            "import httpx",
            "",
            "",
            f"def test_{self._safe_name(testcase.testcase_id.lower())}():",
            "    # Auto-generated API starter",
            f"    # TestCase ID: {testcase.testcase_id}",
            f"    # Title: {testcase.title}",
            f"    preconditions = {testcase.preconditions!r}",
            f"    steps = {testcase.steps!r}",
            f"    expected_results = {testcase.expected_results!r}",
            "",
            "    # TODO: replace with actual API endpoint and assertions",
            '    response = httpx.get("https://example.com/health")',
            "    assert response.status_code in (200, 204)",
        ]

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def _safe_name(self, value: str) -> str:
        cleaned = []
        for ch in value:
            cleaned.append(ch if ch.isalnum() or ch == "_" else "_")
        result = "".join(cleaned).strip("_")
        while "__" in result:
            result = result.replace("__", "_")
        if not result:
            result = "generated_test"
        if result[0].isdigit():
            result = f"tc_{result}"
        return result