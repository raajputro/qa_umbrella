from __future__ import annotations

from pathlib import Path
import json
import typer

from ppai_test_umbrella.modules.prototype_service import PrototypeService
from ppai_test_umbrella.agents.self_healing_agent import SelfHealingAgent
from ppai_test_umbrella.shared.models import LocatorHealingRequest, StepHealingRequest

app = typer.Typer(help="PPAI Test Umbrella prototype CLI")
service = PrototypeService()
healer = SelfHealingAgent()


@app.command()
def ingest(path: str):
    """Ingest a requirement file into the lightweight RAG index."""
    result = service.ingest(path)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def ask(query: str, limit: int = 5):
    """Search the lightweight RAG knowledge base."""
    result = service.ask(query, limit=limit)
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@app.command()
def generate(path: str):
    """Generate requirements, scenarios, test cases, and starter automation."""
    result = service.generate_from_file(path)
    summary = {
        "output_path": result["output_path"],
        "requirements": len(result["requirements"]),
        "scenarios": len(result["scenarios"]),
        "testcases": len(result["testcases"]),
        "automation_candidates": len(result["automation_candidates"]),
    }
    typer.echo(json.dumps(summary, indent=2))


@app.command("heal-locator")
def heal_locator(page_name: str, locator_name: str, failed_selector: str, dom_hint: list[str] = typer.Option(default=[])):
    req = LocatorHealingRequest(
        page_name=page_name,
        locator_name=locator_name,
        failed_selector=failed_selector,
        dom_hints=dom_hint,
    )
    result = healer.heal_locator(req)
    typer.echo(result.model_dump_json(indent=2))


@app.command("save-locator-fix")
def save_locator_fix(page_name: str, locator_name: str, successful_selector: str, note: str = ""):
    result = healer.save_locator_fix(page_name, locator_name, successful_selector, note)
    typer.echo(json.dumps(result, indent=2))


@app.command("heal-steps")
def heal_steps(flow_name: str, steps_file: str, failure_note: str = ""):
    steps = Path(steps_file).read_text(encoding="utf-8").splitlines()
    req = StepHealingRequest(flow_name=flow_name, current_steps=[s for s in steps if s.strip()], failure_note=failure_note)
    result = healer.heal_steps(req)
    typer.echo(result.model_dump_json(indent=2))


@app.command("save-step-fix")
def save_step_fix(flow_name: str, steps_file: str, note: str = ""):
    steps = [s for s in Path(steps_file).read_text(encoding="utf-8").splitlines() if s.strip()]
    result = healer.save_step_fix(flow_name, steps, note)
    typer.echo(json.dumps(result, indent=2))


from ppai_test_umbrella.modules.requirement_intelligence.scenario_service import generate_scenarios_from_file

@app.command()
def generate_scenarios(file: str):
    scenarios = generate_scenarios_from_file(file)
    print(f"Generated Scenarios:\n{scenarios}")


if __name__ == "__main__":
    app()
