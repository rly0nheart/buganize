"""
Console output for the CLI.

Results print as their dataclasses through a pager, so bulk output scrolls
instead of flooding the terminal. Writing them to file is left to the models'
own ``to_json()``/``to_csv()``.
"""

import typing as t
from contextlib import nullcontext
from datetime import datetime

from rich.pretty import Pretty

from .console import console
from .symbols import OK, WARN
from ..api.models import Exportable, Results

__all__ = ["export", "pretty_print"]


def pretty_print(output: t.Any):
    """
    Show a result, paging it.

    A list prints one item per block, blank-line separated, so it stays readable
    while scrolling. The pager needs a terminal, so a redirected run prints
    straight through instead. An empty result prints a short note.

    :param output: A single item, or a list of them.
    """

    if not output:
        console.log("No results.")
        return

    context = console.pager(styles=True) if console.is_terminal else nullcontext()
    if not console.is_terminal:
        console.print(f"{WARN} Not a TTY — output won't be paged.")

    with context:
        if isinstance(output, list):
            for index, item in enumerate(output):
                if index:
                    console.print()
                console.print(Pretty(item))
        else:
            console.print(Pretty(output))


def export(output: Exportable | Results[Exportable], formats: list[str]):
    """
    Write a result to timestamped files, one per format.

    Files land in the working directory as ``buganize-<timestamp>.<format>``.

    :param output: A single item, or a list of them.
    :param formats: Format strings, each one of ``"csv"`` or ``"json"``.
    """

    if not output:
        return

    base = f"buganize-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    for fmt in formats:
        if fmt == "json":
            console.print(f"\n{OK} JSON exported to {output.to_json(f'{base}.json')}")
        elif fmt == "csv":
            console.print(f"\n{OK} CSV exported to {output.to_csv(f'{base}.csv')}")
        else:
            continue
