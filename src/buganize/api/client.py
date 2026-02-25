from __future__ import annotations

import random
import typing as t
import warnings

import httpx

from .parser import (
    parse_batch_response,
    parse_issue_detail_response,
    parse_search_response,
    parse_updates_response,
)

if t.TYPE_CHECKING:
    from httpx import Response
    from .models import Comment, Issue, IssueUpdatesResult, SearchResult

__all__ = ["Buganize", "TRACKER_NAMES"]

TRACKER_NAMES: dict[str, tuple[str, str]] = {
    "pigweed": ("1", "https://issues.pigweed.dev"),
    "gerrit": ("27", "https://issues.gerritcodereview.com"),
    "git": ("53", "https://git.issues.gerritcodereview.com"),
    "skia": ("79", "https://issues.skia.org"),
    "webrtc": ("105", "https://issues.webrtc.org"),
    "libyuv": ("131", "https://libyuv.issues.chromium.org"),
    "chromium": ("157", "https://issues.chromium.org"),
    "fuchsia": ("183", "https://issues.fuchsia.dev"),
    "angle": ("235", "https://issues.angleproject.org"),
    "aomedia": ("261", "https://aomedia.issues.chromium.org"),
    "webm": ("287", "https://issues.webmproject.org"),
    "gn": ("339", "https://gn.issues.chromium.org"),
    "project-zero": ("365", "https://project-zero.issues.chromium.org"),
    "oss-fuzz": ("391", "https://issues.oss-fuzz.com"),
}

USER_AGENTS: list[str] = [
    "Mozilla/5.0 (compatible; Google-InspectionTool/1.0;)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/87.0.4256.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/91.0.4443.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/104.0.5089.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/106.0.5227.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/109.0.5414.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/110.0.5471.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/111.0.5553.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/112.0.5615.165 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/135.0.6367.201 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/135.0.7049.84 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/135.0.7049.95 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/135.0.7049.114 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7126.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7127.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7128.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7129.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7130.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7131.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7139.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7140.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7141.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7142.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7143.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7144.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7145.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7146.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7147.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7148.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7149.0 Safari/537.36",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/137.0.7150.0 Safari/537.36",
]


