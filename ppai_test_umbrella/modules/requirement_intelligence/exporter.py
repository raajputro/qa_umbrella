from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any


def export_test_cases_txt(output: Any, file_path: str | Path) -> Path:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_format_output(output), encoding="utf-8")
    return path


def export_test_cases_json(output: Any, file_path: str | Path) -> Path:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def export_test_cases_pdf(output: Any, file_path: str | Path) -> Path:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        raise ImportError(
            "Please install reportlab to export PDF files: python -m pip install reportlab"
        ) from None

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    margin = 48
    line_height = 12
    y = height - margin

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y, "Generated Test Cases")
    y -= line_height * 2
    pdf.setFont("Helvetica", 10)

    for raw_line in _format_output(output).splitlines():
        wrapped_lines = textwrap.wrap(raw_line, width=95) or [""]
        for line in wrapped_lines:
            if y <= margin:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - margin
            pdf.drawString(margin, y, line)
            y -= line_height

    pdf.save()
    return path


def _format_output(output: Any) -> str:
    if isinstance(output, dict):
        return _format_dict_output(output)
    return str(output)


def _format_dict_output(output: dict[str, Any]) -> str:
    lines = []

    feature_id = output.get("feature_id")
    feature_name = output.get("feature_name")
    scenario_count = output.get("possible_test_scenario_count")

    if feature_id:
        lines.append(f"Feature ID: {feature_id}")
    if feature_name:
        lines.append(f"Feature Name: {feature_name}")
    if scenario_count is not None:
        lines.append(f"Possible Test Scenario Count: {scenario_count}")

    test_cases = output.get("test_cases")
    if isinstance(test_cases, list):
        if lines:
            lines.append("")
        lines.append("Test Cases")
        lines.append("=" * 10)
        for index, test_case in enumerate(test_cases, start=1):
            lines.extend(_format_test_case(index, test_case))
        return "\n".join(lines).strip() + "\n"

    return json.dumps(output, indent=2, ensure_ascii=False) + "\n"


def _format_test_case(index: int, test_case: Any) -> list[str]:
    if not isinstance(test_case, dict):
        return ["", f"{index}. {test_case}"]

    case_id = test_case.get("test_case_id", f"TC-{index:03d}")
    title = test_case.get("title", "Untitled test case")
    lines = ["", f"{case_id}: {title}"]

    for key, label in [
        ("type", "Type"),
        ("preconditions", "Preconditions"),
        ("steps", "Steps"),
        ("expected_result", "Expected Result"),
    ]:
        value = test_case.get(key)
        if value is None:
            continue
        lines.extend(_format_field(label, value))

    return lines


def _format_field(label: str, value: Any) -> list[str]:
    if isinstance(value, list):
        lines = [f"{label}:"]
        lines.extend(f"  - {item}" for item in value)
        return lines
    return [f"{label}: {value}"]
