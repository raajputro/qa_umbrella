"""
Strict prompt templates for evidence-based SRS testcase generation.

Main policy:
- Generate only from explicit SRS evidence.
- Do not force minimum testcase count.
- Every testcase must cite an exact evidence quote.
"""
from __future__ import annotations

from typing import List

SYSTEM_PROMPT = (
    "Act as a senior SQA engineer. Generate concise, non-duplicated, evidence-backed "
    "test cases strictly from the provided SRS. Do not invent constraints, UI behavior, "
    "roles, limits, error messages, statuses, or workflows that are not explicitly stated."
)


def build_generation_rules(feature_id: str, feature_name: str) -> str:
    return f"""
TASK: Generate SRS-grounded test cases for this feature only.

HARD RULES:
1. Generate EVERY unique test cases required to fully cover the SRS for this feature. 
2. Extract EVERY possible valid test case supported by the evidence. 
3. Do not stop until all evidence has been converted into test cases. Produce AS MANY TEST CASES POSSIBLE in a single response.
4. Each test case must map to an explicit SRS statement or rule.
5. Every test case MUST include one exact short evidence quote copied from the SRS text.
6. Do NOT create boundary cases unless the SRS gives an explicit boundary, limit, date rule, numeric rule, status rule, or validation rule.
7. Do NOT create role/permission cases unless roles or permissions are explicitly stated.
8. Do NOT invent field length, date format, max hours, duplicate behavior, sorting, filtering, approval flow, audit log, toast messages, API behavior, or exact error messages.
9. If a possible scenario needs an assumption, do NOT include it in test_cases.
10. Titles must start with only: "Verify that", "Ensure that", or "Validate that".
11. Steps must be just concrete user actions.
12. Expected results must describe only the behavior proven by the evidence quote.
13. Remove duplicates and near-duplicates.
14. Return strictly valid JSON only. Do not wrap in markdown.

Return JSON in this exact format:
{{
  "feature_id": "{feature_id}",
  "feature_name": "{feature_name}",
  "no_new_test_cases": false,
  "test_cases": [
    {{
      "test_case_id": "TC-001",
      "title": "Verify that ...",
      "type": "positive | negative | boundary | edge",
      "source_requirement_ids": ["REQ-001"],
      "evidence_quote": "Exact quote copied from SRS",
      "assumption_flag": false,
      "preconditions": ["precondition 1"],
      "steps": [
        "1. first user action",
        "2. second user action"
      ],
      "expected_result": [
        "The system should ..."
      ]
    }}
  ]
}}
""".strip()


def build_iterative_instruction(latest_titles: List[str], covered_summary: str) -> str:
    titles_block = "\n".join(f"  {i + 1}. {t}" for i, t in enumerate(latest_titles))
    summary_block = f"\n{covered_summary}\n" if covered_summary else ""

    return f"""
---
ITERATIVE GENERATION INSTRUCTION:
The following test cases already exist. Do not duplicate or rephrase them:

{titles_block}
{summary_block}
Your task now:
1. Generate ONLY genuinely missing test cases that are explicitly supported by SRS evidence.
2. If an existing test case broadly covers a scenario, do NOT generate narrower test cases for the same scenario. Instead, generate entirely distinct functional cases.
3. If all explicit SRS behavior is already covered, return an empty test_cases array and set "no_new_test_cases" to true.
4. Every new testcase must include evidence_quote and assumption_flag=false.
Return JSON in the same format.
""".strip()

def build_continuation_instruction(partial_output: str) -> str:
    return (
        "Your previous response was truncated. Continue and complete the same JSON object. "
        "Return only valid JSON. Do not add markdown.\n\n"
        f"Partial response:\n{partial_output}"
    )
