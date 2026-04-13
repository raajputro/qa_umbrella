import os
from dotenv import load_dotenv
from openai import OpenAI
import ollama_config as oc
from ppai_test_umbrella.shared.llm.ollama_client import PPAILLMClient 

load_dotenv()

required = ["PPAI_LLM_BASE_URL", "PPAI_LLM_API_KEY", "PPAI_LLM_MODEL"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


client = OpenAI(
    base_url=os.getenv('PPAI_LLM_BASE_URL'), # type: ignore
    api_key=os.getenv('PPAI_LLM_API_KEY'), # type: ignore
)

# resp = client.chat.completions.create(
#     model=os.getenv('PPAI_LLM_MODEL'), # type: ignore
#     messages=[
#         {"role": "system", "content": "You are a QA automation assistant."},
#         {"role": "user", "content": "Generate 3 login test scenarios."},
#     ],
#     temperature=0.2,
# )

# print(f"Using model: {os.getenv('PPAI_LLM_MODEL')}")# type: ignore
# print(resp.choices[0].message.content)

prompt = "You are a QA automation assistant. Generate 3 login validation negative test scenarios."

# ------------------------------------------------------------------------------------------------------------------------
resp = oc.get_llm_response_for_testcase(prompt)
print(f"OLLAMA Generated Test Cases:")
print(f"Used OLLAMA Model: {os.getenv('PPAI_LLM_MODEL')}")# type: ignore
print(f"Response from get_llm_response_for_testcase: {resp}")
# ------------------------------------------------------------------------------------------------------------------------
llm = PPAILLMClient()
answer = llm.ask(prompt)
print(f"PPAI Generated Test Cases:")
print(f"Response from PPAI: {answer}")