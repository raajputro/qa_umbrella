from __future__ import annotations

from pathlib import Path

from ppai_test_umbrella.shared.models import TestCase
from ppai_test_umbrella.shared.settings import settings


class AutomationGenerator:
    def generate_playwright_skeleton(self, testcase: TestCase) -> Path:
        path = settings.generated_dir / f"{testcase.testcase_id.lower()}_playwright.py"
        code = f'''from playwright.sync_api import Page\n\n\ndef test_{testcase.testcase_id.lower()}(page: Page):\n    # Auto-generated starter from PPAI prototype\n    # Title: {testcase.title}\n    page.goto("https://example.com")\n    # TODO: replace selectors and steps\n'''
        for step in testcase.steps:
            code += f"    # - {step}\n"
        code += "    assert page is not None\n"
        path.write_text(code, encoding="utf-8")
        return path

    def generate_api_skeleton(self, testcase: TestCase) -> Path:
        path = settings.generated_dir / f"{testcase.testcase_id.lower()}_api_test.py"
        code = f'''import httpx\n\n\ndef test_{testcase.testcase_id.lower()}():\n    # Auto-generated API starter\n    response = httpx.get("https://example.com/health")\n    assert response.status_code in (200, 204)\n'''
        path.write_text(code, encoding="utf-8")
        return path
