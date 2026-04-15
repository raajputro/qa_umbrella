from __future__ import annotations

import argparse
import asyncio
import json
import re
import os
from dotenv import load_dotenv
load_dotenv()
from dataclasses import dataclass
from typing import Any

import requests

from ppai_test_umbrella.mcp.client import QAUmbrellaMCPClient


SYSTEM_PROMPT = """You are a QA Umbrella MCP orchestration assistant.

You must decide the next action for the user's request.

Return ONLY one of the following:

1. A JSON object:
{
  "action": "tool" | "resource" | "answer",
  "name": "<tool name or resource uri or answer text>",
  "arguments": {},
  "reason": "<short reason>"
}

2. If you cannot follow JSON strictly, return ONLY the exact tool name.
Example:
list_requirements

Rules:
- No markdown
- No code fences
- No explanation outside the JSON or tool name
- Prefer tools for requirement analysis
- For test generation flows, common sequence is:
  list_requirements -> list_features -> get_feature -> count_possible_test_scenarios -> generate_test_cases_for_feature
"""


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = str(os.getenv("PPAI_LLM_MODEL"))
    base_url: str = "http://127.0.0.1:11434"


class LLMRouter:
    """
    Minimal LLM router for deciding which MCP action to take.
    Currently supports Ollama chat-style generation.
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def decide(
        self,
        user_prompt: str,
        tools: Any,
        resources: Any,
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        if self.config.provider.lower() != "ollama":
            raise ValueError(f"Unsupported provider: {self.config.provider}")

        prompt = self._build_decision_prompt(
            user_prompt=user_prompt,
            tools=tools,
            resources=resources,
            history=history,
        )
        raw = self._call_ollama(prompt)
        parsed = self._extract_json(raw)
        return self._normalize_action(parsed)

    def summarize(
        self,
        user_prompt: str,
        tool_or_resource_result: Any,
        history: list[dict[str, str]],
    ) -> str:
        if self.config.provider.lower() != "ollama":
            raise ValueError(f"Unsupported provider: {self.config.provider}")

        prompt = f"""You are a helpful QA assistant.

User request:
{user_prompt}

Conversation history:
{json.dumps(history, indent=2, ensure_ascii=False)}

Tool/resource result:
{json.dumps(tool_or_resource_result, indent=2, ensure_ascii=False)}

Write a clear final answer for the user.
Requirements:
- Be concise but useful.
- If result includes feature info, mention feature name/id.
- If result includes scenario count, mention it clearly.
- If result includes test cases, present them in a readable numbered format.
- If result is empty or failed, explain honestly.
Do not mention internal MCP mechanics unless necessary.
"""
        return self._call_ollama(prompt).strip()

    def _build_decision_prompt(
        self,
        user_prompt: str,
        tools: Any,
        resources: Any,
        history: list[dict[str, str]],
    ) -> str:
        return f"""{SYSTEM_PROMPT}

Available tools:
{json.dumps(tools, indent=2, ensure_ascii=False)}

Available resources:
{json.dumps(resources, indent=2, ensure_ascii=False)}

Conversation history:
{json.dumps(history, indent=2, ensure_ascii=False)}

