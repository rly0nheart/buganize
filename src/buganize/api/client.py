import random
import typing

import httpx

from .parser import (
    parse_batch_response,
    parse_comments_response,
    parse_issue_detail_response,
    parse_search_response,
    parse_updates_response,
)

if typing.TYPE_CHECKING:
    from httpx import Response
    from .models import CommentsResult, Issue, IssueUpdatesResult, SearchResult

__all__ = ["Buganize", "TRACKERS"]

TRACKERS: list[dict[str, str | int]] = [
    {"id": 1, "name": "pigweed", "url": "https://issues.pigweed.dev"},
    {"id": 27, "name": "gerrit", "url": "https://issues.gerritcodereview.com"},
    {"id": 53, "name": "git", "url": "https://git.issues.gerritcodereview.com"},
    {"id": 79, "name": "skia", "url": "https://issues.skia.org"},
    {"id": 105, "name": "webrtc", "url": "https://issues.webrtc.org"},
    {"id": 131, "name": "libyuv", "url": "https://libyuv.issues.chromium.org"},
    {"id": 157, "name": "chromium", "url": "https://issues.chromium.org"},
    {"id": 183, "name": "fuchsia", "url": "https://issues.fuchsia.dev"},
    {"id": 235, "name": "angle", "url": "https://issues.angleproject.org"},
    {"id": 261, "name": "aomedia", "url": "https://aomedia.issues.chromium.org"},
    {"id": 287, "name": "webm", "url": "https://issues.webmproject.org"},
    {"id": 339, "name": "gn", "url": "https://gn.issues.chromium.org"},
    {
        "id": 365,
        "name": "project-zero",
        "url": "https://project-zero.issues.chromium.org",
    },
    {"id": 391, "name": "oss-fuzz", "url": "https://issues.oss-fuzz.com"},
]

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
        ``TRACKERS``. Pass multiple to search across specific trackers.
        Defaults to None (search all public trackers).
    :param timeout: HTTP request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        trackers: list[str | int] = None,
        timeout: float = 30.0,
    ):
        self.base_endpoint = "https://issuetracker.google.com/action"

        self.tracker_ids: list[str] | None = None
        if trackers:
            tracker_by_name = {tracker["name"]: tracker["id"] for tracker in TRACKERS}
            self.tracker_ids = [tracker_by_name.get(name, name) for name in trackers]

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

    async def is_healthy(self) -> bool:
        """
        Check if the issue tracker backend is reachable.

        Hits the ``/action/yes`` endpoint which returns the literal
        string ``yes`` on success. Works on all tracker domains.

        :return: True if the backend responded with ``yes``, False otherwise.
        """

        url = f"{self.base_endpoint}/yes"
        try:
            response: Response = await self._http.get(url)
            return response.status_code == 200 and response.text.strip() == "yes"
        except httpx.HTTPError:
            return False

    async def search(
        self,
        query: str,
        page_size: int = 50,
        page_token: str | None = None,
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

    async def next_page(self, result: SearchResult) -> SearchResult | None:
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

        Returns all fields including the issue body/description.

        :param issue_id: The issue ID (e.g. 40060244).
        :return: The fully populated issue.
        """

        request_body: list = [issue_id, 2, 1]
        url: str = f"{self.base_endpoint}/issues/{issue_id}/getIssue"

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

    async def comments(
        self,
        issue_id: int,
        sort_order: str = "ASC",
        page_size: int = 500,
        page_token: str | None = None,
    ) -> CommentsResult:
        """
        Fetch comments for an issue.

        Returns only text comments (no field-change-only updates).
        Use :meth:`issue_updates` if you need field changes.

        :param issue_id: The issue ID to fetch comments for.
        :param sort_order: ``"ASC"`` for oldest-first, ``"DESC"`` for newest-first.
        :param page_size: Number of comments per page (max 500).
        :param page_token: Pagination token from a previous CommentsResult.
        :return: Comments and pagination info.
        """

        url: str = f"{self.base_endpoint}/issues/{issue_id}/listComments"
        request_body: list = [issue_id, sort_order, page_size]
        if page_token:
            request_body.append(page_token)

        response: Response = await self._http.post(url, json=request_body)
        response.raise_for_status()
        return parse_comments_response(raw_text=response.text)
