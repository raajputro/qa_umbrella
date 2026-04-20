# # # from __future__ import annotations

# # # import json
# # # import os
# # # import subprocess
# # # import sys
# # # import uuid
# # # from pathlib import Path
# # # from typing import Any

# # # from ppai_test_umbrella.shared.io_utils import read_json, write_json
# # # from ppai_test_umbrella.shared.settings import settings


# # # class ExecutionService:
# # #     def __init__(self) -> None:
# # #         self.generated_dir = settings.generated_dir
# # #         self.executions_dir = self.generated_dir / "executions"
# # #         self.executions_dir.mkdir(parents=True, exist_ok=True)

# # #     def list_executable_generated_outputs(self) -> list[dict[str, Any]]:
# # #         items: list[dict[str, Any]] = []

# # #         for path in sorted(self.generated_dir.glob("*")):
# # #             if not path.is_file():
# # #                 continue

# # #             executable = False
# # #             kind = "unknown"

# # #             if path.suffix == ".py":
# # #                 executable = True
# # #                 kind = "python_test"
# # #             elif path.suffix == ".json":
# # #                 data = read_json(path, {})
# # #                 if isinstance(data, dict) and data.get("testcases"):
# # #                     executable = True
# # #                     kind = "json_test_bundle"

# # #             items.append(
# # #                 {
# # #                     "name": path.name,
# # #                     "path": str(path),
# # #                     "kind": kind,
# # #                     "executable": executable,
# # #                 }
# # #             )

# # #         return items

# # #     def execute_generated_output(self, name: str, mode: str = "dry_run") -> dict[str, Any]:
# # #         path = self.generated_dir / name
# # #         if not path.exists() or not path.is_file():
# # #             raise FileNotFoundError(f"Generated output not found: {name}")

# # #         run_id = uuid.uuid4().hex[:12]
# # #         run_dir = self.executions_dir / run_id
# # #         run_dir.mkdir(parents=True, exist_ok=True)

# # #         if path.suffix == ".py":
# # #             result = self._run_pytest_file(path, run_dir, mode=mode)
# # #         elif path.suffix == ".json":
# # #             result = self._run_json_bundle(path, run_dir, mode=mode)
# # #         else:
# # #             raise ValueError(f"Unsupported generated output type: {path.suffix}")

# # #         report = {
# # #             "run_id": run_id,
# # #             "source_name": name,
# # #             "source_path": str(path),
# # #             "mode": mode,
# # #             **result,
# # #         }
# # #         write_json(run_dir / "report.json", report)
# # #         return report

# # #     def execute_testcase_by_id(self, name: str, testcase_id: str, mode: str = "dry_run") -> dict[str, Any]:
# # #         path = self.generated_dir / name
# # #         if not path.exists() or path.suffix != ".json":
# # #             raise FileNotFoundError(f"JSON generated output not found: {name}")

# # #         data = read_json(path, {})
# # #         testcases = data.get("testcases", [])
# # #         selected = [tc for tc in testcases if tc.get("testcase_id") == testcase_id]
# # #         if not selected:
# # #             raise ValueError(f"Test case not found: {testcase_id}")

# # #         run_id = uuid.uuid4().hex[:12]
# # #         run_dir = self.executions_dir / run_id
# # #         run_dir.mkdir(parents=True, exist_ok=True)

# # #         tmp_json = run_dir / f"{Path(name).stem}_{testcase_id}.json"
# # #         write_json(tmp_json, {"testcases": selected})

# # #         result = self._run_json_bundle(tmp_json, run_dir, mode=mode)

# # #         report = {
# # #             "run_id": run_id,
# # #             "source_name": name,
# # #             "testcase_id": testcase_id,
# # #             "mode": mode,
# # #             **result,
# # #         }
# # #         write_json(run_dir / "report.json", report)
# # #         return report

# # #     def read_execution_report(self, run_id: str) -> dict[str, Any]:
# # #         report_path = self.executions_dir / run_id / "report.json"
# # #         return read_json(report_path, {})

# # #     def _run_pytest_file(self, test_file: Path, run_dir: Path, mode: str) -> dict[str, Any]:
# # #         env = os.environ.copy()
# # #         env["PPAI_EXECUTION_MODE"] = mode

# # #         cmd = [
# # #             sys.executable,
# # #             "-m",
# # #             "pytest",
# # #             str(test_file),
# # #             "-q",
# # #         ]

# # #         proc = subprocess.run(
# # #             cmd,
# # #             capture_output=True,
# # #             text=True,
# # #             cwd=str(Path.cwd()),
# # #             env=env,
# # #         )

# # #         return {
# # #             "execution_type": "pytest_file",
# # #             "exit_code": proc.returncode,
# # #             "stdout": proc.stdout,
# # #             "stderr": proc.stderr,
# # #             "status": "passed" if proc.returncode == 0 else "failed",
# # #         }

# # #     def _run_json_bundle(self, json_file: Path, run_dir: Path, mode: str) -> dict[str, Any]:
# # #         data = read_json(json_file, {})
# # #         testcases = data.get("testcases", [])

# # #         generated_test_file = run_dir / "test_generated_bundle.py"
# # #         generated_test_file.write_text(
# # #             self._build_pytest_from_json(testcases, mode),
# # #             encoding="utf-8",
# # #         )

# # #         return self._run_pytest_file(generated_test_file, run_dir, mode=mode)