class Buganize:
    """
    Async Python client for the Google Issue Tracker.

    Wraps the non-public JSON-array API at issuetracker.google.com. Supports
    searching issues, fetching individual issues, batch fetching, and
    reading comments/updates.

    Can be used as an async context manager::

        async with Buganize() as client:
            result = await client.search("priority:p1")

    :param trackers: Trackers to query. Accepts names (e.g. ``["chromium"]``)
        or numeric ID strings (e.g. ``["157"]``). Names are resolved via
        ``TRACKER_NAMES``. Pass multiple to search across specific trackers.
        Defaults to None (search all public trackers).
    :param timeout: HTTP request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        trackers: t.Optional[list[str | int]] = None,
        timeout: float = 30.0,
    ):
        self.base_endpoint = "https://issuetracker.google.com/action"

        self.tracker_ids: t.Optional[list[str]] = None
        if trackers:
            self.tracker_ids = [
                TRACKER_NAMES.get(name, (name, None))[0] for name in trackers
            ]

        self._http = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Origin": "https://issuetracker.google.com",
                "Referer": "https://issuetracker.google.com/",
                "User-Agent": random.choice(USER_AGENTS),
            },
            timeout=timeout,
        )

    async def close(self):
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def search(
        self,
        query: str,
        page_size: int = 50,
        page_token: t.Optional[str] = None,
    ) -> SearchResult:
        """
        Search for issues in the Google Issue Tracker.

        :param query: Search query string (e.g. "status:open", "component:Blink").
        :param page_size: Number of results per page (25, 50, 100, or 250).
        :param page_token: Pagination token from a previous SearchResult.next_page_token.
        :return: Matching issues, total count, and pagination token.
        """

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        query_payload: list = (
            [query, None, page_size, page_token]
            if page_token
            else [query, None, page_size]
        )
        tracker_filter = self.tracker_ids if self.tracker_ids else None
        request_body: list = [
            None,
            None,
            None,
            None,
            None,
            tracker_filter,
            query_payload,
        ]
        url: str = f"{self.base_endpoint}/issues/list"

        response: Response = await self._http.post(url, json=request_body)
        response.raise_for_status()
        return parse_search_response(
            raw_text=response.text, query=query, page_size=page_size
        )

    async def next_page(self, result: SearchResult) -> t.Optional[SearchResult]:
        """
        Fetch the next page of a search result.

        :param result: A previous SearchResult.
        :return: The next page of results, or None if there are no more pages.
        """

        if not result.has_more:
            return None

        return await self.search(
            query=result.query,
            page_size=result.page_size,
            page_token=result.next_page_token,
        )

    async def issue(self, issue_id: int) -> Issue:
        """
        Fetch a single issue by its numeric ID.

        .. deprecated::
            This method does not return the issue body/description
            (``TOP[43]`` is always ``None``). Use :meth:`issues` with a
            single-element list instead::

                issues = await client.issues([issue_id])
                issue_with_body = issues[0]

        :param issue_id: The issue ID (e.g. 40060244).
        :return: The issue with all available fields populated (except ``body``).
        """
        # FIXME: getIssue does not populate TOP[43] (issue body/description).
        # Use the batch endpoint (client.issues([id])) if the body is needed.
        warnings.warn(
            "issue() is deprecated and may be removed in a future version. "
            "Use issues([issue_id])[0] instead, which also returns the issue body.",
            DeprecationWarning,
            stacklevel=2,
        )

        request_body: list = [issue_id, 1, 1]
        url: str = f"{self.base_endpoint}/issues/{issue_id}/getIssue"

        # FIXME: currentTrackerId appears unnecessary — issue ID alone resolves correctly.
        # params=QueryParams({"currentTrackerId": self.tracker_ids[0] if self.tracker_ids else None}),
        response: Response = await self._http.post(url=url, json=request_body)

        response.raise_for_status()
        return parse_issue_detail_response(raw_text=response.text)

    async def issues(self, issue_ids: list[int]) -> list[Issue]:
        """
        Fetch multiple issues by ID in a single request.

        :param issue_ids: List of issue IDs to fetch.
        :return: The fetched issues (order may not match input).
        """

        request_body: list = ["b.BatchGetIssuesRequest", None, None, [issue_ids, 2, 2]]
        url: str = f"{self.base_endpoint}/issues/batch"

        response: Response = await self._http.post(url, json=request_body)
        response.raise_for_status()
        return parse_batch_response(raw_text=response.text)

    async def issue_updates(self, issue_id: int) -> IssueUpdatesResult:
        """
        Fetch all updates (comments and field changes) for an issue.

        Returns updates in reverse chronological order (newest first).
        Use ``result.comments`` to get just the comments in chronological order.

        :param issue_id: The issue ID to fetch updates for.
        :return: Updates, total count, and pagination token.
        """

        url: str = f"{self.base_endpoint}/issues/{issue_id}/updates"
        # FIXME: currentTrackerId appears unnecessary — issue ID alone resolves correctly.
        # params=QueryParams({"currentTrackerId": self.tracker_ids[0] if self.tracker_ids else None}),
        response: Response = await self._http.post(url=url, json=[issue_id])
        response.raise_for_status()

        return parse_updates_response(raw_text=response.text)

    async def comments(self, issue_id: int) -> list[Comment]:
        """
        Fetch only the comments for an issue, in chronological order.

        This is a convenience wrapper around issue_updates() that
        filters out field-change-only updates and reverses to chronological order.

        :param issue_id: The issue ID to fetch comments for.
        :return: Comments oldest-first.
        """

        result: IssueUpdatesResult = await self.issue_updates(issue_id=issue_id)
        return result.comments
