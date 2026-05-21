"""Bridge the async Buganize client to the GTK main loop.

The Buganize client is httpx-based and async. GTK needs work to happen on the
main thread. We run the async call in a worker thread via asyncio.run, then
post the result back via GLib.idle_add.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable

from gi.repository import GLib

from buganize import Buganize, SearchResult

# Callback signature: (result, error, was_next_page_request) -> bool (GLib idle return)
SearchCallback = Callable[[SearchResult | None, Exception | None, bool], bool]


def run_search(
    *,
    query: str,
    page_size: int,
    page_token: str | None,
    trackers: list[str] | None,
    callback: SearchCallback,
) -> None:
    """
    Run a Buganize search on a background thread and deliver the result to
    ``callback`` on the GTK main loop.

    :param query: Search query string (e.g. ``"status:open priority:p1"``).
    :param page_size: Results per page passed to the client.
    :param page_token: Pagination token from a previous result, or ``None``
        for the first page.
    :param trackers: Tracker slugs to scope the search, or ``None`` for all.
    :param callback: ``(result, error, was_next_page_request) -> bool``
        invoked on the main loop. ``error`` is ``None`` on success.
    """

    def worker() -> None:
        result: SearchResult | None = None
        err: Exception | None = None
        try:

            async def go() -> SearchResult:
                async with Buganize(trackers=trackers) as client:
                    return await client.search(
                        query, page_size=page_size, page_token=page_token
                    )

            result = asyncio.run(go())
        except Exception as exc:  # noqa: BLE001
            err = exc

        GLib.idle_add(callback, result, err, page_token is not None)

    threading.Thread(target=worker, daemon=True).start()
