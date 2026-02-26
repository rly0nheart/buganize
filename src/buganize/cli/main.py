from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import typing as t
from asyncio import Task
from datetime import datetime

from rich.logging import RichHandler

from .update_checker import update_check

if t.TYPE_CHECKING:
    from rich.status import Status

from ..api.client import Buganize, TRACKER_NAMES
from ..cli import console, __pkg__, __version__, output
from ..cli.output import EXTRA_FIELDS

__all__ = ["start"]


def resolve_fields(args: argparse.Namespace) -> t.Union[list[str], None]:
    """
    Figure out which extra fields to display based on CLI args.

    :param args: Parsed argparse namespace with .all and .show attributes.
    :return: List of field names to show, or None for defaults only.
    """

    if getattr(args, "all", False):
        return list(EXTRA_FIELDS.keys())
    if getattr(args, "fields", None):
        return args.fields
    return None


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments and return the populated namespace.

    :return: Parsed arguments with the selected subcommand function in ``.func``.
    """

    parser = argparse.ArgumentParser(
        prog=__pkg__,
        description="Python client for the Google Issue Tracking system (Buganizer)",
        epilog=f"© {datetime.now().year} Ritchie Mwewa",
    )
    parser.add_argument(
        "-t",
        "--tracker",
        action="append",
        choices=TRACKER_NAMES.keys(),
        help="tracker name (repeatable). Defaults to all",
    )
    parser.add_argument(
        "-f",
        "--fields",
        action="append",
        choices=list(EXTRA_FIELDS.keys()),
        help="extra field to display (repeatable)",
    )
    parser.add_argument(
        "-F",
        "--all-fields",
        action="store_true",
        help="show all available fields",
    )
    parser.add_argument(
        "-e",
        "--export",
        action="append",
        choices=["csv", "json"],
        help="export format (repeatable)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug logging",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        metavar="SECONDS",
        help="request timeout (default %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{__pkg__} {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    search_parser = subparsers.add_parser("search", help="search for issues")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "-n",
        "--per-page",
        type=int,
        default=25,
        choices=[25, 50, 100, 250],
        help="results per page (default: 25)",
    )
    search_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="total results to fetch, paginating as needed",
    )

    search_parser.set_defaults(func=cmd_search)

    # get
    issue_parser = subparsers.add_parser("issue", help="get a single issue")
    issue_parser.add_argument("issue_id", type=int, help="issue ID")
    issue_parser.set_defaults(func=cmd_issue)

    # batch
    issues_parser = subparsers.add_parser("issues", help="batch get issues")
    issues_parser.add_argument("issue_ids", type=int, nargs="+", help="issue IDs")
    issues_parser.set_defaults(func=cmd_issues)

    # comments
    comments_parser = subparsers.add_parser("comments", help="get comments on an issue")
    comments_parser.add_argument("issue_id", type=int, help="issue ID")
    comments_parser.set_defaults(func=cmd_comments)

    # trackers
    subparsers.add_parser("trackers", help="list available trackers")

    return parser.parse_args()


async def cmd_search(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'search' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.query``, ``.per_page``, and ``.limit``.
    :param status: Rich status spinner for progress updates.
    """

    query = args.query
    export_formats = args.export
    per_page = args.per_page
    limit = args.limit
    tracker_label = ", ".join(args.tracker) if args.tracker else "all"

    status.update(
        f"[dim][bold]Searching [italic]{tracker_label}[/] issues for [bold green]{query}[/bold green]…[/dim]"
    )
    result = await client.search(query=query, page_size=per_page)
    issues = list(result.issues)

    if limit is not None:
        if result.has_more:
            while len(issues) < limit:
                status.update(
                    f"[dim]Collected [cyan]{len(issues)}[/] of [cyan]{limit}[/] issues…[/dim]"
                )

                result = await client.next_page(result)
                issues.extend(result.issues)
        issues = issues[:limit]

    fields = resolve_fields(args=args)

    console.log(
        f"[bold green]✔[/bold green] Got {len(issues)} of ~{result.total_count}+ issues for '{query}'\n"
    )
    output.Print(data=issues).print(fields=fields)

    if args.export:
        output_format = output.Format(items=issues)
        rows = output_format.to_rows(fields=fields)
        output_save = output.Save(rows=rows)
        output_save.save(formats=export_formats)

    if result.has_more:
        console.log(f"\n~{result.total_count - len(issues)}+ more results available")


async def cmd_issue(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'issue' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id = args.issue_id
    export_formats = args.export

    status.update(f"[dim]Getting issue {issue_id}…[/]")
    # Use batch endpoint to get the issue body/description (getIssue doesn't include it).
    issues = await client.issues(issue_ids=[issue_id])
    issue = issues[0]
    fields = resolve_fields(args=args)

    output.Print(data=issue).print(fields=fields)

    if args.export:
        output_format = output.Format(items=[issue])
        rows = output_format.to_rows(fields=fields)
        output_save = output.Save(rows=rows)
        output_save.save(formats=export_formats)


async def cmd_issues(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'issues' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_ids``.
    :param status: Rich status spinner for progress updates.
    """

    issue_ids = args.issue_ids
    export_formats = args.export

    status.update(f"[dim]Getting issues {issue_ids}…[/]")
    issues = await client.issues(issue_ids=issue_ids)
    fields = resolve_fields(args=args)
    output.Print(data=issues).print(fields=fields)

    if args.export:
        output_format = output.Format(items=issues)
        rows = output_format.to_rows(fields=fields)
        output_save = output.Save(rows=rows)
        output_save.save(formats=export_formats)


async def cmd_comments(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'comments' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id = args.issue_id
    export_formats = args.export

    status.update(status=f"[dim]Getting comments for issue {issue_id}…[/]")
    comments = await client.comments(issue_id=issue_id)

    console.print(f"Issue #{issue_id} — {len(comments)} comments\n")
    output.Print(data=comments).print()

    if args.export:
        output_format = output.Format(items=comments)
        rows = output_format.to_rows()
        output_save = output.Save(rows=rows)
        output_save.save(formats=export_formats)


async def dispatch_client(args: argparse.Namespace, status: Status):
    """
    Create a single client and dispatch to the chosen subcommand.

    Runs the update check concurrently with the main command so it adds
    no extra latency.

    :param args: Parsed arguments with ``.func`` set to the subcommand handler.
    :param status: Rich status spinner for progress updates.
    """

    update_checker_task: Task = asyncio.create_task(
        update_check(package_name=__pkg__, package_version=__version__)
    )

    async with Buganize(trackers=args.tracker, timeout=args.timeout) as client:
        await args.func(client=client, args=args, status=status)

    await update_checker_task


def start():
    """
    CLI entry point. Parse arguments, configure logging, and run the subcommand.

    The ``trackers`` subcommand is handled synchronously and returns early.
    All other subcommands run through the async :func:`dispatch_client` path.
    """

    args = parse_args()

    if args.command == "trackers":
        output.Print(data=TRACKER_NAMES).trackers()
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
        with console.status("Initialising") as status:
            asyncio.run(dispatch_client(args=args, status=status))
    except KeyboardInterrupt:
        console.log(
            "[bold yellow]✘[/bold yellow] User interrupted ([bold yellow]CTRL+C[/bold yellow])"
        )
        sys.exit(0)
    except Exception as exception:
        console.log(
            f"[bold red]✘[/bold red] An error occurred: [bold red]{exception}[/bold red]"
        )
        sys.exit(1)
    finally:
        elapsed = (datetime.now() - start_time).total_seconds()
        console.log(f"[bold blue]*[/bold blue] Finished in {elapsed:.1f} seconds")
