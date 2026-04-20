from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass(slots=True)
class Settings:
    project_name: str = os.getenv("PPAI_PROJECT_NAME", "ppai-test-umbrella")
    env: str = os.getenv("PPAI_ENV", "local")
    base_dir: Path = Path(os.getenv("PPAI_BASE_DIR", "./runtime_data"))
    log_level: str = os.getenv("PPAI_LOG_LEVEL", "INFO")

    @property
    def requirements_dir(self) -> Path:
        return Path(os.getenv("PPAI_REQUIREMENTS_DIR",  "./reqs"))

    @property
    def knowledge_dir(self) -> Path:
        return Path(os.getenv("PPAI_KNOWLEDGE_DIR", str(self.base_dir / "knowledge")))

    @property
    def generated_dir(self) -> Path:
        return Path(os.getenv("PPAI_GENERATED_DIR", str(self.base_dir / "generated")))

    @property
    def healing_memory_dir(self) -> Path:
        return Path(os.getenv("PPAI_HEALING_MEMORY_DIR", str(self.base_dir / "healing_memory")))

    def ensure_dirs(self) -> None:
        for path in [self.base_dir, self.requirements_dir, self.knowledge_dir, self.generated_dir, self.healing_memory_dir]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
