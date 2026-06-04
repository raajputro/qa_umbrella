from ppai_test_umbrella.modules.requirement_intelligence.loader import load_requirement_text
from ppai_test_umbrella.modules.requirement_intelligence.requirement_processor import RequirementKnowledgeProcessor
from ppai_test_umbrella.modules.requirement_intelligence.scenario_generator import OllamaScenarioGenerator
from ppai_test_umbrella.modules.requirement_intelligence.exporter import (
    export_test_cases_json,
    export_test_cases_excel,
)
from ppai_test_umbrella.modules.requirement_intelligence.memory_manager import GenerationMemoryManager
from ppai_test_umbrella.modules.requirement_intelligence.prompt_builder import SYSTEM_PROMPT
from utils.timers import Timer
import argparse
import json
import re
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


GENERATION_SCOPE = "all"  # use "feature" for one feature, or "all" for full SRS
FEATURE_ID = "7"  # used only when GENERATION_SCOPE = "feature"
USER_PROMPT = SYSTEM_PROMPT

FILE_PATH = "reqs/Section_IV 1.docx"


def _safe_file_part(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return value.strip("_") or "unknown"


def _is_toc_like_heading(feature) -> bool:
    first_line = feature.raw_text.splitlines()[0] if feature.raw_text else ""
    return bool(re.search(r"\.{3,}\s*\d+\s*$", first_line))



def _select_top_level_features(features):
    selected = []
    for feature in features:
        if _is_toc_like_heading(feature):
            continue
        selected.append(feature)
    return selected


def _prompt_requests_full_srs(prompt: str) -> bool:
    lower = prompt.lower()
    return bool(
        re.search(r"\b(all|every|full|entire|complete)\s+(top-level\s+)?features?\b", lower)
        or re.search(r"\b(full|entire|complete)\s+srs\b", lower)
        or re.search(r"\bfor\s+each\s+feature\b", lower)
    )


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Generate test cases for one SRS feature or for the full SRS."
    )
    parser.add_argument(
        "--scope",
        choices=["feature", "all"],
        default=GENERATION_SCOPE,
        help='Use "feature" for one selected feature, or "all" for the full SRS.',
    )
    parser.add_argument(
        "--feature-id",
        default=FEATURE_ID,
        help='Feature id to generate when --scope feature is used, for example "7".',
    )
    parser.add_argument(
        "--prompt",
        default=USER_PROMPT,
        help="Optional natural-language prompt.",
    )
    parser.add_argument(
        "--file",
        default=FILE_PATH,
        help="Requirement file path.",
    )
    return parser.parse_args()


def _select_features_for_request(
    processor,
    req_index,
    prompt=None,
    generation_scope=GENERATION_SCOPE,
    feature_id=FEATURE_ID,
):
    top_level_features = _select_top_level_features(req_index.features)

    if prompt and _prompt_requests_full_srs(prompt):
        return top_level_features, "all"

    if prompt:
        intent = processor.parse_prompt(prompt)
        if intent.feature_id:
            feature = processor.get_feature_by_id(req_index, intent.feature_id)
            if not feature:
                raise ValueError(f"Could not find feature {intent.feature_id}")
            return [feature], "feature"

    if generation_scope.lower() == "all":
        return top_level_features, "all"

    if generation_scope.lower() == "feature":
        feature = processor.get_feature_by_id(req_index, feature_id)
        if not feature:
            raise ValueError(f"Could not find feature {feature_id}")
        return [feature], "feature"

    raise ValueError('GENERATION_SCOPE must be either "feature" or "all"')


def _build_generation_request(processor, feature, prompt=None, srs_context=None):
    return {
        "feature_id": feature.feature_id,
        "feature_name": feature.feature_name,
        "test_case_generation_prompt": processor.build_test_case_generation_prompt(
            feature=feature,
            user_instruction=prompt,
            srs_context=srs_context,
        ),
    }


def _versioned_path(raw_path: str) -> str:
    """Return a versioned file path: file.json -> file.json, file_v2.json, file_v3.json, ..."""
    p = Path(raw_path)
    if not p.exists():
        return str(p)
    stem, suffix = p.stem, p.suffix
    version = 2
    while True:
        candidate = p.parent / f"{stem}_v{version}{suffix}"
        if not candidate.exists():
            return str(candidate)
        version += 1


def _find_latest_version(raw_path: str):
    """Find the latest versioned file: file.json, file_v2.json, file_v3.json, ...
    Returns the Path to the latest version, or None if no file exists."""
    p = Path(raw_path)

    # If the parent directory doesn't exist yet, no previous output exists
    if not p.parent.exists():
        return None

    # Collect all versions
    candidates = []
    if p.exists():
        candidates.append((1, p))
    for f in p.parent.glob(f"{p.stem}_v*{p.suffix}"):
        match = re.search(r"_v(\d+)$", f.stem)
        if match:
            candidates.append((int(match.group(1)), f))

    if not candidates:
        return None

    # Return the one with the highest version number
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _load_existing_test_cases(raw_path: str):
    """Load existing test cases from the latest versioned JSON output.
    Returns (test_cases_list, path_loaded_from)."""
    latest = _find_latest_version(raw_path)
    if latest is None:
        return [], None
    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            tcs = data.get("test_cases", [])
            if isinstance(tcs, list):
                return tcs, str(latest)
    except Exception as e:
        print(f"  Warning: Could not load previous results from {latest}: {e}")
    return [], None


# ======================================================================
# Main execution
# ======================================================================

args = _parse_args()
timer = Timer()
timer.start()

file_path = args.file

