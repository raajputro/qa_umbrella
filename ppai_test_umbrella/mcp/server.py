# from __future__ import annotations

# from ppai_test_umbrella.modules.prototype_service import PrototypeService
# from ppai_test_umbrella.agents.self_healing_agent import SelfHealingAgent
# from ppai_test_umbrella.shared.io_utils import read_text
# from ppai_test_umbrella.shared.settings import settings

# service = PrototypeService()
# healer = SelfHealingAgent()


# def _run_stub() -> None:
#     print("MCP package not installed. Install with: pip install -e .[mcp]")
#     print("Then rerun: python -m ppai_test_umbrella.mcp.server")


# try:
#     from mcp.server.fastmcp import FastMCP
# except Exception:
#     FastMCP = None


# if FastMCP is None:
#     if __name__ == "__main__":
#         _run_stub()
# else:
#     mcp = FastMCP("PPAI Test Umbrella MCP")

#     @mcp.tool()
#     def list_requirements() -> list[str]:
#         return [str(p) for p in settings.requirements_dir.glob("**/*") if p.is_file()]

#     @mcp.tool()
#     def read_requirement(path: str) -> str:
#         return read_text(path)

#     @mcp.tool()
#     def generate_from_requirement(path: str) -> dict:
#         return service.generate_from_file(path)

#     @mcp.tool()
#     def save_locator_fix(page_name: str, locator_name: str, successful_selector: str, note: str = "") -> dict:
#         return healer.save_locator_fix(page_name, locator_name, successful_selector, note)

#     @mcp.tool()
#     def heal_locator(page_name: str, locator_name: str, failed_selector: str, dom_hints: list[str] | None = None) -> dict:
#         from ppai_test_umbrella.shared.models import LocatorHealingRequest
#         req = LocatorHealingRequest(
#             page_name=page_name,
#             locator_name=locator_name,
#             failed_selector=failed_selector,
#             dom_hints=dom_hints or [],
#         )
#         return healer.heal_locator(req).model_dump()

#     if __name__ == '__main__':
#         mcp.run()


from __future__ import annotations

from pathlib import Path

from ppai_test_umbrella.modules.prototype_service import PrototypeService
from ppai_test_umbrella.agents.self_healing_agent import SelfHealingAgent
from ppai_test_umbrella.shared.io_utils import read_text, read_json
from ppai_test_umbrella.shared.settings import settings

service = PrototypeService()
healer = SelfHealingAgent()


def _run_stub() -> None:
    print("MCP package not installed.")
    print("Install with: pip install -e .[mcp]")
    print("Then rerun: python -m ppai_test_umbrella.mcp.server")


try:
    from mcp.server.fastmcp import FastMCP # type: ignore
except Exception:
    FastMCP = None


if FastMCP is None:
    if __name__ == "__main__":
        _run_stub()
else:
    mcp = FastMCP("PPAI Test Umbrella MCP")

    # -----------------------------
    # Requirement tools
    # -----------------------------

    @mcp.tool()
    def list_requirements() -> list[str]:
        return [str(p) for p in settings.requirements_dir.glob("**/*") if p.is_file()]

    @mcp.tool()
    def read_requirement(path: str) -> str:
        return read_text(path)

    @mcp.tool()
    def parse_requirements(path: str) -> list[dict]:
        return service.parse_requirements(path)

    @mcp.tool()
    def list_features(path: str) -> list[dict]:
        return service.list_features(path)

    @mcp.tool()
    def get_feature(path: str, feature_id: str) -> dict:
        return service.get_feature(path, feature_id)

    @mcp.tool()
    def count_possible_test_scenarios(path: str, feature_id: str) -> dict:
        return service.count_possible_test_scenarios(path, feature_id)

    @mcp.tool()
    def generate_test_cases_for_feature(
        path: str,
        feature_id: str,
        count: int = 10,
    ) -> dict:
        return service.generate_test_cases_for_feature(path, feature_id, count)

    @mcp.tool()
    def generate_from_requirement(path: str) -> dict:
        return service.generate_from_file(path)

    # -----------------------------
    # Generated output tools
    # -----------------------------

    @mcp.tool()
    def list_generated_outputs() -> list[str]:
        return service.list_generated_outputs()

    @mcp.tool()
    def read_generated_output(name: str) -> str:
        return service.read_generated_output(name)

    # -----------------------------
    # Healing tools
    # -----------------------------

    @mcp.tool()
    def save_locator_fix(
        page_name: str,
        locator_name: str,
        successful_selector: str,
        note: str = "",
    ) -> dict:
        return healer.save_locator_fix(page_name, locator_name, successful_selector, note)

    @mcp.tool()
    def heal_locator(
        page_name: str,
        locator_name: str,
        failed_selector: str,
        dom_hints: list[str] | None = None,
    ) -> dict:
        from ppai_test_umbrella.shared.models import LocatorHealingRequest

        req = LocatorHealingRequest(
            page_name=page_name,
            locator_name=locator_name,
            failed_selector=failed_selector,
            dom_hints=dom_hints or [],
        )
        return healer.heal_locator(req).model_dump()

    @mcp.tool()
    def save_step_fix(
        flow_name: str,
        steps: list[str],
        note: str = "",
    ) -> dict:
        return healer.save_step_fix(flow_name, steps, note)

    @mcp.tool()
    def heal_steps(
        flow_name: str,
        current_steps: list[str],
        failure_note: str = "",
    ) -> dict:
        from ppai_test_umbrella.shared.models import StepHealingRequest

        req = StepHealingRequest(
            flow_name=flow_name,
            current_steps=current_steps,
            failure_note=failure_note or None,
        )
        return healer.heal_steps(req).model_dump()

    # -----------------------------
    # Resources
    # -----------------------------

    @mcp.resource("requirements://files")
    def requirements_files() -> str:
        items = [str(p) for p in settings.requirements_dir.glob("**/*") if p.is_file()]
        return "\n".join(sorted(items))

    @mcp.resource("requirements://document/{path}")
    def requirement_document(path: str) -> str:
        return read_text(path)

    @mcp.resource("requirements://features/{path}")
    def requirement_features(path: str) -> str:
        import json
        return json.dumps(service.list_features(path), indent=2, ensure_ascii=False)

    @mcp.resource("generated://files")
    def generated_files() -> str:
        items = service.list_generated_outputs()
        return "\n".join(items)

    @mcp.resource("generated://file/{name}")
    def generated_file(name: str) -> str:
        return service.read_generated_output(name)

    @mcp.resource("healing://locator-memory")
    def locator_memory() -> str:
        import json
        data = read_json(healer.locator_memory_path, {"entries": []})
        return json.dumps(data, indent=2, ensure_ascii=False)

    @mcp.resource("healing://step-memory")
    def step_memory() -> str:
        import json
        data = read_json(healer.step_memory_path, {"flows": []})
        return json.dumps(data, indent=2, ensure_ascii=False)

    if __name__ == "__main__":
        mcp.run()