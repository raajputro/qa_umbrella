# # from ppai_test_umbrella.modules.requirement_intelligence.loader import load_requirement_text
# # from ppai_test_umbrella.modules.requirement_intelligence.requirement_processor import RequirementProcessor

# # file_path = "reqs/sample.txt"  # change to any file
# # raw_text = load_requirement_text(file_path=file_path)

# # processor = RequirementProcessor(chunk_size=2500, chunk_overlap=200)
# # doc = processor.process(raw_text, title="Sample Requirement")

# # print(doc.to_dict())
# # print("----- DOCUMENT CHUNKS -----")
# # print(processor.build_llm_ready_text(doc))
# # print()
# # print(processor.build_scenario_generation_prompt(doc))

# # # text = load_requirement_text(file_path)

# # # print("----- LOADED TEXT -----")
# # # print(text[:1000])  # preview


# from ppai_test_umbrella.modules.requirement_intelligence.loader import load_requirement_text
# from ppai_test_umbrella.modules.requirement_intelligence.requirement_processor import RequirementKnowledgeProcessor

# file_path = "reqs/AmarHishab_Release_1.pdf"

# raw_text = load_requirement_text(file_path)

# # processor = RequirementKnowledgeProcessor(chunk_size=1200, chunk_overlap=150)
# # req_index = processor.build_index(raw_text, title="Sample SRS")

# # prompt = "count possible test scenarios for feature 6, and write me 10 test cases of that"

# # result = processor.answer_prompt(req_index, prompt)

# # print(result["feature_id"])
# # print(result["feature_name"])
# # print(result["possible_test_scenario_count"])
# # print(result["test_case_generation_prompt"])

# processor = RequirementKnowledgeProcessor(
#     chunk_size=1200,
#     chunk_overlap=150,
#     min_feature_word_count=40,
# )

# req_index = processor.build_index(raw_text, title="My SRS")

# prompt = "count possible test scenarios for feature 6, and write me 10 test cases of that"
# result = processor.answer_prompt(req_index, prompt)

# print(result["feature_id"])
# print(result["feature_name"])
# print(result["possible_test_scenario_count"])
# print(result["test_case_generation_prompt"])


from ppai_test_umbrella.modules.requirement_intelligence.loader import load_requirement_text
from ppai_test_umbrella.modules.requirement_intelligence.requirement_processor import RequirementKnowledgeProcessor
from ppai_test_umbrella.modules.requirement_intelligence.scenario_generator import OllamaScenarioGenerator
from ppai_test_umbrella.modules.requirement_intelligence.exporter import (
    export_test_cases_json,
    export_test_cases_pdf,
    export_test_cases_txt,
)
from utils.timers import Timer
import argparse
import re


GENERATION_SCOPE = "all"  # use "feature" for one feature, or "all" for full SRS
FEATURE_ID = "7"  # used only when GENERATION_SCOPE = "feature"
USER_PROMPT = "count possible test scenarios for all features, and write me all test cases for each feature"  # optional natural-language prompt to override scope and requested test case count
FILE_PATH = "reqs/Section_I2.docx"
# Examples:
# USER_PROMPT = "count possible test scenarios for feature 7, and write me all test cases of that"
# USER_PROMPT = "count possible test scenarios for all features, and write me all test cases for each feature"


