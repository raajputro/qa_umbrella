from ppai_test_umbrella.modules.requirement_intelligence.loader import load_requirement_text
from ppai_test_umbrella.modules.requirement_intelligence.prompt_builder import build_scenario_prompt
from ppai_test_umbrella.shared.llm.ollama_client import PPAILLMClient


def generate_scenarios_from_file(file_path: str) -> str:
    requirement_text = load_requirement_text(file_path)
    prompt = build_scenario_prompt(requirement_text)

    llm = PPAILLMClient()
    return llm.ask(
        prompt=prompt,
        system_prompt="You are a senior QA analyst who creates structured test scenarios.",
        temperature=0.2,
    )