import sys
import asyncio
import logging
from datetime import datetime
from rich.logging import RichHandler

from .commands import dispatch_client, parse_args
from .console import console
from .output import pretty_print
from .symbols import INFO, WARN
from .update_checker import __version__
from ..api.client import TRACKERS


def start():
    """
    CLI entry point.
    """

    args = parse_args()

    if args.command == "trackers":
        pretty_print(output=TRACKERS)
        console.print(f"\n{len(TRACKERS)} trackers available")
        return

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        handlers=[RichHandler(markup=True, show_level=True)],
    )

    start_time = datetime.now()
    try:
        if getattr(args, "uses_trackers", True):
            tracker_label = ", ".join(args.tracker) if args.tracker else "all"
            plural = "s" if not args.tracker or len(args.tracker) > 1 else ""
            tracker_note = f" (w/ tracker{plural}: [italic]{tracker_label}[/italic])"
        else:
            tracker_note = ""
        console.log(
            f"{INFO} Started buganize CLI {__version__}{tracker_note} "
            f"at {datetime.now().strftime('%x %X')}"
        )
        with console.status("[dim]Initialising…[/dim]") as status:
            asyncio.run(dispatch_client(args=args, status=status))
    except KeyboardInterrupt:
        console.log(f"{WARN} User interrupted ([bold yellow]CTRL+C[/bold yellow])")
        sys.exit(0)
    finally:
        elapsed = (datetime.now() - start_time).total_seconds()
        console.log(f"{INFO} Finished in {elapsed:.1f} seconds")