# # #     def _build_pytest_from_json(self, testcases: list[dict[str, Any]], mode: str) -> str:
# # #         lines = [
# # #             "import pytest",
# # #             "",
# # #             f"EXECUTION_MODE = {mode!r}",
# # #             "",
# # #         ]

# # #         for idx, tc in enumerate(testcases, start=1):
# # #             testcase_id = tc.get("testcase_id", f"TC_{idx}")
# # #             title = tc.get("title", testcase_id)
# # #             steps = tc.get("steps", [])
# # #             expected = tc.get("expected_results", [])

# # #             fn_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in testcase_id)
# # #             lines.append(f"def test_{fn_name}():")
# # #             lines.append(f"    title = {title!r}")
# # #             lines.append(f"    steps = {steps!r}")
# # #             lines.append(f"    expected = {expected!r}")
# # #             lines.append("    assert isinstance(title, str) and title")
# # #             lines.append("    assert isinstance(steps, list)")
# # #             lines.append("    assert isinstance(expected, list)")
# # #             lines.append("    if EXECUTION_MODE == 'dry_run':")
# # #             lines.append("        assert len(steps) >= 0")
# # #             lines.append("    else:")
# # #             lines.append("        pytest.skip('Live execution mapping not implemented yet')")
# # #             lines.append("")

# # #         return "\n".join(lines)

# # from __future__ import annotations

# # import os
# # import re
# # import subprocess
# # import sys
# # import uuid
# # from pathlib import Path
# # from typing import Any

# # from ppai_test_umbrella.shared.io_utils import read_json, write_json
# # from ppai_test_umbrella.shared.settings import settings


# # class ExecutionService:
# #     def __init__(self) -> None:
# #         self.generated_dir = settings.generated_dir
# #         self.executions_dir = self.generated_dir / "executions"
# #         self.executions_dir.mkdir(parents=True, exist_ok=True)

# #     def list_executable_generated_outputs(self) -> list[dict[str, Any]]:
# #         items: list[dict[str, Any]] = []

# #         for path in sorted(self.generated_dir.glob("*")):
# #             if not path.is_file():
# #                 continue

# #             kind = "unknown"
# #             executable = False
# #             testcase_count = 0

# #             if path.suffix == ".py":
# #                 kind = "python_test"
# #                 executable = True

# #             elif path.suffix == ".json":
# #                 data = read_json(path, {})
# #                 testcases = data.get("testcases", []) if isinstance(data, dict) else []
# #                 if isinstance(testcases, list) and testcases:
# #                     kind = "json_test_bundle"
# #                     executable = True
# #                     testcase_count = len(testcases)

# #             items.append(
# #                 {
# #                     "name": path.name,
# #                     "path": str(path),
# #                     "kind": kind,
# #                     "executable": executable,
# #                     "testcase_count": testcase_count,
# #                 }
# #             )

# #         return items

# #     def execute_generated_output(self, name: str, mode: str = "dry_run") -> dict[str, Any]:
# #         self._validate_mode(mode)

# #         path = self.generated_dir / name
# #         if not path.exists() or not path.is_file():
# #             raise FileNotFoundError(f"Generated output not found: {name}")

# #         run_id = uuid.uuid4().hex[:12]
# #         run_dir = self.executions_dir / run_id
# #         run_dir.mkdir(parents=True, exist_ok=True)

# #         if path.suffix == ".py":
# #             result = self._run_pytest_file(path, run_dir, mode=mode)
# #         elif path.suffix == ".json":
# #             result = self._run_json_bundle(path, run_dir, mode=mode)
# #         else:
# #             raise ValueError(f"Unsupported generated output type: {path.suffix}")

# #         report = {
# #             "run_id": run_id,
# #             "source_name": name,
# #             "source_path": str(path),
# #             "mode": mode,
# #             **result,
# #         }

# #         write_json(run_dir / "report.json", report)
# #         return report

# #     def execute_testcase_by_id(
# #         self,
# #         name: str,
# #         testcase_id: str,
# #         mode: str = "dry_run",
# #     ) -> dict[str, Any]:
# #         self._validate_mode(mode)

# #         path = self.generated_dir / name
# #         if not path.exists() or not path.is_file():
# #             raise FileNotFoundError(f"Generated output not found: {name}")

# #         if path.suffix != ".json":
# #             raise ValueError("execute_testcase_by_id only supports JSON generated bundles")

# #         data = read_json(path, {})
# #         testcases = data.get("testcases", []) if isinstance(data, dict) else []

# #         if not isinstance(testcases, list):
# #             raise ValueError(f"Invalid testcases structure in: {name}")

# #         selected = [tc for tc in testcases if tc.get("testcase_id") == testcase_id]
# #         if not selected:
# #             raise ValueError(f"Test case not found: {testcase_id}")

# #         run_id = uuid.uuid4().hex[:12]
# #         run_dir = self.executions_dir / run_id
# #         run_dir.mkdir(parents=True, exist_ok=True)

# #         subset_json = run_dir / f"{Path(name).stem}_{testcase_id}.json"
# #         write_json(subset_json, {"testcases": selected})

# #         result = self._run_json_bundle(subset_json, run_dir, mode=mode)

# #         report = {
# #             "run_id": run_id,
# #             "source_name": name,
# #             "source_path": str(path),
# #             "testcase_id": testcase_id,
# #             "mode": mode,
# #             **result,
# #         }

# #         write_json(run_dir / "report.json", report)
# #         return report

