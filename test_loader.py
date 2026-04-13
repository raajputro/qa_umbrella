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

file_path = "reqs/AmarHishab_Release_1.pdf"
user_prompt = "count possible test scenarios for feature 6, and write me 10 test cases of that"

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
    model="qwen2.5-coder:latest",   # change if needed
    ollama_url="http://localhost:11434/api/generate",
    timeout=180,
    temperature=0.2,
)

final_output = generator.generate_from_prompt(result["test_case_generation_prompt"])

print("----- FINAL OUTPUT -----")
print(final_output)