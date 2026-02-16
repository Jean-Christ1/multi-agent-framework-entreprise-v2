# Typer CLI entry point for jaf
import typer
import importlib.metadata

from .scaffolder import scaffold_project

app = typer.Typer(help="JAF CLI - Jems Agent Framework")


def _get_version() -> str:
    try:
        return importlib.metadata.version("jaf-framework")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the JAF framework version and exit.",
        is_eager=True,
    ),
):
    if version:
        typer.echo(f"jaf-framework version: {_get_version()}")
        raise typer.Exit(code=0)

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)


@app.command()
def new(project_name: str):
    """Scaffold a new JAF project in a new directory."""
    scaffold_project(project_name)


@app.command()
def version():
    """Show the JAF framework version."""
    typer.echo(f"jaf-framework version: {_get_version()}")