# #     def read_execution_report(self, run_id: str) -> dict[str, Any]:
# #         report_path = self.executions_dir / run_id / "report.json"
# #         if not report_path.exists():
# #             raise FileNotFoundError(f"Execution report not found for run_id: {run_id}")
# #         return read_json(report_path, {})

# #     def list_execution_reports(self) -> list[str]:
# #         return sorted(
# #             [
# #                 str(p)
# #                 for p in self.executions_dir.glob("*/report.json")
# #                 if p.is_file()
# #             ]
# #         )

# #     def _validate_mode(self, mode: str) -> None:
# #         allowed = {"dry_run", "live"}
# #         if mode not in allowed:
# #             raise ValueError(f"Unsupported mode: {mode}. Allowed values: {sorted(allowed)}")

# #     def _run_json_bundle(self, json_file: Path, run_dir: Path, mode: str) -> dict[str, Any]:
# #         data = read_json(json_file, {})
# #         testcases = data.get("testcases", []) if isinstance(data, dict) else []

# #         if not isinstance(testcases, list) or not testcases:
# #             raise ValueError(f"No testcases found in JSON bundle: {json_file}")

# #         generated_test_file = run_dir / "test_generated_bundle.py"
# #         generated_test_file.write_text(
# #             self._build_pytest_from_json(testcases, mode),
# #             encoding="utf-8",
# #         )

# #         pytest_result = self._run_pytest_file(generated_test_file, run_dir, mode=mode)

# #         return {
# #             "execution_type": "json_test_bundle",
# #             "generated_test_file": str(generated_test_file),
# #             "testcase_count": len(testcases),
# #             **pytest_result,
# #         }

# #     def _run_pytest_file(self, test_file: Path, run_dir: Path, mode: str) -> dict[str, Any]:
# #         env = os.environ.copy()
# #         env["PPAI_EXECUTION_MODE"] = mode
# #         env["PYTHONUTF8"] = "1"

# #         cmd = [
# #             sys.executable,
# #             "-m",
# #             "pytest",
# #             str(test_file),
# #             "-q",
# #         ]

# #         proc = subprocess.run(
# #             cmd,
# #             capture_output=True,
# #             text=True,
# #             cwd=str(Path.cwd()),
# #             env=env,
# #         )

# #         stdout_path = run_dir / "stdout.txt"
# #         stderr_path = run_dir / "stderr.txt"
# #         stdout_path.write_text(proc.stdout or "", encoding="utf-8")
# #         stderr_path.write_text(proc.stderr or "", encoding="utf-8")

# #         status = "passed" if proc.returncode == 0 else "failed"

# #         return {
# #             "execution_type": "pytest_file",
# #             "executed_file": str(test_file),
# #             "exit_code": proc.returncode,
# #             "status": status,
# #             "stdout": proc.stdout,
# #             "stderr": proc.stderr,
# #             "stdout_path": str(stdout_path),
# #             "stderr_path": str(stderr_path),
# #         }

# #     def _build_pytest_from_json(self, testcases: list[dict[str, Any]], mode: str) -> str:
# #         lines: list[str] = [
# #             "import pytest",
# #             "",
# #             f"EXECUTION_MODE = {mode!r}",
# #             "",
# #         ]

# #         for idx, tc in enumerate(testcases, start=1):
# #             testcase_id = str(tc.get("testcase_id", f"TC_{idx}"))
# #             title = str(tc.get("title", testcase_id))
# #             preconditions = tc.get("preconditions", [])
# #             steps = tc.get("steps", [])
# #             expected = tc.get("expected_results", [])
# #             automation_type = tc.get("automation_type")

# #             fn_name = self._safe_py_name(testcase_id)

# #             lines.append(f"def test_{fn_name}():")
# #             lines.append(f"    testcase_id = {testcase_id!r}")
# #             lines.append(f"    title = {title!r}")
# #             lines.append(f"    preconditions = {preconditions!r}")
# #             lines.append(f"    steps = {steps!r}")
# #             lines.append(f"    expected = {expected!r}")
# #             lines.append(f"    automation_type = {automation_type!r}")
# #             lines.append("")
# #             lines.append("    assert isinstance(testcase_id, str) and testcase_id.strip()")
# #             lines.append("    assert isinstance(title, str) and title.strip()")
# #             lines.append("    assert isinstance(preconditions, list)")
# #             lines.append("    assert isinstance(steps, list)")
# #             lines.append("    assert isinstance(expected, list)")
# #             lines.append("")
# #             lines.append("    if EXECUTION_MODE == 'dry_run':")
# #             lines.append("        # Dry run validates structure and completeness only.")
# #             lines.append("        assert len(steps) >= 0")
# #             lines.append("    else:")
# #             lines.append("        # Live execution mapping can be extended later per automation_type.")
# #             lines.append("        pytest.skip('Live execution mapping is not implemented yet')")
# #             lines.append("")

# #         return "\n".join(lines)

# #     def _safe_py_name(self, value: str) -> str:
# #         cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", value.strip().lower())
# #         cleaned = re.sub(r"_+", "_", cleaned).strip("_")
# #         if not cleaned:
# #             cleaned = "generated_test"
# #         if cleaned[0].isdigit():
# #             cleaned = f"tc_{cleaned}"
# #         return cleaned

# from __future__ import annotations

# import os
# import re
# import traceback
# import uuid
# from pathlib import Path
# from typing import Any

# import httpx

# from ppai_test_umbrella.shared.io_utils import read_json, write_json
# from ppai_test_umbrella.shared.settings import settings


