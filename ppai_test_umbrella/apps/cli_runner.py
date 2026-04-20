# # from __future__ import annotations

# # import typer
# # import os

# # from ppai_test_umbrella.modules.prototype_service import PrototypeService
# # from ppai_test_umbrella.modules.execution_service import ExecutionService

# # app = typer.Typer(help="PPAI CLI Runner")

# # service = PrototypeService()
# # executor = ExecutionService()


# # @app.command()
# # def run(
# #     file: str = typer.Argument(..., help="Path to requirement file (PDF/TXT/etc)"),
# #     feature: str = typer.Option(..., "--feature", "-f", help="Feature ID"),
# #     count: int = typer.Option(10, "--count", "-c", help="Number of testcases"),
# #     execute: bool = typer.Option(False, "--execute", "-e", help="Execute after generation"),
# #     mode: str = typer.Option("dry_run", "--mode", "-m", help="Execution mode: dry_run/live"),
# # ):
# #     """
# #     Generate testcases for a feature and optionally execute them
# #     """

# #     typer.echo(f"\n📄 Processing file: {file}")
# #     typer.echo(f"🎯 Feature: {feature}")

# #     # Step 1: Generate
# #     result = service.generate_test_cases_for_feature(file, feature, count)

# #     output_path = result["output_path"]
# #     filename = os.path.basename(output_path)

# #     typer.echo(f"\n✅ Testcases generated:")
# #     typer.echo(f"📁 {output_path}")

# #     # Step 2: Execute (optional)
# #     if execute:
# #         typer.echo("\n⚡ Executing generated testcases...\n")

# #         exec_result = executor.execute_generated_output(filename, mode)

# #         run_id = exec_result["run_id"]

# #         typer.echo("📊 Execution Result:")
# #         typer.echo(f"Status: {exec_result['status']}")
# #         typer.echo(f"Run ID: {run_id}")

# #         typer.echo("\n📁 Report location:")
# #         typer.echo(f"runtime_data/generated/executions/{run_id}/report.json")

# #     typer.echo("\n🎉 Done!")


# # @app.command()
# # def list():
# #     """
# #     List generated outputs
# #     """
# #     items = service.list_generated_outputs()
# #     for item in items:
# #         typer.echo(item)


# # @app.command()
# # def exec(
# #     name: str = typer.Argument(..., help="Generated JSON file name"),
# #     mode: str = typer.Option("dry_run", "--mode"),
# # ):
# #     """
# #     Execute a generated file
# #     """
# #     result = executor.execute_generated_output(name, mode)

# #     typer.echo(f"\nStatus: {result['status']}")
# #     typer.echo(f"Run ID: {result['run_id']}")


# # @app.command()
# # def report(run_id: str):
# #     """
# #     Read execution report
# #     """
# #     data = executor.read_execution_report(run_id)
# #     typer.echo(data)


# # if __name__ == "__main__":
# #     app()

# from __future__ import annotations

# import os
# import typer

# from ppai_test_umbrella.modules.prototype_service import PrototypeService
# from ppai_test_umbrella.modules.execution_service import ExecutionService

# app = typer.Typer(help="PPAI CLI Runner")

# service = PrototypeService()
# executor = ExecutionService()


# @app.command()
# def run(
#     file: str = typer.Argument(..., help="Path to requirement file"),
#     feature: str = typer.Option(..., "--feature", "-f", help="Feature ID"),
#     count: int = typer.Option(10, "--count", "-c", help="Number of testcases"),
#     execute: bool = typer.Option(False, "--execute", "-e", help="Execute after generation"),
#     mode: str = typer.Option("dry_run", "--mode", "-m", help="dry_run/live"),
# ):
#     typer.echo(f"\nProcessing file: {file}")
#     typer.echo(f"Feature: {feature}")

#     result = service.generate_test_cases_for_feature(file, feature, count)
#     output_path = result["output_path"]
#     filename = os.path.basename(output_path)

#     typer.echo("\nGenerated output:")
#     typer.echo(output_path)

#     if execute:
#         typer.echo(f"\nExecuting in mode={mode} ...")
#         exec_result = executor.execute_generated_output(filename, mode)
#         typer.echo(f"Status: {exec_result['status']}")
#         typer.echo(f"Run ID: {exec_result['run_id']}")
#         typer.echo(f"Summary: {exec_result['summary']}")

#     typer.echo("\nDone.")


# @app.command("list-generated")
# def list_generated():
#     items = service.list_generated_outputs()
#     for item in items:
#         typer.echo(item)


# @app.command("list-exec")
# def list_exec():
#     items = executor.list_executable_generated_outputs()
#     for item in items:
#         typer.echo(item)


# @app.command("exec")
# def exec_file(
#     name: str = typer.Argument(..., help="Generated JSON file name"),
#     mode: str = typer.Option("dry_run", "--mode", "-m"),
# ):
#     result = executor.execute_generated_output(name, mode)
#     typer.echo(f"Status: {result['status']}")
#     typer.echo(f"Run ID: {result['run_id']}")
#     typer.echo(f"Summary: {result['summary']}")


# @app.command("report")
# def report(run_id: str):
#     typer.echo(executor.read_execution_report(run_id))


# if __name__ == "__main__":
#     app()

from __future__ import annotations

import os
import typer

from ppai_test_umbrella.modules.prototype_service import PrototypeService
from ppai_test_umbrella.modules.execution_service import ExecutionService

app = typer.Typer(help="PPAI CLI Runner")

service = PrototypeService()
executor = ExecutionService()


@app.command()
def run(
    file: str = typer.Argument(..., help="Path to requirement file"),
    feature: str = typer.Option(..., "--feature", "-f", help="Feature ID"),
    count: int = typer.Option(10, "--count", "-c", help="Number of testcases"),
    execute: bool = typer.Option(False, "--execute", "-e", help="Execute after generation"),
    mode: str = typer.Option("dry_run", "--mode", "-m", help="dry_run/live"),
    config: str = typer.Option("", "--config", help="Path to YAML runtime config"),
):
    typer.echo(f"\nProcessing file: {file}")
    typer.echo(f"Feature: {feature}")

    result = service.generate_test_cases_for_feature(file, feature, count)
    output_path = result["output_path"]
    filename = os.path.basename(output_path)

    typer.echo("\nGenerated output:")
    typer.echo(output_path)

    if execute:
        typer.echo(f"\nExecuting in mode={mode} ...")
        exec_result = executor.execute_generated_output(
            filename,
            mode,
            config_path=config or None,
        )
        typer.echo(f"Status: {exec_result['status']}")
        typer.echo(f"Run ID: {exec_result['run_id']}")
        typer.echo(f"Summary: {exec_result['summary']}")

    typer.echo("\nDone.")


@app.command("exec")
def exec_file(
    name: str = typer.Argument(..., help="Generated JSON file name"),
    mode: str = typer.Option("dry_run", "--mode", "-m"),
    config: str = typer.Option("", "--config", help="Path to YAML runtime config"),
):
    result = executor.execute_generated_output(
        name,
        mode,
        config_path=config or None,
    )
    typer.echo(f"Status: {result['status']}")
    typer.echo(f"Run ID: {result['run_id']}")
    typer.echo(f"Summary: {result['summary']}")


@app.command("report")
def report(run_id: str):
    typer.echo(executor.read_execution_report(run_id))


@app.command("list-generated")
def list_generated():
    items = service.list_generated_outputs()
    for item in items:
        typer.echo(item)


@app.command("list-exec")
def list_exec():
    items = executor.list_executable_generated_outputs()
    for item in items:
        typer.echo(item)


if __name__ == "__main__":
    app()