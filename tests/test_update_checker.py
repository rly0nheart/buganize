import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from buganize.cli import update_checker


async def test_update_check_caches_pypi_lookup_for_an_hour(tmp_path):
    """Query PyPI once, then serve the notice from the cache file.

    :param tmp_path: Temporary directory holding the cache file.
    """
    messages = []
    console = SimpleNamespace(console=SimpleNamespace(log=messages.append))
    query = AsyncMock(
        return_value={
            "success": True,
            "data": {"version": "2.0.0", "upload_time": "2020-01-01T00:00:00"},
        }
    )
    with (
        patch.object(update_checker, "CACHE_FILE", tmp_path / "cache.json"),
        patch.object(update_checker, "query_pypi", new=query),
        patch.dict(sys.modules, {"buganize.cli.console": console}),
    ):
        for _ in range(2):
            await update_checker.update_check(
                package_name="audit-test-package", package_version="1.0.0"
            )

        with patch.object(update_checker, "time", SimpleNamespace(time=lambda: 10**12)):
            await update_checker.update_check(
                package_name="audit-test-package", package_version="1.0.0"
            )

    assert query.await_count == 2  # first call, then again once the cache expired
    assert (tmp_path / "cache.json").exists()
    assert (
        messages
        == [
            "[bold blue]⬆[/bold blue] Version 1.0.0 of audit-test-package is outdated. "
            "Version 2.0.0 was released on 2020-01-01."
        ]
        * 3
    )
