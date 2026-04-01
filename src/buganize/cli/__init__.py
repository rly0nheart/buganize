import sys
from importlib.metadata import version

__pkg__ = "buganize"
__version__ = version(__pkg__)


def start():
    """
    CLI entry point. Requires the ``cli`` extra (``pip install buganize[cli]``)
    which provides `rich <https://rich.readthedocs.io>`_. Exits with a
    helpful message if the dependency is missing.

    The ``trackers`` subcommand is handled synchronously and returns early.
    All other subcommands run through the async :func:`dispatch_client` path.
    """

    try:
        from rich.console import Console
    except ImportError:
        print(
            f"{__pkg__} {__version__}: If you wish to run {__pkg__} as a CLI tool, "
            f"you will need to install the 'cli' extra by running 'pip install buganize[cli]'"
        )
        sys.exit(1)

    import asyncio
    import logging
    from datetime import datetime

    from rich.logging import RichHandler

    from . import output_handler
    from .commands import dispatch_client, parse_args
    from .console import console
    from ..api.client import TRACKERS

    args = parse_args()

    if args.command == "trackers":
        output_handler.print_trackers(TRACKERS)
        return

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        handlers=[RichHandler(markup=True, show_level=True)],
    )

    start_time = datetime.now()
    try:
        console.log(
            f"[bold blue]*[/bold blue] Started buganize CLI {__version__} "
            f"(w/ tracker{'s' if not args.tracker or len(args.tracker) > 1 else ''}: [italic]"
            f"{', '.join(args.tracker) if args.tracker else 'all'}"
            f") at {datetime.now().strftime('%x %X')}"
        )
        with console.status("[dim]Initialising…[/dim]") as status:
            asyncio.run(dispatch_client(args=args, status=status))
    except KeyboardInterrupt:
        console.log(
            "[bold yellow]✘[/bold yellow] User interrupted ([bold yellow]CTRL+C[/bold yellow])"
        )
        sys.exit(0)

    finally:
        elapsed = (datetime.now() - start_time).total_seconds()
        console.log(f"[bold blue]*[/bold blue] Finished in {elapsed:.1f} seconds")