# class ExecutionService:
#     def __init__(self) -> None:
#         self.generated_dir = settings.generated_dir
#         self.executions_dir = self.generated_dir / "executions"
#         self.executions_dir.mkdir(parents=True, exist_ok=True)

#     def list_executable_generated_outputs(self) -> list[dict[str, Any]]:
#         items: list[dict[str, Any]] = []

#         for path in sorted(self.generated_dir.glob("*")):
#             if not path.is_file():
#                 continue

#             kind = "unknown"
#             executable = False
#             testcase_count = 0

#             if path.suffix == ".py":
#                 kind = "python_test"
#                 executable = True
#             elif path.suffix == ".json":
#                 data = read_json(path, {})
#                 testcases = data.get("testcases", []) if isinstance(data, dict) else []
#                 if isinstance(testcases, list) and testcases:
#                     kind = "json_test_bundle"
#                     executable = True
#                     testcase_count = len(testcases)

#             items.append(
#                 {
#                     "name": path.name,
#                     "path": str(path),
#                     "kind": kind,
#                     "executable": executable,
#                     "testcase_count": testcase_count,
#                 }
#             )

#         return items

#     def execute_generated_output(self, name: str, mode: str = "dry_run") -> dict[str, Any]:
#         self._validate_mode(mode)

#         path = self.generated_dir / name
#         if not path.exists() or not path.is_file():
#             raise FileNotFoundError(f"Generated output not found: {name}")

#         if path.suffix == ".json":
#             return self._execute_json_bundle(path, mode)

#         raise ValueError(f"Unsupported generated output type for real execution: {path.suffix}")

#     def execute_testcase_by_id(
#         self,
#         name: str,
#         testcase_id: str,
#         mode: str = "dry_run",
#     ) -> dict[str, Any]:
#         self._validate_mode(mode)

#         path = self.generated_dir / name
#         if not path.exists() or not path.is_file():
#             raise FileNotFoundError(f"Generated output not found: {name}")

#         if path.suffix != ".json":
#             raise ValueError("execute_testcase_by_id only supports JSON generated bundles")

#         data = read_json(path, {})
#         testcases = data.get("testcases", []) if isinstance(data, dict) else []

#         if not isinstance(testcases, list):
#             raise ValueError(f"Invalid testcases structure in: {name}")

#         selected = [tc for tc in testcases if tc.get("testcase_id") == testcase_id]
#         if not selected:
#             raise ValueError(f"Test case not found: {testcase_id}")

#         run_id = self._new_run_id()
#         run_dir = self._prepare_run_dir(run_id)

#         report = self._execute_testcases(
#             source_name=name,
#             testcases=selected,
#             mode=mode,
#             run_id=run_id,
#             run_dir=run_dir,
#         )
#         write_json(run_dir / "report.json", report)
#         return report

#     def read_execution_report(self, run_id: str) -> dict[str, Any]:
#         report_path = self.executions_dir / run_id / "report.json"
#         if not report_path.exists():
#             raise FileNotFoundError(f"Execution report not found for run_id: {run_id}")
#         return read_json(report_path, {})

#     def list_execution_reports(self) -> list[str]:
#         return sorted(str(p) for p in self.executions_dir.glob("*/report.json") if p.is_file())

#     def _execute_json_bundle(self, path: Path, mode: str) -> dict[str, Any]:
#         data = read_json(path, {})
#         testcases = data.get("testcases", []) if isinstance(data, dict) else []

#         if not isinstance(testcases, list) or not testcases:
#             raise ValueError(f"No testcases found in JSON bundle: {path}")

#         run_id = self._new_run_id()
#         run_dir = self._prepare_run_dir(run_id)

#         report = self._execute_testcases(
#             source_name=path.name,
#             testcases=testcases,
#             mode=mode,
#             run_id=run_id,
#             run_dir=run_dir,
#         )
#         write_json(run_dir / "report.json", report)
#         return report

#     def _execute_testcases(
#         self,
#         source_name: str,
#         testcases: list[dict[str, Any]],
#         mode: str,
#         run_id: str,
#         run_dir: Path,
#     ) -> dict[str, Any]:
#         results = []
#         passed = 0
#         failed = 0
#         skipped = 0

#         for tc in testcases:
#             try:
#                 tc_result = self._execute_single_testcase(tc, mode)
#             except Exception as exc:
#                 tc_result = {
#                     "testcase_id": tc.get("testcase_id"),
#                     "title": tc.get("title"),
#                     "status": "failed",
#                     "error": str(exc),
#                     "traceback": traceback.format_exc(),
#                     "steps": [],
#                 }

#             results.append(tc_result)

#             if tc_result["status"] == "passed":
#                 passed += 1
#             elif tc_result["status"] == "skipped":
#                 skipped += 1
#             else:
#                 failed += 1

#         overall = "passed" if failed == 0 else "failed"

#         return {
#             "run_id": run_id,
#             "source_name": source_name,
#             "mode": mode,
#             "status": overall,
#             "summary": {
#                 "total": len(testcases),
#                 "passed": passed,
#                 "failed": failed,
#                 "skipped": skipped,
#             },
#             "results": results,
#         }

#     def _execute_single_testcase(self, tc: dict[str, Any], mode: str) -> dict[str, Any]:
#         testcase_id = tc.get("testcase_id")
#         title = tc.get("title")
#         automation_type = tc.get("automation_type")
#         action_steps = tc.get("action_steps", []) or []

