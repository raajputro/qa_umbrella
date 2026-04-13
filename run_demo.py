from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ppai_test_umbrella.modules.prototype_service import PrototypeService
from ppai_test_umbrella.agents.self_healing_agent import SelfHealingAgent
from ppai_test_umbrella.shared.models import LocatorHealingRequest, StepHealingRequest


def main() -> None:
    service = PrototypeService()
    example = Path("ppai_test_umbrella/examples/sample_requirement.md")

    print("== Ingest ==")
    print(json.dumps(service.ingest(example), indent=2))

    print("\n== Ask ==")
    print(json.dumps(service.ask("login invalid password error"), indent=2, ensure_ascii=False))

    print("\n== Generate ==")
    generated = service.generate_from_file(example)
    print(json.dumps({
        "output_path": generated["output_path"],
        "requirements": len(generated["requirements"]),
        "scenarios": len(generated["scenarios"]),
        "testcases": len(generated["testcases"]),
    }, indent=2))

    healer = SelfHealingAgent()
    healer.save_locator_fix("LoginPage", "Sign In Button", "#kc-login", "Known good selector")

    print("\n== Heal locator ==")
    print(healer.heal_locator(LocatorHealingRequest(
        page_name="LoginPage",
        locator_name="Sign In Button",
        failed_selector="text=Sign In",
        dom_hints=["Sign In", "#kc-login"],
    )).model_dump_json(indent=2))

    print("\n== Heal steps ==")
    print(healer.heal_steps(StepHealingRequest(
        flow_name="login",
        current_steps=["Open login page", "Enter username", "Enter password", "Click Sign In"],
        failure_note="overlay and modal in new tab",
    )).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
