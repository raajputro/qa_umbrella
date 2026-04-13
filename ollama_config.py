import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

required = ["PPAI_LLM_BASE_URL", "PPAI_LLM_API_KEY", "PPAI_LLM_MODEL"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


client = OpenAI(
    base_url=os.getenv('PPAI_LLM_BASE_URL'), # type: ignore
    api_key=os.getenv('PPAI_LLM_API_KEY'), # type: ignore
)

# Use this for testcase generation
# def get_llm_response_for_testcase(messages):
#     resp = client.chat.completions.create(
#         model=os.getenv('PPAI_LLM_MODEL'), # type: ignore
#         messages=messages,
#         temperature=0.3,
#     )
#     return resp.choices[0].message.content

def get_llm_response_for_testcase(prompt: str) -> str:
    resp = client.chat.completions.create(
        model=os.getenv('PPAI_LLM_MODEL'), # type: ignore
        messages=[{"role": "system", "content": prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content # type: ignore