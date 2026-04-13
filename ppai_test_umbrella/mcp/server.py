from __future__ import annotations

from ppai_test_umbrella.modules.prototype_service import PrototypeService
from ppai_test_umbrella.agents.self_healing_agent import SelfHealingAgent
from ppai_test_umbrella.shared.io_utils import read_text
from ppai_test_umbrella.shared.settings import settings

service = PrototypeService()
healer = SelfHealingAgent()


def _run_stub() -> None:
    print("MCP package not installed. Install with: pip install -e .[mcp]")
    print("Then rerun: python -m ppai_test_umbrella.mcp.server")


try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None


if FastMCP is None:
    if __name__ == "__main__":
        _run_stub()
else:
    mcp = FastMCP("PPAI Test Umbrella MCP")

    @mcp.tool()
    def list_requirements() -> list[str]:
        return [str(p) for p in settings.requirements_dir.glob("**/*") if p.is_file()]

    @mcp.tool()
    def read_requirement(path: str) -> str:
        return read_text(path)

    @mcp.tool()
    def generate_from_requirement(path: str) -> dict:
        return service.generate_from_file(path)

    @mcp.tool()
    def save_locator_fix(page_name: str, locator_name: str, successful_selector: str, note: str = "") -> dict:
        return healer.save_locator_fix(page_name, locator_name, successful_selector, note)

    @mcp.tool()
    def heal_locator(page_name: str, locator_name: str, failed_selector: str, dom_hints: list[str] | None = None) -> dict:
        from ppai_test_umbrella.shared.models import LocatorHealingRequest
        req = LocatorHealingRequest(
            page_name=page_name,
            locator_name=locator_name,
            failed_selector=failed_selector,
            dom_hints=dom_hints or [],
        )
        return healer.heal_locator(req).model_dump()

    if __name__ == '__main__':
        mcp.run()
