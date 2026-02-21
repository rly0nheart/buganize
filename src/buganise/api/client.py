from __future__ import annotations

from typing import Optional

import httpx

from .models import Comment, Issue, IssueUpdatesResult, SearchResult
from .parser import (
    parse_batch_response,
    parse_issue_detail_response,
    parse_search_response,
    parse_updates_response,
)

BASE_URL = "https://issues.chromium.org/action"
DEFAULT_TRACKER_ID = "157"  # Chromium

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://issues.chromium.org",
    "Referer": "https://issues.chromium.org/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


class Buganise:
    """
    Async Python client for the Chromium Issue Tracker.

    Wraps the non-public JSON-array API at issues.chromium.org. Supports
    searching issues, fetching individual issues, batch fetching, and
    reading comments/updates.

    Can be used as an async context manager::

        async with Buganise() as client:
            result = await client.search("priority:p1")

    :param tracker_id: Tracker ID to query. Defaults to "157" (Chromium).
    :param timeout: HTTP request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        tracker_id: str = DEFAULT_TRACKER_ID,
        timeout: float = 30.0,
    ):
        self.tracker_id = tracker_id
        self._http = httpx.AsyncClient(
            headers=HEADERS,
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
        query: str = "status:open",
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> SearchResult:
        """
        Search for issues in the Chromium tracker.

        :param query: Search query string (e.g. "status:open", "component:Blink").
        :param page_size: Number of results per page (25, 50, 100, or 250).
        :param page_token: Pagination token from a previous SearchResult.next_page_token.
        :return: Matching issues, total count, and pagination token.
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        query_payload = (
            [query, None, page_size, page_token]
            if page_token
            else [query, None, page_size]
        )
        request_body = [None, None, None, None, None, [self.tracker_id], query_payload]
        url = f"{BASE_URL}/issues/list"

        # log.debug("POST %s query=%r page_size=%d", url, query, page_size)
        response = await self._http.post(url, json=request_body)
        # log.debug("Response %d (%d bytes)", response.status_code, len(response.text))
        response.raise_for_status()
        return parse_search_response(response.text, query=query, page_size=page_size)

    async def next_page(self, result: SearchResult) -> Optional[SearchResult]:
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

        :param issue_id: The issue ID (e.g. 40060244).
        :return: The issue with all available fields populated.
        """
        request_body = [issue_id, 1, 1]
        url = (
            f"{BASE_URL}/issues/{issue_id}/getIssue?currentTrackerId={self.tracker_id}"
        )

        # log.debug("POST %s issue_id=%d", url, issue_id)
        response = await self._http.post(url, json=request_body)
        # log.debug("Response %d (%d bytes)", response.status_code, len(response.text))
        response.raise_for_status()
        return parse_issue_detail_response(response.text)

    async def issues(self, issue_ids: list[int]) -> list[Issue]:
        """
        Fetch multiple issues by ID in a single request.

        :param issue_ids: List of issue IDs to fetch.
        :return: The fetched issues (order may not match input).
        """
        request_body = ["b.BatchGetIssuesRequest", None, None, [issue_ids, 2, 2]]
        url = f"{BASE_URL}/issues/batch"

        # log.debug("POST %s issue_ids=%r", url, issue_ids)
        response = await self._http.post(url, json=request_body)
        # log.debug("Response %d (%d bytes)", response.status_code, len(response.text))
        response.raise_for_status()
        return parse_batch_response(response.text)

    async def issue_updates(self, issue_id: int) -> IssueUpdatesResult:
        """
        Fetch all updates (comments and field changes) for an issue.

        Returns updates in reverse chronological order (newest first).
        Use ``result.comments`` to get just the comments in chronological order.

        :param issue_id: The issue ID to fetch updates for.
        :return: Updates, total count, and pagination token.
        """
        url = f"{BASE_URL}/issues/{issue_id}/updates?currentTrackerId={self.tracker_id}"

        # log.debug("POST %s issue_id=%d", url, issue_id)
        response = await self._http.post(url, json=[issue_id])
        # log.debug("Response %d (%d bytes)", response.status_code, len(response.text))
        response.raise_for_status()
        return parse_updates_response(response.text)

    async def comments(self, issue_id: int) -> list[Comment]:
        """
        Fetch only the comments for an issue, in chronological order.

        This is a convenience wrapper around issue_updates() that
        filters out field-change-only updates and reverses to chronological order.

        :param issue_id: The issue ID to fetch comments for.
        :return: Comments oldest-first.
        """
        result = await self.issue_updates(issue_id)
        return result.comments