#         if not action_steps:
#             return {
#                 "testcase_id": testcase_id,
#                 "title": title,
#                 "automation_type": automation_type,
#                 "status": "skipped" if mode == "live" else "passed",
#                 "reason": "No action_steps found; cannot do real execution.",
#                 "steps": [],
#             }

#         if mode == "dry_run":
#             return self._dry_run_testcase(tc)

#         if automation_type == "playwright_pytest":
#             return self._execute_playwright_testcase(tc)
#         if automation_type == "pytest_httpx":
#             return self._execute_api_testcase(tc)

#         return {
#             "testcase_id": testcase_id,
#             "title": title,
#             "automation_type": automation_type,
#             "status": "skipped",
#             "reason": f"Unsupported automation_type for live execution: {automation_type}",
#             "steps": [],
#         }

#     def _dry_run_testcase(self, tc: dict[str, Any]) -> dict[str, Any]:
#         action_steps = tc.get("action_steps", []) or []
#         return {
#             "testcase_id": tc.get("testcase_id"),
#             "title": tc.get("title"),
#             "automation_type": tc.get("automation_type"),
#             "status": "passed",
#             "reason": "Validated testcase structure only.",
#             "steps": [
#                 {
#                     "index": idx,
#                     "action": step.get("action"),
#                     "status": "validated",
#                 }
#                 for idx, step in enumerate(action_steps, start=1)
#             ],
#         }

#     def _execute_playwright_testcase(self, tc: dict[str, Any]) -> dict[str, Any]:
#         from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

#         resolved_steps = []
#         action_steps = tc.get("action_steps", [])

#         base_url = os.getenv("PPAI_BASE_URL", "").rstrip("/")
#         headless = os.getenv("PPAI_HEADLESS", "false").lower() == "true"

#         if not base_url:
#             raise ValueError("PPAI_BASE_URL is required for live Playwright execution")

#         env_map = {
#             "{{BASE_URL}}": base_url,
#             "{{BASE_URL_PATH_HINT}}": os.getenv("PPAI_BASE_URL_PATH_HINT", "/"),
#             "{{LOGIN_USERNAME_SELECTOR}}": os.getenv("PPAI_LOGIN_USERNAME_SELECTOR", "input[name='username']"),
#             "{{LOGIN_PASSWORD_SELECTOR}}": os.getenv("PPAI_LOGIN_PASSWORD_SELECTOR", "input[name='password']"),
#             "{{LOGIN_SUBMIT_SELECTOR}}": os.getenv("PPAI_LOGIN_SUBMIT_SELECTOR", "button[type='submit']"),
#             "{{LOGIN_ERROR_SELECTOR}}": os.getenv("PPAI_LOGIN_ERROR_SELECTOR", ".error, .alert, .invalid-feedback"),
#             "{{LOGIN_ERROR_TEXT}}": os.getenv("PPAI_LOGIN_ERROR_TEXT", "invalid"),
#             "{{LOGIN_SUCCESS_URL_CONTAINS}}": os.getenv("PPAI_LOGIN_SUCCESS_URL_CONTAINS", "dashboard"),
#         }

#         username_value = os.getenv("PPAI_LOGIN_USERNAME", "testuser")
#         password_value = os.getenv("PPAI_LOGIN_PASSWORD", "testpass")
#         wrong_password_value = os.getenv("PPAI_LOGIN_WRONG_PASSWORD", "wrongpass")

#         def resolve_value(value: Any) -> Any:
#             if not isinstance(value, str):
#                 return value
#             result = value
#             for key, replacement in env_map.items():
#                 result = result.replace(key, replacement)
#             if result == "valid_user":
#                 return username_value
#             if result == "valid_pass":
#                 return password_value
#             if result == "wrong_pass":
#                 return wrong_password_value
#             return result

#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=headless)
#             page = browser.new_page()

#             try:
#                 for idx, step in enumerate(action_steps, start=1):
#                     action = step.get("action")
#                     selector = resolve_value(step.get("selector"))
#                     value = resolve_value(step.get("value"))
#                     url = resolve_value(step.get("url"))
#                     expected = resolve_value(step.get("expected"))
#                     timeout_ms = int(step.get("timeout_ms", 10000))

#                     step_result = {
#                         "index": idx,
#                         "action": action,
#                         "status": "passed",
#                     }

#                     try:
#                         if action == "goto":
#                             page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

#                         elif action == "fill":
#                             page.locator(selector).first.fill("" if value is None else str(value), timeout=timeout_ms)

#                         elif action == "click":
#                             page.locator(selector).first.click(timeout=timeout_ms)

#                         elif action == "wait":
#                             page.wait_for_timeout(timeout_ms)

#                         elif action == "assert_url_contains":
#                             current = page.url
#                             if expected not in current:
#                                 raise AssertionError(f"Expected URL to contain '{expected}', got '{current}'")

#                         elif action == "assert_text_visible":
#                             locator = page.locator(selector).first
#                             locator.wait_for(timeout=timeout_ms)
#                             text = locator.inner_text(timeout=timeout_ms)
#                             if expected and expected.lower() not in text.lower():
#                                 raise AssertionError(f"Expected '{expected}' in '{text}'")

#                         else:
#                             raise ValueError(f"Unsupported Playwright action: {action}")

#                     except (AssertionError, PlaywrightTimeoutError, Exception) as exc:
#                         step_result["status"] = "failed"
#                         step_result["error"] = str(exc)
#                         resolved_steps.append(step_result)
#                         raise