# 1. Load requirement file
raw_text = load_requirement_text(file_path)

# 2. Build feature-aware index
processor = RequirementKnowledgeProcessor(
    chunk_size=1200,
    chunk_overlap=150,
    min_feature_word_count=40,
)
req_index = processor.build_index(raw_text, title="Sample SRS")
features_to_generate, _ = _select_features_for_request(
    processor,
    req_index,
    prompt=args.prompt,
    generation_scope=args.scope,
    feature_id=args.feature_id,
)

# 3. Send one focused prompt per feature to Ollama (cumulative iterative mode)
generator = OllamaScenarioGenerator(
    ollama_url="http://localhost:11434/api/chat",
)

memory_manager = GenerationMemoryManager()

total_new_tc_count = 0
features_with_no_new = 0

print(
    f"Detected {len(req_index.features)} candidate feature section(s); "
    f"generating test cases for {len(features_to_generate)} feature(s)."
)

for feature in features_to_generate:
    print(f"\n{'='*60}")
    print(f"Feature {feature.feature_id}: {feature.feature_name}")
    print(f"{'='*60}")

    # Determine the base file name for this feature
    file_name = (
        f"test_cases_feature_{_safe_file_part(feature.feature_id)}_"
        f"{_safe_file_part(feature.feature_name)}"
    )
    base_json_path = f"runtime_data/generated/{file_name}.json"

    # Load existing test cases from the latest versioned file
    existing_tcs, loaded_from = _load_existing_test_cases(base_json_path)
    if existing_tcs:
        print(f"  Loaded {len(existing_tcs)} existing test cases from: {loaded_from}")
    else:
        print("  No previous results found. Starting fresh.")

    # Construct SRS-wide context
    other_features = [f for f in req_index.features if str(f.feature_id) != str(feature.feature_id)]
    srs_context_lines = ["Other features in this SRS (for cross-feature interdependencies):"]
    for f in other_features:
        first_line = f.raw_text.splitlines()[0] if f.raw_text else ""
        srs_context_lines.append(f"- Feature {f.feature_id}: {f.feature_name} (Summary: {first_line[:150]})")
    srs_context = "\n".join(srs_context_lines)

    # Inject past run history
    run_history = memory_manager.get_run_history_context(feature.feature_id)
    if run_history:
        srs_context = srs_context + "\n\n" + run_history

    result = _build_generation_request(processor, feature, prompt=args.prompt, srs_context=srs_context)

    try:
        final_output = generator.generate_from_prompt(
            result["test_case_generation_prompt"],
            existing_test_cases=existing_tcs,
        )
    except Exception as exc:
        print(f"  Feature {feature.feature_id} failed: {exc}")
        continue

    # Check convergence
    new_count = final_output.get("new_test_case_count", 0)
    total_count = final_output.get("generated_test_case_count", 0)
    no_new = final_output.get("no_new_test_cases", False)

    if no_new:
        features_with_no_new += 1
        print(f"\n  Feature fully covered. Total: {total_count} test cases.")
    elif new_count == 0:
        print(f"\n  Generated: {new_count} new test cases (all duplicates). Total: {total_count} test cases.")
    else:
        total_new_tc_count += new_count
        print(f"\n  {new_count} new test cases added. Total: {total_count} test cases.")

    # Ensure feature metadata is set
    final_output["feature_id"] = str(feature.feature_id)
    final_output["feature_name"] = feature.feature_name

    clarifications = final_output.pop("clarification_needed", [])
    if clarifications:
        print("  Clarifications needed (assumptions):")
        for c in clarifications:
            if str(c).strip() and str(c).strip() != "Any missing SRS detail that prevents safe testcase generation":
                print(f"    - {c}")

    # Persist newly generated titles
    if isinstance(final_output, dict) and "test_cases" in final_output:
        new_titles = [tc.get("title", "") for tc in final_output["test_cases"] if isinstance(tc, dict)]
        memory_manager.add_generated_titles(new_titles)

        # Save run summary
        tc_types = {}
        for tc in final_output["test_cases"]:
            if isinstance(tc, dict):
                t = tc.get("type", "unknown")
                tc_types[t] = tc_types.get(t, 0) + 1
        memory_manager.add_run_summary(
            feature_id=str(feature.feature_id),
            feature_name=feature.feature_name,
            test_case_count=total_count,
            type_breakdown=tc_types,
        )


    # Save as new versioned files (never overwrite previous output)
    Path("runtime_data/generated").mkdir(parents=True, exist_ok=True)

    json_path = _versioned_path(base_json_path)
    export_test_cases_json(final_output, json_path)
    print(f"\n  JSON saved to: {json_path}")

    base_excel_path = f"runtime_data/generated/{file_name}.xlsx"
    excel_path = _versioned_path(base_excel_path)
    export_test_cases_excel(final_output, excel_path)
    print(f"  Excel saved to: {excel_path}")


# Summary
print(f"\n{'='*60}")
print("RUN SUMMARY")
print(f"{'='*60}")
print(f"  Features processed:       {len(features_to_generate)}")
print(f"  New TCs added this run:   {total_new_tc_count}")
print(f"  Fully covered features:   {features_with_no_new} out of {len(features_to_generate)}")
if features_with_no_new < len(features_to_generate):
    remaining = len(features_to_generate) - features_with_no_new
    print(f"  Status:                   {remaining} feature(s) may still have uncovered scenarios.")
    print("                            Run again to generate more test cases.")
else:
    print("  Status:                   All features fully covered!")
    print("                            No new test cases can be generated.")
time_elapsed = timer.elapsed()
print(f"  Time elapsed:             {time_elapsed}")
