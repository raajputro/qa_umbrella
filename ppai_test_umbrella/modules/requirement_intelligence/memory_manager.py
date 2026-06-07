from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class GenerationMemoryManager:
    def __init__(self, file_path: str | Path = "runtime_data/knowledge/generation_memory.json"):
        self.file_path = Path(file_path)
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        default = {
            "generated_titles": [],
            "feature_dependencies": {},
            "domain_glossary": [],
            "lessons_learned": [],
            "run_summaries": [],
        }
        if not self.file_path.exists():
            return default
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, default_val in default.items():
                    if key not in data:
                        data[key] = default_val
                return data
        except Exception:
            return default

    def save_memory(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving generation memory: {e}")

    def add_generated_titles(self, titles: List[str]) -> None:
        existing = set(t.lower() for t in self.memory["generated_titles"])
        for title in titles:
            t_strip = title.strip()
            if t_strip and t_strip.lower() not in existing:
                self.memory["generated_titles"].append(t_strip)
                existing.add(t_strip.lower())
        self.save_memory()


    def add_run_summary(
        self,
        feature_id: str,
        feature_name: str,
        test_case_count: int,
        type_breakdown: Dict[str, int] = None,
    ) -> None:
        """Record a summary of this generation run for cross-run contextual learning."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "feature_id": feature_id,
            "feature_name": feature_name,
            "test_case_count": test_case_count,
            "type_breakdown": type_breakdown or {},
        }
        self.memory["run_summaries"].append(summary)
        self.save_memory()

    def get_run_history_context(self, feature_id: str | None = None) -> str:
        """Return a prompt-ready string summarizing past runs for contextual improvement."""
        summaries = self.memory.get("run_summaries", [])
        if feature_id is not None:
            summaries = [s for s in summaries if str(s.get("feature_id")) == str(feature_id)]

        if not summaries:
            return ""

        lines = [
            "Previous generation runs (use this context to avoid duplicates and improve accuracy):"
        ]
        for s in summaries:
            types_str = ", ".join(f"{k}: {v}" for k, v in s.get("type_breakdown", {}).items())
            lines.append(
                f"- Feature {s['feature_id']} ({s['feature_name']}): "
                f"{s['test_case_count']} test cases generated"
                + (f" ({types_str})" if types_str else "")
            )
        return "\n".join(lines)
