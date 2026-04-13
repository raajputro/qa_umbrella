from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from ppai_test_umbrella.shared.io_utils import read_json, write_json
from ppai_test_umbrella.shared.models import (
    LocatorHealingRequest,
    LocatorHealingResponse,
    StepHealingRequest,
    StepHealingResponse,
)
from ppai_test_umbrella.shared.settings import settings


@dataclass(slots=True)
class SelfHealingAgent:
    locator_memory_path: Path = settings.healing_memory_dir / "locator_memory.json"
    step_memory_path: Path = settings.healing_memory_dir / "step_memory.json"

    def heal_locator(self, request: LocatorHealingRequest) -> LocatorHealingResponse:
        memory = read_json(self.locator_memory_path, {"entries": []})
        entries = memory["entries"]
        matches = [
            e for e in entries
            if e.get("page_name") == request.page_name and e.get("locator_name") == request.locator_name
        ]
        candidates: list[str] = []
        for item in matches:
            for sel in item.get("successful_selectors", []):
                if sel not in candidates:
                    candidates.append(sel)

        hint_candidates = self._from_dom_hints(request.dom_hints)
        for sel in hint_candidates:
            if sel not in candidates:
                candidates.append(sel)

        return LocatorHealingResponse(
            resolved=bool(candidates),
            candidates=candidates[:8],
            reason="Found prior successful selectors and/or DOM-derived fallbacks." if candidates else "No prior selector or useful hint found.",
        )

    def save_locator_fix(self, page_name: str, locator_name: str, successful_selector: str, note: str = "") -> dict:
        memory = read_json(self.locator_memory_path, {"entries": []})
        entries = memory["entries"]
        target = None
        for item in entries:
            if item.get("page_name") == page_name and item.get("locator_name") == locator_name:
                target = item
                break
        if target is None:
            target = {
                "page_name": page_name,
                "locator_name": locator_name,
                "successful_selectors": [],
                "notes": [],
            }
            entries.append(target)
        if successful_selector not in target["successful_selectors"]:
            target["successful_selectors"].append(successful_selector)
        if note:
            target["notes"].append(note)
        write_json(self.locator_memory_path, memory)
        return target

    def heal_steps(self, request: StepHealingRequest) -> StepHealingResponse:
        memory = read_json(self.step_memory_path, {"flows": []})
        similar = next((f for f in memory["flows"] if f.get("flow_name") == request.flow_name), None)
        updated = list(request.current_steps)
        reasons: list[str] = []
        if similar:
            previous_updates = similar.get("best_known_steps", [])
            if previous_updates:
                updated = previous_updates
                reasons.append("Reused previously successful step order for this flow.")
        if request.failure_note:
            note = request.failure_note.lower()
            if "modal" in note and not any("Dismiss blocking modal" in s for s in updated):
                updated.insert(1, "Dismiss blocking modal if shown.")
                reasons.append("Added modal handling from failure note.")
            if "new tab" in note and not any("Switch to the newly opened tab" in s for s in updated):
                updated.insert(2, "Switch to the newly opened tab if one appears.")
                reasons.append("Added new-tab handling from failure note.")
            if "overlay" in note and not any("Wait for overlay to disappear" in s for s in updated):
                updated.insert(1, "Wait for overlay to disappear before clicking.")
                reasons.append("Added overlay wait from failure note.")
        return StepHealingResponse(updated_steps=updated, reasons=reasons or ["No better step version found."])

    def save_step_fix(self, flow_name: str, steps: List[str], note: str = "") -> dict:
        memory = read_json(self.step_memory_path, {"flows": []})
        flows = memory["flows"]
        target = next((f for f in flows if f.get("flow_name") == flow_name), None)
        if target is None:
            target = {"flow_name": flow_name, "best_known_steps": [], "notes": []}
            flows.append(target)
        target["best_known_steps"] = steps
        if note:
            target["notes"].append(note)
        write_json(self.step_memory_path, memory)
        return target

    def _from_dom_hints(self, dom_hints: List[str]) -> List[str]:
        hints = [h.strip() for h in dom_hints if h.strip()]
        candidates: list[str] = []
        for hint in hints:
            clean = hint.replace('"', '').replace("'", "").strip()
            if clean.startswith("#") or clean.startswith(".") or clean.startswith("//"):
                candidates.append(clean)
                continue
            if len(clean.split()) <= 4:
                candidates.append(f"text={clean}")
                candidates.append(f"role=button[name='{clean}']")
        return candidates
