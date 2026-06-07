"""
Centralized prompt templates for test case generation.

All prompts used by the pipeline are defined here. Other modules import
from this file — no prompt text should be hardcoded elsewhere.

PROMPT FLOW:
  1. SYSTEM_PROMPT → sent as the "system" role message to the LLM
  2. build_generation_rules() → sent as the "user" role message (the main instruction)
  3. build_iterative_instruction() → appended to user message on subsequent runs
  4. build_retry_instruction() → appended when model generates fewer than minimum TCs
  5. build_continuation_instruction() → used when model output is truncated
"""
from __future__ import annotations

from typing import List


# ------------------------------------------------------------------
# System prompt — sets the LLM role
# ------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Act as a senior SQA engineer. Generate all possible positive, negative, "
    "boundary, and edge test cases strictly from the provided requirements."
)


# ------------------------------------------------------------------
# Main generation rules — the actual instruction the model follows
# ------------------------------------------------------------------

def build_generation_rules(feature_id: str, feature_name: str) -> str:
    return f"""
TASK: Generate exhaustive positive, negative, boundary, and edge test cases covering:
- positive/negative validation of each requirement & acceptance criteria
- UI fields (valid, invalid, empty, min/max limits)
- Role-based access, status transitions, and error handling scenarios

RULES:
1. Titles must start with: "Verify that", "Ensure that", "Validate that", "Confirm that", or "Assert that".
2. Expected results must use "should" statements and strictly reflect SRS rules.
3. Steps must be numbered, concrete user actions covering the full testcase flow.
4. No duplicates.
5. Strict Adherence: Do not invent or assume constraints unless explicitly stated in the SRS. If it's not forbidden, it is allowed.
6. Logical Domain Limits: Expected results must respect logical and physical constraints implied by the domain. Treat physically impossible inputs as invalid and expect them to be blocked/fail.
7. Return strictly valid JSON. Do not wrap in markdown. Include "no_new_test_cases": false.

Return JSON in this format:
{{
  "feature_id": "{feature_id}",
  "feature_name": "{feature_name}",
  "possible_test_scenario_count": <your decided count based on SRS analysis>,
  "no_new_test_cases": false,
  "test_cases": [
    {{
      "test_case_id": "TC-001",
      "title": "Verify that ...",
      "type": "positive | negative | boundary | edge",
      "preconditions": ["precondition 1", "precondition 2"],
      "steps": [
        "1. first action step",
        "2. second action step",
        "3. third action step"
      ],
      "expected_result": ["The system should ...", "The field should ..."]
    }}
  ]
}}
""".strip()


# ------------------------------------------------------------------
# Iterative (gap-finding) prompt
# ------------------------------------------------------------------

def build_iterative_instruction(latest_titles: List[str], covered_summary: str) -> str:
    """
    Return the instruction block that tells the model to find ONLY new
    test cases not already covered by latest_titles.
    """
    titles_block = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(latest_titles))
    summary_block = f"\n{covered_summary}\n" if covered_summary else ""

    return f"""
---
ITERATIVE GENERATION INSTRUCTION:
The following test cases were generated in the latest run. Do not duplicate them:

{titles_block}
{summary_block}
Your task now:
1. Identify gaps in the covered scenarios.
2. Generate ONLY NEW test cases for uncovered areas — focus on: negative/boundary/edge cases, error handling, role-based access, and other fields.
3. If all areas are fully covered, return an empty test_cases array and set "no_new_test_cases" to true.
Return JSON in the same format.
"""
# ------------------------------------------------------------------
# Retry (minimum threshold) prompt
# ------------------------------------------------------------------

def build_retry_instruction(
    existing_count: int,
    min_required: int,
    existing_titles: List[str],
) -> str:
    """
    Return the instruction block appended when the model produced
    fewer than min_required test cases on the first attempt.
    """
    titles_list = "\n".join(f"- {t}" for t in existing_titles if t)

    return (
        f"---\n"
        f"RETRY: Previous attempt returned {existing_count} test cases — minimum required is {min_required}.\n\n"
        f"Re-read ALL SRS sections (requirements, acceptance criteria, impacted areas, "
        f"pre-conditions, user stories, user journeys) and generate at least {min_required} test cases covering:\n"
        f"- Positive: every requirement and acceptance criterion\n"
        f"- Negative: every input field and validation rule\n"
        f"- Boundary: all numeric/text limits\n"
        f"- Edge: error handling and exceptional flows\n\n"
        f"Already generated (DO NOT duplicate):\n"
        f"{titles_list}\n\n"
        f"Generate a complete fresh set. Do not skip any requirement."
    )


# ------------------------------------------------------------------
# Continuation (truncated JSON recovery) prompt
# ------------------------------------------------------------------

def build_continuation_instruction(partial_output: str) -> str:
    """
    Return the prompt used when the model's previous response was truncated.
    """
    return (
        f"Your previous response was truncated. Here is what you generated so far:\n\n"
        f"{partial_output}\n\n"
        f"Continue generating from where you stopped. "
        f"Complete the JSON response with the remaining test cases. "
        f"Return ONLY the missing part to complete the JSON (starting from where you left off)."
    )