#                     resolved_steps.append(step_result)

#                 return {
#                     "testcase_id": tc.get("testcase_id"),
#                     "title": tc.get("title"),
#                     "automation_type": tc.get("automation_type"),
#                     "status": "passed",
#                     "steps": resolved_steps,
#                 }

#             finally:
#                 browser.close()

#     def _execute_api_testcase(self, tc: dict[str, Any]) -> dict[str, Any]:
#         action_steps = tc.get("action_steps", [])
#         resolved_steps = []
#         last_response = None

#         api_base_url = os.getenv("PPAI_API_BASE_URL", "").rstrip("/")
#         if not api_base_url:
#             raise ValueError("PPAI_API_BASE_URL is required for live API execution")

#         with httpx.Client(timeout=30.0, verify=False) as client:
#             for idx, step in enumerate(action_steps, start=1):
#                 action = step.get("action")
#                 expected = step.get("expected")
#                 meta = step.get("meta", {}) or {}

#                 step_result = {
#                     "index": idx,
#                     "action": action,
#                     "status": "passed",
#                 }

#                 try:
#                     if action == "api_request":
#                         method = str(meta.get("method", "GET")).upper()
#                         url = str(meta.get("url", ""))
#                         headers = meta.get("headers", {}) or {}
#                         json_body = meta.get("json", None)

#                         url = url.replace("{{API_BASE_URL}}", api_base_url)

#                         last_response = client.request(
#                             method=method,
#                             url=url,
#                             headers=headers,
#                             json=json_body,
#                         )

#                         step_result["response_status_code"] = last_response.status_code
#                         step_result["response_text_preview"] = last_response.text[:500]

#                     elif action == "assert_status_code":
#                         if last_response is None:
#                             raise AssertionError("No previous response found")
#                         expected_code = int(expected)
#                         if last_response.status_code != expected_code:
#                             raise AssertionError(
#                                 f"Expected status {expected_code}, got {last_response.status_code}"
#                             )

#                     else:
#                         raise ValueError(f"Unsupported API action: {action}")

#                 except Exception as exc:
#                     step_result["status"] = "failed"
#                     step_result["error"] = str(exc)
#                     resolved_steps.append(step_result)
#                     raise

#                 resolved_steps.append(step_result)

#         return {
#             "testcase_id": tc.get("testcase_id"),
#             "title": tc.get("title"),
#             "automation_type": tc.get("automation_type"),
#             "status": "passed",
#             "steps": resolved_steps,
#         }

#     def _validate_mode(self, mode: str) -> None:
#         allowed = {"dry_run", "live"}
#         if mode not in allowed:
#             raise ValueError(f"Unsupported mode: {mode}. Allowed values: {sorted(allowed)}")

#     def _new_run_id(self) -> str:
#         return uuid.uuid4().hex[:12]

#     def _prepare_run_dir(self, run_id: str) -> Path:
#         run_dir = self.executions_dir / run_id
#         run_dir.mkdir(parents=True, exist_ok=True)
#         return run_dir

#     def _safe_py_name(self, value: str) -> str:
#         cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", value.strip().lower())
#         cleaned = re.sub(r"_+", "_", cleaned).strip("_")
#         if not cleaned:
#             cleaned = "generated_test"
#         if cleaned[0].isdigit():
#             cleaned = f"tc_{cleaned}"
#         return cleaned

from __future__ import annotations

import re
import traceback
import uuid
from pathlib import Path
from typing import Any

import httpx

from ppai_test_umbrella.shared.io_utils import read_json, read_yaml, write_json
from ppai_test_umbrella.shared.settings import settings


