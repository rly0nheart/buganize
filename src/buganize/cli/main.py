from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import typing as t
from datetime import datetime

from rich.logging import RichHandler
from update_checker import UpdateChecker

if t.TYPE_CHECKING:
    from rich.status import Status
    from ..api.models import Comment, Issue

from ..api.client import Buganize, TRACKER_NAMES
from ..cli import console, __pkg__, __version__, output
from ..cli.output import EXTRA_FIELDS


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments and return the populated namespace.

    :return: Parsed arguments with the selected subcommand function in ``.func``.
    """

    parser = argparse.ArgumentParser(
        prog=__pkg__,
        description="Buganize: Python client for the Google Issue Tracker",
        epilog=f"© {datetime.now().year} Ritchie Mwewa",
    )
    parser.add_argument(
        "-t",
        "--tracker",
        default=None,
        metavar="TRACKER",
        help=f"tracker name ({', '.join(TRACKER_NAMES)}) or numeric ID (default: all trackers)",
    )
    parser.add_argument(
        "-e",
        "--export",
        nargs="+",
        choices=["csv", "json"],
        metavar="FORMAT",
        help="export formats: %(choices)s (one or more)",
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
    _add_fields_args(search_parser)
    search_parser.set_defaults(func=cmd_search)

    # get
    issue_parser = subparsers.add_parser("issue", help="get a single issue")
    issue_parser.add_argument("issue_id", type=int, help="issue ID")
    _add_fields_args(issue_parser)
    issue_parser.set_defaults(func=cmd_issue)

    # batch
    issues_parser = subparsers.add_parser("issues", help="batch get issues")
    issues_parser.add_argument("issue_ids", type=int, nargs="+", help="issue IDs")
    _add_fields_args(issues_parser)
    issues_parser.set_defaults(func=cmd_issues)

    # comments
    comments_parser = subparsers.add_parser("comments", help="get comments on an issue")
    comments_parser.add_argument("issue_id", type=int, help="issue ID")
    comments_parser.set_defaults(func=cmd_comments)

    return parser.parse_args()


def check_updates(status: Status):
    """
    Check for updates available

    :param status: Rich status spinner for progress updates.
    """

    status.update("[dim]Checking for updates[yellow]…[/yellow][/dim]")
    checker = UpdateChecker()
    result = checker.check(package_name=__pkg__, package_version=__version__)
    if result:
        console.print(result)


def _resolve_fields(args: argparse.Namespace) -> t.Union[list[str], None]:
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


def _print_issue_detail(issue: Issue, fields: t.Optional[list[str]] = None):
    """
    Print a single issue with full detail.

    Always shows the basic fields. Extra fields are shown only when
    requested via --fields or --all-fields.

    :param issue: The issue to display.
    :param fields: Extra field names to include.
    """

    enabled_fields = set(fields or [])
    all_fields = bool(enabled_fields)

    def is_shown(field_name: str) -> bool:
        return all_fields or field_name in enabled_fields

    # Basic fields (always shown).
    console.print(f"Issue #{issue.id}")
    console.print(f"  URL:           {issue.url}")
    console.print(f"  Title:         {issue.title}")
    console.print(f"  Status:        {issue.status.name}")
    console.print(f"  Priority:      {issue.priority.name}")
    if issue.issue_type:
        console.print(f"  Type:          {issue.issue_type.name}")
    if issue.reporter:
        console.print(f"  Reporter:      {issue.reporter}")
    if issue.owner:
        console.print(f"  Owner:         {issue.owner}")
    if issue.component_id:
        console.print(f"  Component:     {issue.component_id}")
    if issue.created_at:
        console.print(f"  Created:       {issue.created_at.isoformat()}")
    if issue.modified_at:
        console.print(f"  Modified:      {issue.modified_at.isoformat()}")
    console.print(f"  Comments:      {issue.comment_count}")

    # Extra fields (only when requested).
    if is_shown("verifier") and issue.verifier:
        console.print(f"  Verifier:      {issue.verifier}")
    if is_shown("tags") and issue.component_tags:
        console.print(f"  Comp. Tags:    {', '.join(issue.component_tags)}")
    if is_shown("ancestor_tags") and issue.component_ancestor_tags:
        console.print(f"  Ancestor Tags: {', '.join(issue.component_ancestor_tags)}")
    if is_shown("labels") and issue.labels:
        console.print(f"  Labels:        {', '.join(issue.labels)}")
    if is_shown("os") and issue.os:
        console.print(f"  OS:            {', '.join(issue.os)}")
    if is_shown("milestone") and issue.milestone:
        console.print(f"  Milestone:     {', '.join(issue.milestone)}")
    if is_shown("ccs") and issue.ccs:
        console.print(f"  CCs:           {', '.join(issue.ccs)}")
    if is_shown("hotlists") and issue.hotlist_ids:
        console.print(
            f"  Hotlists:      {', '.join(str(h) for h in issue.hotlist_ids)}"
        )
    if is_shown("blocking") and issue.blocking_issue_ids:
        console.print(
            f"  Blocking:      {', '.join(str(b) for b in issue.blocking_issue_ids)}"
        )
    if is_shown("cve") and issue.cve:
        console.print(f"  CVE:           {', '.join(issue.cve)}")
    if is_shown("cwe") and issue.cwe_id is not None:
        console.print(f"  CWE ID:        {int(issue.cwe_id)}")
    if is_shown("build") and issue.build_number:
        console.print(f"  Build:         {issue.build_number}")
    if is_shown("introduced_in") and issue.introduced_in:
        console.print(f"  Introduced In: {issue.introduced_in}")
    if is_shown("merge") and issue.merge:
        console.print(f"  Merge:         {', '.join(issue.merge)}")
    if is_shown("merge_request") and issue.merge_request:
        console.print(f"  Merge Req.:    {', '.join(issue.merge_request)}")
    if is_shown("release_block") and issue.release_block:
        console.print(f"  Release Block: {', '.join(issue.release_block)}")
    if is_shown("notice") and issue.notice:
        console.print(f"  Notice:        {issue.notice}")
    if is_shown("flaky_test") and issue.flaky_test:
        console.print(f"  Flaky Test:    {issue.flaky_test}")
    if is_shown("est_days") and issue.estimated_days is not None:
        console.print(f"  Est. Days:     {issue.estimated_days}")
    if is_shown("next_action") and issue.next_action:
        console.print(f"  Next Action:   {issue.next_action}")
    if is_shown("vrp_reward") and issue.vrp_reward is not None:
        console.print(f"  VRP Reward:    {issue.vrp_reward}")
    if is_shown("irm_link") and issue.irm_link:
        console.print(f"  IRM Link:      {issue.irm_link}")
    if is_shown("sec_release") and issue.security_release:
        console.print(f"  Sec. Release:  {', '.join(issue.security_release)}")
    if is_shown("fixed_by") and issue.fixed_by_code_changes:
        console.print(f"  Fixed By:      {', '.join(issue.fixed_by_code_changes)}")
    if is_shown("verified") and issue.verified_at:
        console.print(f"  Verified:      {issue.verified_at.isoformat()}")
    if is_shown("stars"):
        console.print(f"  Stars:         {issue.star_count}")
    if is_shown("last_modifier") and issue.last_modifier:
        console.print(f"  Last Modifier: {issue.last_modifier}")
    if all_fields and issue.custom_fields:
        console.print(f"  Other Fields:")
        for key, value in issue.custom_fields.items():
            console.print(f"    {key}: {value}")


def _print_comments(comments: list[Comment]):
    """
    Print a list of comments in a readable thread format.

    :param comments: Comments to display (expected in chronological order).
    """

    if not comments:
        console.print("No comments.")
        return
    for i, comment in enumerate(comments):
        author = comment.author or "unknown"
        timestamp = (
            comment.timestamp.strftime("%Y-%m-%d %H:%M UTC")
            if comment.timestamp
            else "unknown date"
        )
        console.print(f"#{comment.comment_number}  {author}  ({timestamp})")
        console.print()
        for line in comment.body.splitlines():
            console.print(f"    {line}")
        if i < len(comments) - 1:
            console.print()
            console.print(f"  {'─' * 72}")
            console.print()


def _add_fields_args(subparser: argparse.ArgumentParser):
    """
    Add the --fields and --all-fields flags to a subcommand parser.

    :param subparser: The argparse subparser to add the flags to.
    """

    subparser.add_argument(
        "-f",
        "--fields",
        nargs="+",
        metavar="FIELD",
        choices=list(EXTRA_FIELDS.keys()),
        help="extra fields to display. such as: %(choices)s",
    )
    subparser.add_argument(
        "-F",
        "--all-fields",
        action="store_true",
        help="Show all available fields",
    )


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
    tracker = args.tracker.title() if args.tracker else "Google"

    status.update(
        f"[dim]Searching for [bold green]{query}[/bold green] on "
        f"[bold]{tracker} Issue Tracker[/bold][yellow]…[/yellow][/dim]"
    )
    result = await client.search(query=query, page_size=per_page)
    issues = list(result.issues)

    if limit is not None:
        while len(issues) < limit and result.has_more:
            status.update(
                f"[dim][bold]{tracker}[/bold]: collected [cyan]{len(issues)}[/]/[cyan]{limit}[/] results[yellow]…[/][/dim]"
            )

            result = await client.next_page(result)
            issues.extend(result.issues)
        issues = issues[:limit]

    fields = _resolve_fields(args=args)

    console.print(
        f"[bold green]✔[/bold green] Returned {len(issues)} of ~{result.total_count}+ results for '{query}'\n"
    )

    output_print = output.Table(items=issues)
    output_print.print(fields=fields)

    if args.export:
        output_format = output.Format(items=issues)
        rows = output_format.to_rows(fields=fields)
        output_save = output.Save(rows=rows)
        output_save.save(formats=export_formats)

    if result.has_more:
        console.print(f"\n~{result.total_count - len(issues)}+ more results available")


async def cmd_issue(client: Buganize, args: argparse.Namespace, status: Status):
    """
    Handle the 'issue' subcommand.

    :param client: Shared API client instance.
    :param args: Parsed arguments with ``.issue_id``.
    :param status: Rich status spinner for progress updates.
    """

    issue_id = args.issue_id
    export_formats = args.export

    status.update(f"[dim]Getting issue {issue_id}[yellow]…[/][/]")
    issue = await client.issue(issue_id=args.issue_id)
    fields = _resolve_fields(args=args)

    _print_issue_detail(issue=issue, fields=fields)

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

    status.update(f"[dim]Getting issues {issue_ids}[yellow]…[/][/]")
    issues = await client.issues(issue_ids=issue_ids)
    fields = _resolve_fields(args=args)

    output_print = output.Table(items=issues)
    output_print.print(fields=fields)

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

    status.update(status=f"[dim]Getting comments for issue {issue_id}[yellow]…[/][/]")
    comments = await client.comments(issue_id=issue_id)

    console.print(f"Issue #{issue_id} — {len(comments)} comments\n")
    _print_comments(comments=comments)

    if args.export:
        output_format = output.Format(items=comments)
        rows = output_format.to_rows()
        output_save = output.Save(rows=rows)
        output_save.save(formats=export_formats)


async def dispatch_client(args: argparse.Namespace, status: Status):
    """
    Create a single client and dispatch to the chosen subcommand.

    :param args: Parsed arguments with ``.func`` set to the subcommand handler.
    :param status: Rich status spinner for progress updates.
    """

    tracker_id = None
    if args.tracker:
        tracker_id = TRACKER_NAMES.get(args.tracker.lower(), args.tracker)
    async with Buganize(tracker_id=tracker_id, timeout=args.timeout) as client:
        await args.func(client=client, args=args, status=status)


def start():
    """
    CLI entry point. Parse arguments, configure logging, and run the subcommand.
    """

    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        handlers=[RichHandler(markup=True, show_level=True)],
    )

    try:
        with console.status("Initialising") as status:
            check_updates(status=status)
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