User request:
{user_prompt}
"""

    # def _call_ollama(self, prompt: str) -> str:
    #     url = self.config.base_url.rstrip("/") + "/api/chat"
    #     payload = {
    #         "model": self.config.model,
    #         "messages": [{"role": "user", "content": prompt}],
    #         "stream": False,
    #     }

    #     response = requests.post(url, json=payload, timeout=120)
    #     response.raise_for_status()

    #     data = response.json()
    #     text = data.get("message", {}).get("content", "")
    #     if not isinstance(text, str):
    #         raise ValueError("Unexpected Ollama response format")
    #     return text

    def _call_ollama(self, prompt: str) -> str:
        self._ensure_model_exists()

        base = self.config.base_url.rstrip("/")

        # sanity check
        tags_resp = requests.get(f"{base}/api/tags", timeout=20)
        tags_resp.raise_for_status()

        # try chat first
        chat_payload = {
            "model": self.config.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
        }

        chat_resp = requests.post(
            f"{base}/api/chat",
            json=chat_payload,
            timeout=120,
        )

        if chat_resp.ok:
            data = chat_resp.json()
            text = data.get("message", {}).get("content", "")
            if isinstance(text, str) and text.strip():
                return text

        # fallback to generate
        gen_payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
        }

        gen_resp = requests.post(
            f"{base}/api/generate",
            json=gen_payload,
            timeout=120,
        )
        gen_resp.raise_for_status()

        data = gen_resp.json()
        text = data.get("response", "")
        if not isinstance(text, str):
            raise ValueError("Unexpected Ollama response format")
        return text

    # @staticmethod
    # def _extract_json(text: str) -> dict[str, Any]:
    #     text = text.strip()

    #     try:
    #         parsed = json.loads(text)
    #         if isinstance(parsed, dict):
    #             return parsed
    #     except Exception:
    #         pass

    #     match = re.search(r"\{.*\}", text, re.DOTALL)
    #     if not match:
    #         raise ValueError(f"Could not find JSON in model response:\n{text}")

    #     candidate = match.group(0)
    #     parsed = json.loads(candidate)
    #     if not isinstance(parsed, dict):
    #         raise ValueError("Model response JSON is not an object")
    #     return parsed

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | str:
        text = text.strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, str):
                return parsed
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            candidate = match.group(0)
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return text

    # @staticmethod
    # # def _normalize_action(data: dict[str, Any]) -> dict[str, Any]:
    #     action = str(data.get("action", "")).strip().lower()
    #     name = data.get("name", "")
    #     arguments = data.get("arguments", {})
    #     reason = data.get("reason", "")

    #     if action not in {"tool", "resource", "answer"}:
    #         raise ValueError(f"Invalid action from model: {action}")

    #     if not isinstance(arguments, dict):
    #         arguments = {}

    #     return {
    #         "action": action,
    #         "name": str(name),
    #         "arguments": arguments,
    #         "reason": str(reason),
    #     }
    
    @staticmethod
    def _normalize_action(data: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(data, str):
            raw = data.strip()

            if raw.startswith("requirements://") or raw.startswith("generated://") or raw.startswith("healing://"):
                return {
                    "action": "resource",
                    "name": raw,
                    "arguments": {},
                    "reason": "Model returned a resource URI directly.",
                }

            return {
                "action": "tool",
                "name": raw,
                "arguments": {},
                "reason": "Model returned a tool name directly.",
            }

        action = str(data.get("action", "")).strip().lower()
        name = str(data.get("name", "")).strip()
        arguments = data.get("arguments", {})
        reason = str(data.get("reason", "")).strip()

        # If model put the tool name in action
        if action and action not in {"tool", "resource", "answer"}:
            return {
                "action": "tool",
                "name": action,
                "arguments": arguments if isinstance(arguments, dict) else {},
                "reason": reason or "Model used tool name in action field.",
            }

        if action == "answer" and not name:
            name = reason or "I could not determine the next action."

        if not isinstance(arguments, dict):
            arguments = {}

        if action not in {"tool", "resource", "answer"}:
            raise ValueError(f"Invalid action from model: {action}")

        return {
            "action": action,
            "name": name,
            "arguments": arguments,
            "reason": reason,
        }

    def _ensure_model_exists(self) -> None:
        base = self.config.base_url.rstrip("/")
        resp = requests.get(f"{base}/api/tags", timeout=20)
        resp.raise_for_status()

        data = resp.json()
        models = data.get("models", [])
        names = {m.get("name") for m in models if isinstance(m, dict)}

        if self.config.model not in names:
            raise ValueError(
                f"Configured Ollama model '{self.config.model}' is not installed. "
                f"Available models: {sorted(n for n in names if n)}"
            )


class MCPChatAgent:
    """
    Chat-style agent that uses an LLM to decide which MCP tool/resource to use,
    then summarizes the result back to the user.
    """

    def __init__(
        self,
        mcp_client: QAUmbrellaMCPClient,
        llm_router: LLMRouter,
        max_turn_tools: int = 3,
    ) -> None:
        self.mcp_client = mcp_client
        self.llm_router = llm_router
        self.max_turn_tools = max(1, max_turn_tools)
        self.history: list[dict[str, str]] = []

    async def ask(self, user_prompt: str) -> str:
        self.history.append({"role": "user", "content": user_prompt})

        tools = await self.mcp_client.list_tools()
        resources = await self.mcp_client.list_resources()

        last_result: Any = None

        for _ in range(self.max_turn_tools):
            decision = self.llm_router.decide(
                user_prompt=user_prompt,
                tools=tools,
                resources=resources,
                history=self.history,
            )

            action = decision["action"]
            name = decision["name"]
            arguments = decision["arguments"]

            if action == "answer":
                answer = name or "I could not find a specific action to take."
                self.history.append({"role": "assistant", "content": answer})
                return answer

            if action == "resource":
                last_result = await self.mcp_client.read_resource(name)
                self.history.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            {
                                "action": "resource",
                                "name": name,
                                "result": last_result,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
                final = self.llm_router.summarize(
                    user_prompt=user_prompt,
                    tool_or_resource_result=last_result,
                    history=self.history,
                )
                self.history.append({"role": "assistant", "content": final})
                return final

            if action == "tool":
                last_result = await self.mcp_client.call_tool(name, arguments)
                self.history.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            {
                                "action": "tool",
                                "name": name,
                                "arguments": arguments,
                                "result": last_result,
                            },
                            ensure_ascii=False,
                        ),
                    }
                )

                terminal_tools = {
                    "get_feature",
                    "count_possible_test_scenarios",
                    "generate_test_cases_for_feature",
                    "generate_from_requirement",
                    "heal_locator",
                    "heal_steps",
                    "read_requirement",
                    "read_generated_output",
                }

                discovery_tools = {
                    "list_requirements",
                    "parse_requirements",
                    "list_features",
                    "list_generated_outputs",
                }

                if name in terminal_tools:
                    final = self.llm_router.summarize(
                        user_prompt=user_prompt,
                        tool_or_resource_result=last_result,
                        history=self.history,
                    )
                    self.history.append({"role": "assistant", "content": final})
                    return final

                if name in discovery_tools:
                    continue

                continue

        if last_result is None:
            final = "I could not complete the request through the MCP tools."
        else:
            final = self.llm_router.summarize(
                user_prompt=user_prompt,
                tool_or_resource_result=last_result,
                history=self.history,
            )

        self.history.append({"role": "assistant", "content": final})
        return final


async def _interactive_loop(args: argparse.Namespace) -> None:
    llm = LLMRouter(
        LLMConfig(
            provider="ollama",
            model=args.model,
            base_url=args.ollama_url,
        )
    )

    async with QAUmbrellaMCPClient(
        python_executable=args.python,
        server_module=args.server_module,
        cwd=args.cwd,
    ) as mcp_client:
        agent = MCPChatAgent(
            mcp_client=mcp_client,
            llm_router=llm,
            max_turn_tools=args.max_turn_tools,
        )

        print("QA Umbrella MCP Chat Agent is ready.")
        print("Type 'exit' or 'quit' to stop.\n")

        while True:
            try:
                user_prompt = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not user_prompt:
                continue

            if user_prompt.lower() in {"exit", "quit"}:
                print("Bye.")
                break

            try:
                answer = await agent.ask(user_prompt)
                print(f"\nAgent: {answer}\n")
            except Exception as exc:
                print(f"\nAgent error: {exc}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ppai_test_umbrella.apps.mcp_chat_agent",
        description="Chat-style MCP agent for QA Umbrella using Ollama",
    )
    parser.add_argument(
        "--python",
        default="python",
        help="Python executable used to launch the local MCP server",
    )
    parser.add_argument(
        "--server-module",
        default="ppai_test_umbrella.mcp.server",
        help="Python module path of the MCP server",
    )
    parser.add_argument(
        "--cwd",
        default=None,
        help="Optional working directory for launching the server",
    )
    parser.add_argument(
        "--model",
        default=str(os.getenv("PPAI_LLM_MODEL")),
        help="Ollama model name",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Base URL for Ollama",
    )
    parser.add_argument(
        "--max-turn-tools",
        type=int,
        default=3,
        help="Maximum MCP tool/resource actions per user turn",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_interactive_loop(args))


if __name__ == "__main__":
    main()