class ExecutionService:
    def __init__(self) -> None:
        self.generated_dir = settings.generated_dir
        self.executions_dir = self.generated_dir / "executions"
        self.executions_dir.mkdir(parents=True, exist_ok=True)

    def list_executable_generated_outputs(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for path in sorted(self.generated_dir.glob("*")):
            if not path.is_file():
                continue

            kind = "unknown"
            executable = False
            testcase_count = 0

            if path.suffix == ".py":
                kind = "python_test"
                executable = True
            elif path.suffix == ".json":
                data = read_json(path, {})
                testcases = data.get("testcases", []) if isinstance(data, dict) else []
                if isinstance(testcases, list) and testcases:
                    kind = "json_test_bundle"
                    executable = True
                    testcase_count = len(testcases)

            items.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "kind": kind,
                    "executable": executable,
                    "testcase_count": testcase_count,
                }
            )

        return items

    def execute_generated_output(
        self,
        name: str,
        mode: str = "dry_run",
        config_path: str | None = None,
    ) -> dict[str, Any]:
        self._validate_mode(mode)

        path = self.generated_dir / name
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Generated output not found: {name}")

        if path.suffix == ".json":
            return self._execute_json_bundle(path, mode, config_path=config_path)

        raise ValueError(f"Unsupported generated output type for real execution: {path.suffix}")

    def execute_testcase_by_id(
        self,
        name: str,
        testcase_id: str,
        mode: str = "dry_run",
        config_path: str | None = None,
    ) -> dict[str, Any]:
        self._validate_mode(mode)

        path = self.generated_dir / name
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Generated output not found: {name}")

        if path.suffix != ".json":
            raise ValueError("execute_testcase_by_id only supports JSON generated bundles")

        data = read_json(path, {})
        testcases = data.get("testcases", []) if isinstance(data, dict) else []

        if not isinstance(testcases, list):
            raise ValueError(f"Invalid testcases structure in: {name}")

        selected = [tc for tc in testcases if tc.get("testcase_id") == testcase_id]
        if not selected:
            raise ValueError(f"Test case not found: {testcase_id}")

        run_id = self._new_run_id()
        run_dir = self._prepare_run_dir(run_id)
        config = self._load_config(config_path)

        report = self._execute_testcases(
            source_name=name,
            testcases=selected,
            mode=mode,
            run_id=run_id,
            run_dir=run_dir,
            config=config,
        )
        write_json(run_dir / "report.json", report)
        return report

    def read_execution_report(self, run_id: str) -> dict[str, Any]:
        report_path = self.executions_dir / run_id / "report.json"
        if not report_path.exists():
            raise FileNotFoundError(f"Execution report not found for run_id: {run_id}")
        return read_json(report_path, {})

    def list_execution_reports(self) -> list[str]:
        return sorted(str(p) for p in self.executions_dir.glob("*/report.json") if p.is_file())

    def _execute_json_bundle(
        self,
        path: Path,
        mode: str,
        config_path: str | None = None,
    ) -> dict[str, Any]:
        data = read_json(path, {})
        testcases = data.get("testcases", []) if isinstance(data, dict) else []

        if not isinstance(testcases, list) or not testcases:
            raise ValueError(f"No testcases found in JSON bundle: {path}")

        run_id = self._new_run_id()
        run_dir = self._prepare_run_dir(run_id)
        config = self._load_config(config_path)

        report = self._execute_testcases(
            source_name=path.name,
            testcases=testcases,
            mode=mode,
            run_id=run_id,
            run_dir=run_dir,
            config=config,
        )
        write_json(run_dir / "report.json", report)
        return report

    def _load_config(self, config_path: str | None) -> dict[str, Any]:
        if not config_path:
            return {}
        data = read_yaml(config_path, default={})
        if not isinstance(data, dict):
            raise ValueError("Execution YAML config must be a mapping/object")
        return data

    def _execute_testcases(
        self,
        source_name: str,
        testcases: list[dict[str, Any]],
        mode: str,
        run_id: str,
        run_dir: Path,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        results = []
        passed = 0
        failed = 0
        skipped = 0

        for tc in testcases:
            try:
                tc_result = self._execute_single_testcase(tc, mode, config)
            except Exception as exc:
                tc_result = {
                    "testcase_id": tc.get("testcase_id"),
                    "title": tc.get("title"),
                    "status": "failed",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "steps": [],
                }

            results.append(tc_result)

            if tc_result["status"] == "passed":
                passed += 1
            elif tc_result["status"] == "skipped":
                skipped += 1
            else:
                failed += 1

        overall = "passed" if failed == 0 else "failed"

        return {
            "run_id": run_id,
            "source_name": source_name,
            "mode": mode,
            "status": overall,
            "summary": {
                "total": len(testcases),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
            "results": results,
        }

    def _execute_single_testcase(
        self,
        tc: dict[str, Any],
        mode: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        testcase_id = tc.get("testcase_id")
        title = tc.get("title")
        automation_type = tc.get("automation_type")
        action_steps = tc.get("action_steps", []) or []

        if not action_steps:
            return {
                "testcase_id": testcase_id,
                "title": title,
                "automation_type": automation_type,
                "status": "skipped" if mode == "live" else "passed",
                "reason": "No action_steps found; cannot do real execution.",
                "steps": [],
            }

        if mode == "dry_run":
            return self._dry_run_testcase(tc)

        if automation_type == "playwright_pytest":
            return self._execute_playwright_testcase(tc, config)
        if automation_type == "pytest_httpx":
            return self._execute_api_testcase(tc, config)

        return {
            "testcase_id": testcase_id,
            "title": title,
            "automation_type": automation_type,
            "status": "skipped",
            "reason": f"Unsupported automation_type for live execution: {automation_type}",
            "steps": [],
        }

    def _dry_run_testcase(self, tc: dict[str, Any]) -> dict[str, Any]:
        action_steps = tc.get("action_steps", []) or []
        return {
            "testcase_id": tc.get("testcase_id"),
            "title": tc.get("title"),
            "automation_type": tc.get("automation_type"),
            "status": "passed",
            "reason": "Validated testcase structure only.",
            "steps": [
                {"index": idx, "action": step.get("action"), "status": "validated"}
                for idx, step in enumerate(action_steps, start=1)
            ],
        }

    def _execute_playwright_testcase(self, tc: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

        resolved_steps = []
        action_steps = tc.get("action_steps", [])

        app_cfg = config.get("app", {})
        auth_cfg = config.get("auth", {})
        selectors_cfg = config.get("selectors", {})
        assertions_cfg = config.get("assertions", {})

        base_url = str(app_cfg.get("base_url", "")).rstrip("/")
        headless = bool(app_cfg.get("headless", False))

        if not base_url:
            raise ValueError("app.base_url is required in YAML for live Playwright execution")

        env_map = {
            "{{BASE_URL}}": base_url,
            "{{BASE_URL_PATH_HINT}}": str(assertions_cfg.get("base_url_path_hint", "/")),
            "{{LOGIN_USERNAME_SELECTOR}}": str(selectors_cfg.get("login_username", "input[name='username']")),
            "{{LOGIN_PASSWORD_SELECTOR}}": str(selectors_cfg.get("login_password", "input[name='password']")),
            "{{LOGIN_SUBMIT_SELECTOR}}": str(selectors_cfg.get("login_submit", "button[type='submit']")),
            "{{LOGIN_ERROR_SELECTOR}}": str(selectors_cfg.get("login_error", ".error, .alert, .invalid-feedback")),
            "{{LOGIN_ERROR_TEXT}}": str(assertions_cfg.get("login_error_text", "invalid")),
            "{{LOGIN_SUCCESS_URL_CONTAINS}}": str(assertions_cfg.get("login_success_url_contains", "dashboard")),
        }

        username_value = str(auth_cfg.get("username", "testuser"))
        password_value = str(auth_cfg.get("password", "testpass"))
        wrong_password_value = str(auth_cfg.get("wrong_password", "wrongpass"))

        def resolve_value(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            result = value
            for key, replacement in env_map.items():
                result = result.replace(key, replacement)
            if result == "valid_user":
                return username_value
            if result == "valid_pass":
                return password_value
            if result == "wrong_pass":
                return wrong_password_value
            return result

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            try:
                for idx, step in enumerate(action_steps, start=1):
                    action = step.get("action")
                    selector = resolve_value(step.get("selector"))
                    value = resolve_value(step.get("value"))
                    url = resolve_value(step.get("url"))
                    expected = resolve_value(step.get("expected"))
                    timeout_ms = int(step.get("timeout_ms", 10000))

                    step_result = {"index": idx, "action": action, "status": "passed"}

                    try:
                        if action == "goto":
                            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                        elif action == "fill":
                            page.locator(selector).first.fill("" if value is None else str(value), timeout=timeout_ms)

                        elif action == "click":
                            page.locator(selector).first.click(timeout=timeout_ms)

                        elif action == "wait":
                            page.wait_for_timeout(timeout_ms)

                        elif action == "assert_url_contains":
                            current = page.url
                            if expected not in current:
                                raise AssertionError(f"Expected URL to contain '{expected}', got '{current}'")

                        elif action == "assert_text_visible":
                            locator = page.locator(selector).first
                            locator.wait_for(timeout=timeout_ms)
                            text = locator.inner_text(timeout=timeout_ms)
                            if expected and expected.lower() not in text.lower():
                                raise AssertionError(f"Expected '{expected}' in '{text}'")

                        else:
                            raise ValueError(f"Unsupported Playwright action: {action}")

                    except (AssertionError, PlaywrightTimeoutError, Exception) as exc:
                        step_result["status"] = "failed"
                        step_result["error"] = str(exc)
                        resolved_steps.append(step_result)
                        raise

                    resolved_steps.append(step_result)

                return {
                    "testcase_id": tc.get("testcase_id"),
                    "title": tc.get("title"),
                    "automation_type": tc.get("automation_type"),
                    "status": "passed",
                    "steps": resolved_steps,
                }

            finally:
                browser.close()

    def _execute_api_testcase(self, tc: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        action_steps = tc.get("action_steps", [])
        resolved_steps = []
        last_response = None

        api_cfg = config.get("api", {})
        api_base_url = str(api_cfg.get("base_url", "")).rstrip("/")
        default_headers = api_cfg.get("headers", {}) or {}

        if not api_base_url:
            raise ValueError("api.base_url is required in YAML for live API execution")

        with httpx.Client(timeout=30.0, verify=False) as client:
            for idx, step in enumerate(action_steps, start=1):
                action = step.get("action")
                expected = step.get("expected")
                meta = step.get("meta", {}) or {}

                step_result = {"index": idx, "action": action, "status": "passed"}

                try:
                    if action == "api_request":
                        method = str(meta.get("method", "GET")).upper()
                        url = str(meta.get("url", "")).replace("{{API_BASE_URL}}", api_base_url)
                        headers = {**default_headers, **(meta.get("headers", {}) or {})}
                        json_body = meta.get("json", None)

                        last_response = client.request(
                            method=method,
                            url=url,
                            headers=headers,
                            json=json_body,
                        )

                        step_result["response_status_code"] = last_response.status_code
                        step_result["response_text_preview"] = last_response.text[:500]

                    elif action == "assert_status_code":
                        if last_response is None:
                            raise AssertionError("No previous response found")
                        expected_code = int(expected)
                        if last_response.status_code != expected_code:
                            raise AssertionError(
                                f"Expected status {expected_code}, got {last_response.status_code}"
                            )

                    else:
                        raise ValueError(f"Unsupported API action: {action}")

                except Exception as exc:
                    step_result["status"] = "failed"
                    step_result["error"] = str(exc)
                    resolved_steps.append(step_result)
                    raise

                resolved_steps.append(step_result)

        return {
            "testcase_id": tc.get("testcase_id"),
            "title": tc.get("title"),
            "automation_type": tc.get("automation_type"),
            "status": "passed",
            "steps": resolved_steps,
        }

    def _validate_mode(self, mode: str) -> None:
        allowed = {"dry_run", "live"}
        if mode not in allowed:
            raise ValueError(f"Unsupported mode: {mode}. Allowed values: {sorted(allowed)}")

    def _new_run_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _prepare_run_dir(self, run_id: str) -> Path:
        run_dir = self.executions_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _safe_py_name(self, value: str) -> str:
        cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", value.strip().lower())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = "generated_test"
        if cleaned[0].isdigit():
            cleaned = f"tc_{cleaned}"
        return cleaned