def _safe_file_part(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return value.strip("_") or "unknown"


def _is_toc_like_heading(feature) -> bool:
    first_line = feature.raw_text.splitlines()[0] if feature.raw_text else ""
    return bool(re.search(r"\.{3,}\s*\d+\s*$", first_line))


def _looks_like_feature_heading(feature) -> bool:
    first_line = feature.raw_text.splitlines()[0] if feature.raw_text else ""
    heading_text = f"{feature.feature_name} {first_line}".lower()
    return "feature" in heading_text


def _select_top_level_features(features):
    selected = []
    last_feature_number = 0

    for feature in features:
        if _is_toc_like_heading(feature):
            continue

        try:
            feature_number = int(str(feature.feature_id).strip())
        except ValueError:
            selected.append(feature)
            continue

        is_next_feature = feature_number == last_feature_number + 1
        if not _looks_like_feature_heading(feature) and not is_next_feature:
            continue

        selected.append(feature)
        last_feature_number = feature_number

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
        help="Optional natural-language prompt. A prompt mentioning all features switches to full-SRS mode.",
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


def _build_generation_request(processor, feature, prompt=None):
    possible_count = processor.estimate_possible_test_scenarios(feature)
    requested_count = possible_count

    if prompt and not _prompt_requests_full_srs(prompt):
        intent = processor.parse_prompt(prompt)
        requested_count = intent.requested_test_case_count or possible_count

    return {
        "feature_id": feature.feature_id,
        "feature_name": feature.feature_name,
        "possible_test_scenario_count": possible_count,
        "requested_test_case_count": requested_count,
        "test_case_generation_prompt": processor.build_test_case_generation_prompt(
            feature=feature,
            requested_count=requested_count,
            possible_scenario_count=possible_count,
        ),
    }


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
features_to_generate, selected_scope = _select_features_for_request(
    processor,
    req_index,
    prompt=args.prompt,
    generation_scope=args.scope,
    feature_id=args.feature_id,
)

# 3. Send one focused prompt per feature to Ollama
generator = OllamaScenarioGenerator(
    ollama_url="http://localhost:11434/api/generate",
    timeout=1200,
    temperature=0.2,
    batch_size=5,
)

all_feature_outputs = []
generation_errors = []

print(
    f"Detected {len(req_index.features)} candidate feature section(s); "
    f"generating test cases for {len(features_to_generate)} feature(s) "
    f"in {selected_scope} mode."
)

for feature in features_to_generate:
    print(f"Generating feature {feature.feature_id}: {feature.feature_name}")
    result = _build_generation_request(processor, feature, prompt=args.prompt)

    try:
        final_output = generator.generate_from_prompt(
            result["test_case_generation_prompt"],
            expected_count=result["requested_test_case_count"],
        )
    except Exception as exc:
        generation_errors.append(
            {
                "feature_id": feature.feature_id,
                "feature_name": feature.feature_name,
                "error": str(exc),
            }
        )
        print(f"Feature {feature.feature_id} failed: {exc}")
        continue

    all_feature_outputs.append(final_output)

    file_name = (
        f"test_cases_feature_{_safe_file_part(feature.feature_id)}_"
        f"{_safe_file_part(feature.feature_name)}"
    )
    txt_path = export_test_cases_txt(final_output, f"runtime_data/generated/{file_name}.txt")
    print(f"TXT exported to: {txt_path}")

    json_path = export_test_cases_json(final_output, f"runtime_data/generated/{file_name}.json")
    print(f"JSON exported to: {json_path}")

    try:
        pdf_path = export_test_cases_pdf(final_output, f"runtime_data/generated/{file_name}.pdf")
        print(f"PDF exported to: {pdf_path}")
    except ImportError as exc:
        print(f"PDF export skipped for feature {feature.feature_id}: {exc}")

if selected_scope == "all":
    combined_output = {
        "source_file": file_path,
        "candidate_feature_count": len(req_index.features),
        "feature_count": len(features_to_generate),
        "generated_feature_count": len(all_feature_outputs),
        "total_test_case_count": sum(
            len(output.get("test_cases", []))
            for output in all_feature_outputs
            if isinstance(output, dict)
        ),
        "features": all_feature_outputs,
    }

    if generation_errors:
        combined_output["generation_errors"] = generation_errors

    combined_file_name = "test_cases_all_features"
    txt_path = export_test_cases_txt(combined_output, f"runtime_data/generated/{combined_file_name}.txt")
    print(f"Combined TXT exported to: {txt_path}")

    json_path = export_test_cases_json(combined_output, f"runtime_data/generated/{combined_file_name}.json")
    print(f"Combined JSON exported to: {json_path}")

    try:
        pdf_path = export_test_cases_pdf(combined_output, f"runtime_data/generated/{combined_file_name}.pdf")
        print(f"Combined PDF exported to: {pdf_path}")
    except ImportError as exc:
        print(f"Combined PDF export skipped: {exc}")

time_elapsed = timer.elapsed()
print(f"Total time elapsed: {time_elapsed}")
