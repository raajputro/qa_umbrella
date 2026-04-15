from __future__ import annotations

import asyncio
import json
import os
from contextlib import AsyncExitStack
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _to_plain(value: Any) -> Any:
    """
    Convert SDK/model objects into JSON-serializable plain Python structures.
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_plain(v) for v in value]

    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump())
        except Exception:
            pass

    if is_dataclass(value):
        return _to_plain(asdict(value))

    if hasattr(value, "__dict__"):
        try:
            return _to_plain(vars(value))
        except Exception:
            pass

    return str(value)


class QAUmbrellaMCPClient:
    """
    MCP client for the qa_umbrella / ppai_test_umbrella MCP server.

    This client starts the local MCP server over stdio and exposes a few
    convenient high-level helpers around session methods.
    """

    def __init__(
        self,
        python_executable: str | None = None,
        server_module: str = "ppai_test_umbrella.mcp.server",
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.python_executable = python_executable or os.environ.get("PYTHON", "python")
        self.server_module = server_module
        self.cwd = cwd
        self.env = env or os.environ.copy()

        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def connect(self) -> "QAUmbrellaMCPClient":
        """
        Start the MCP server as a subprocess and initialize a session.
        """
        if self._session is not None:
            return self

        server_params = StdioServerParameters(
            command=self.python_executable,
            args=["-m", self.server_module],
            env=self.env,
            cwd=self.cwd,
        )

        self._exit_stack = AsyncExitStack()
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._session = session
        return self

    async def close(self) -> None:
        """
        Close the MCP session and the spawned server process.
        """
        if self._exit_stack is not None:
            await self._exit_stack.aclose()

        self._exit_stack = None
        self._session = None

    async def __aenter__(self) -> "QAUmbrellaMCPClient":
        return await self.connect()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP client is not connected. Call connect() first.")
        return self._session

    async def list_tools(self) -> Any:
        result = await self.session.list_tools()
        return _to_plain(result)

    async def list_resources(self) -> Any:
        result = await self.session.list_resources()
        return _to_plain(result)

    async def list_prompts(self) -> Any:
        result = await self.session.list_prompts()
        return _to_plain(result)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """
        Call a named MCP tool.
        """
        result = await self.session.call_tool(name, arguments=arguments or {})
        return _to_plain(result)

    async def read_resource(self, uri: str) -> Any:
        """
        Read an MCP resource by URI.
        """
        result = await self.session.read_resource(uri)
        return _to_plain(result)

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """
        Get an MCP prompt by name.
        """
        result = await self.session.get_prompt(name, arguments=arguments or {})
        return _to_plain(result)

    #
    # High-level helpers for your QA Umbrella workflows
    #

    async def workflow_feature_test_design(
        self,
        requirement_path: str,
        feature_id: str,
        count: int = 10,
    ) -> dict[str, Any]:
        """
        End-to-end helper:
        - inspect the feature
        - estimate scenarios
        - generate test cases
        """
        feature = await self.call_tool(
            "get_feature",
            {"path": requirement_path, "feature_id": str(feature_id)},
        )

        scenario_info = await self.call_tool(
            "count_possible_test_scenarios",
            {"path": requirement_path, "feature_id": str(feature_id)},
        )

        testcases = await self.call_tool(
            "generate_test_cases_for_feature",
            {
                "path": requirement_path,
                "feature_id": str(feature_id),
                "count": int(count),
            },
        )

        return {
            "feature": feature,
            "scenario_info": scenario_info,
            "testcases": testcases,
        }


async def _demo() -> None:
    async with QAUmbrellaMCPClient() as client:
        print("Connected to MCP server.\n")

        tools = await client.list_tools()
        print("TOOLS:")
        print(json.dumps(tools, indent=2, ensure_ascii=False))

        resources = await client.list_resources()
        print("\nRESOURCES:")
        print(json.dumps(resources, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_demo())