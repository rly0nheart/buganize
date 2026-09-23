from __future__ import annotations

import argparse
import asyncio
import typing as t
from asyncio import Task
from datetime import datetime

from ..api.client import TRACKERS, Buganize
from ..api.models import Results
from .console import console
from .output import export, pretty_print, print_table
from .symbols import FAIL, OK
from .update_checker import __pkg__, __version__, update_check

if t.TYPE_CHECKING:
    from rich.status import Status

    from ..api.models import Issue

__all__ = ["dispatch_client", "parse_args"]


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments and return the populated namespace.

    :return: Parsed arguments with the selected subcommand function in ``.func``.
    """

    parser = argparse.ArgumentParser(
        prog=__pkg__,
        description="Python client for the Google Issue Tracking system (Buganizer)",
        epilog=f"© {datetime.now().astimezone().year} Ritchie Mwewa",
    )
    parser.add_argument(
        "-t",
        "--tracker",
        action="append",
        choices=[tracker["name"] for tracker in TRACKERS],
        help="tracker name (repeatable). Defaults to all",
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
    # Commands are tracker-scoped by default; non-tracker commands (e.g.
    # ``echo``) override this so the startup banner can drop the tracker note.
    parser.set_defaults(uses_trackers=True)
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

    # echo (health check)
    echo_parser = subparsers.add_parser(
        "echo",
        help="check whether the issue tracker backend is reachable",
        description=(
            "Ping the Buganizer backend (GET /action/yes) and print its "
            "response. 'yes' means the backend is reachable and healthy; "
            "'no' means it is unreachable or returned an error."
        ),
    )
    echo_parser.set_defaults(func=cmd_echo, uses_trackers=False)

    return parser.parse_args()


async def cmd_search(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'search' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.query``, ``.per_page``, and ``.limit``.
    :param status: Rich status spinner for progress updates.
    """

    query = args.query
    per_page = args.per_page
    limit = args.limit
    tracker_label = ", ".join(args.tracker) if args.tracker else "all"

    status.update(
        f"[dim][bold]Searching [italic]{tracker_label}[/] issues for [bold green]{query}[/bold green]…[/dim]"
    )
    result = await client.search(query=query, page_size=per_page)
    issues: Results[Issue] = Results(result.issues)

    while limit is not None and result.has_more and len(issues) < limit:
        status.update(
            f"[dim]Collected [cyan]{len(issues)}[/] of [cyan]{limit}[/] issues…[/dim]"
        )
        result = await client.next_page(result)
        issues.extend(result.issues)
    if limit is not None:
        issues = Results(issues[:limit])

    console.log(
        f"{OK} Got {len(issues)} of ~{result.total_count}+ issues for '{query}'\n"
    )
    # Rich's Status redirects sys.stdout, which makes the pager (and the
    # TTY check) see a non-tty. Stop it first so paging can take over.
    status.stop()
    print_table(issues=issues)
    if args.export:
        export(output=issues, formats=args.export)

    if result.has_more:
        print()
        console.log(f"~{result.total_count - len(issues)}+ more results available")


async def cmd_issue(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'issue' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id = args.issue_id
    status.update(f"[dim]Getting issue {issue_id}…[/]")
    issue = await client.issue(issue_id=issue_id)

    status.stop()  # restore stdout so the pager works (Status redirects it)
    pretty_print(output=issue)
    if args.export:
        export(output=issue, formats=args.export)


async def cmd_issues(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'issues' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_ids``.
    :param status: Rich status spinner for progress updates.
    """

    issue_ids = args.issue_ids
    status.update(f"[dim]Getting issues {issue_ids}…[/]")
    issues = await client.issues(issue_ids=issue_ids)

    status.stop()  # restore stdout so the pager works (Status redirects it)
    print_table(issues=issues)
    if args.export:
        export(output=issues, formats=args.export)


async def cmd_comments(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'comments' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id = args.issue_id

    status.update(status=f"[dim]Getting comments for issue {issue_id}…[/]")
    result = await client.comments(issue_id=issue_id)

    status.stop()  # restore stdout so the pager works (Status redirects it)
    console.print(f"Issue #{issue_id} — {len(result.comments)} comments\n")
    pretty_print(output=result.comments)
    if args.export:
        export(output=result.comments, formats=args.export)


# noinspection PyUnusedLocal
async def cmd_echo(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'echo' subcommand: ping the backend and print its response.

    Prints a green ``✔`` when the backend is reachable and healthy
    (``echo: yes``), or a red ``✘`` when it is unreachable or returned
    an error (``echo: no``).

    :param client: Shared API client instance.
    :param args: Parsed arguments (unused).
    :param status: Rich status spinner for progress updates.
    """

    status.update("[dim]Pinging issue tracker backend…[/dim]")
    response = await client.echo()
    if response == "yes":
        console.log(f"{OK} echo: {response}")
    else:
        console.log(f"{FAIL} echo: {response}")


async def dispatch_client(args: argparse.Namespace, status: Status):
    """
    Create a single client and dispatch to the chosen subcommand.

    Runs the update check concurrently with the main command so it adds
    no extra latency.

    :param args: Parsed arguments with ``.func`` set to the subcommand handler.
    :param status: Rich status spinner for progress updates.
    """

    update_checker_task: Task = asyncio.create_task(update_check())

    async with Buganize(trackers=args.tracker, timeout=args.timeout) as client:
        await args.func(client=client, args=args, status=status)

    await update_checker_task
