"""Example helper showing how you would use the self-healing memory with Playwright."""
from playwright.sync_api import Page
import requests


def healed_click(page: Page, primary: str, candidates: list[str]):
    selectors = [primary] + [c for c in candidates if c != primary]
    last_error = None
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=3000)
            return selector
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"All selectors failed. Last error: {last_error}")


def fetch_healed_locators(page_name: str, locator_name: str, failed_selector: str, dom_hints: list[str]) -> list[str]:
    resp = requests.post(
        "http://127.0.0.1:8000/heal/locator",
        json={
            "page_name": page_name,
            "locator_name": locator_name,
            "failed_selector": failed_selector,
            "dom_hints": dom_hints,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("candidates", [])
