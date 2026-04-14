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

timer = Timer()
timer.start()

file_path = "reqs/SRS_AH_R1.pdf"
user_prompt = "count possible test scenarios for feature 7, and write me all test cases of that"

# 1. Load requirement file
raw_text = load_requirement_text(file_path)

# 2. Build feature-aware index
processor = RequirementKnowledgeProcessor(
    chunk_size=1200,
    chunk_overlap=150,
    min_feature_word_count=40,
)
req_index = processor.build_index(raw_text, title="Sample SRS")

# 3. Build focused prompt for the target feature
result = processor.answer_prompt(req_index, user_prompt)

# Debug what was selected
print(processor.debug_feature_selection(req_index, "6"))

# 4. Send prompt to Ollama
generator = OllamaScenarioGenerator(
    ollama_url="http://localhost:11434/api/generate",
    timeout=1200,
    temperature=0.2,
    batch_size=5,
)

final_output = generator.generate_from_prompt(
    result["test_case_generation_prompt"],
    expected_count=result["requested_test_case_count"],
)

print("----- FINAL OUTPUT -----")
# print(final_output)
file_name = "test_cases_feature_7_all"
txt_path = export_test_cases_txt(final_output, f"runtime_data/generated/{file_name}.txt")
print(f"TXT exported to: {txt_path}")

json_path = export_test_cases_json(final_output, f"runtime_data/generated/{file_name}.json")
print(f"JSON exported to: {json_path}")

try:
    pdf_path = export_test_cases_pdf(final_output, f"runtime_data/generated/{file_name}.pdf")
    print(f"PDF exported to: {pdf_path}")
except ImportError as exc:
    print(f"PDF export skipped: {exc}")

time_elapsed = timer.elapsed()
print(f"Total time elapsed: {time_elapsed}")
