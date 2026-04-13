from __future__ import annotations

from pathlib import Path
import tempfile
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import uvicorn

from ppai_test_umbrella.modules.prototype_service import PrototypeService
from ppai_test_umbrella.agents.self_healing_agent import SelfHealingAgent
from ppai_test_umbrella.shared.models import LocatorHealingRequest, StepHealingRequest

app = FastAPI(title="PPAI Test Umbrella Prototype API")
service = PrototypeService()
healer = SelfHealingAgent()


class QueryRequest(BaseModel):
    query: str
    limit: int = 5


class GenerateRequest(BaseModel):
    path: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ppai-test-umbrella"}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename).suffix or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    return service.ingest(tmp_path)


@app.post("/ask")
def ask(payload: QueryRequest) -> list[dict]:
    return service.ask(payload.query, limit=payload.limit)


@app.post("/generate")
def generate(payload: GenerateRequest) -> dict:
    return service.generate_from_file(payload.path)


@app.post("/heal/locator")
def heal_locator(payload: LocatorHealingRequest) -> dict:
    return healer.heal_locator(payload).model_dump()


@app.post("/heal/locator/save")
def save_locator_fix(payload: dict) -> dict:
    return healer.save_locator_fix(
        payload["page_name"],
        payload["locator_name"],
        payload["successful_selector"],
        payload.get("note", ""),
    )


@app.post("/heal/steps")
def heal_steps(payload: StepHealingRequest) -> dict:
    return healer.heal_steps(payload).model_dump()


@app.post("/heal/steps/save")
def save_step_fix(payload: dict) -> dict:
    return healer.save_step_fix(payload["flow_name"], payload["steps"], payload.get("note", ""))


def run() -> None:
    uvicorn.run("ppai_test_umbrella.apps.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
