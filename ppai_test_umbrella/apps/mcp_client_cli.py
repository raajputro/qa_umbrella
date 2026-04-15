from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from ppai_test_umbrella.mcp.client import QAUmbrellaMCPClient


def _json_arg(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for --args: {exc}") from exc

    if not isinstance(parsed, dict):
        raise SystemExit("--args must be a JSON object")

    return parsed


async def _run(args: argparse.Namespace) -> None:
    async with QAUmbrellaMCPClient(
        python_executable=args.python,
        server_module=args.server_module,
        cwd=args.cwd,
    ) as client:
        if args.command == "list-tools":
            result = await client.list_tools()

        elif args.command == "list-resources":
            result = await client.list_resources()

        elif args.command == "list-prompts":
            result = await client.list_prompts()

        elif args.command == "call-tool":
            result = await client.call_tool(
                args.name,
                _json_arg(args.args),
            )

        elif args.command == "read-resource":
            result = await client.read_resource(args.uri)

        elif args.command == "get-prompt":
            result = await client.get_prompt(
                args.name,
                _json_arg(args.args),
            )

        elif args.command == "feature-design":
            result = await client.workflow_feature_test_design(
                requirement_path=args.path,
                feature_id=args.feature_id,
                count=args.count,
            )

        else:
            raise SystemExit(f"Unknown command: {args.command}")

        print(json.dumps(result, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ppai_test_umbrella.apps.mcp_client_cli",
        description="CLI MCP client for QA Umbrella",
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-tools")
    subparsers.add_parser("list-resources")
    subparsers.add_parser("list-prompts")

    call_tool = subparsers.add_parser("call-tool")
    call_tool.add_argument("name", help="Tool name")
    call_tool.add_argument(
        "--args",
        default="{}",
        help='JSON object for tool arguments, e.g. \'{"path":"assets/requirements/sample.txt"}\'',
    )

    read_resource = subparsers.add_parser("read-resource")
    read_resource.add_argument("uri", help="Resource URI")

    get_prompt = subparsers.add_parser("get-prompt")
    get_prompt.add_argument("name", help="Prompt name")
    get_prompt.add_argument(
        "--args",
        default="{}",
        help='JSON object for prompt arguments',
    )

    feature_design = subparsers.add_parser("feature-design")
    feature_design.add_argument("path", help="Requirement document path")
    feature_design.add_argument("feature_id", help="Feature identifier")
    feature_design.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of test cases to generate",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()