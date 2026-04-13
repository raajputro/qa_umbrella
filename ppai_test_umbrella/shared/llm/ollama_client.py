import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class PPAILLMClient:
    def __init__(self):
        self.base_url = os.getenv("PPAI_LLM_BASE_URL", "http://localhost:11434/v1")
        self.api_key = os.getenv("PPAI_LLM_API_KEY", "ollama")
        self.model = os.getenv("PPAI_LLM_MODEL", "qwen2.5-coder:3b-instruct-q4_0")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def ask(self, prompt: str, system_prompt: str = "You are a QA automation assistant.", temperature: float = 0.3) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content # type: ignore