# mypackage/cli.py
"""CLI для запуска построения clock tree."""

import logging
from pathlib import Path
from typing import Annotated

import typer

from .core import build_tree, compute_stats, optimize
from .parser import ConfigError, load_input

app = typer.Typer(help="Построение clock tree по конфигу")


@app.command()
def build(
    config: Annotated[Path, typer.Argument(
        exists=True, file_okay=True, dir_okay=False, readable=True,
        help="Путь к JSON-конфигу",
    )],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Строит clock tree и печатает статистику."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        cfg = load_input(config)
    except ConfigError as e:
        typer.secho(f"❌ {e}", fg=typer.colors.RED, err=True)
        for d in e.details:
            typer.echo(f"   • {d}", err=True)
        raise typer.Exit(code=1)

    typer.secho("✅ Конфиг валиден", fg=typer.colors.GREEN)

    typer.echo("🌳 Строю дерево...")
    root = build_tree(cfg)
    stats = compute_stats(root)
    typer.echo(
        f"   Узлов:      {stats.n_nodes}\n"
        f"   Приёмников: {stats.n_sinks}\n"
        f"   Буферов:    {stats.n_buffers}\n"
        f"   Глубина:    {stats.max_depth}\n"
        f"   Длина:      {stats.total_wire_length:.2f}"
    )

    typer.echo("🔁 Оптимизация...")
    result = optimize(cfg)
    typer.echo(
        f"   Итераций: {result.iterations}\n"
        f"   Cost:     {result.final_cost:.4f}\n"
        f"   Сходимость: {'да' if result.converged else 'нет'}"
    )


if __name__ == "__main__":
    app()
