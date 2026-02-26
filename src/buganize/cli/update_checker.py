"""
Module that checks if there is an updated version of a package available.
"""

import os
import pickle
import re
import time
import typing as t
from datetime import UTC
from datetime import datetime
from functools import wraps
from tempfile import gettempdir

import httpx

from . import console


def cache_results(function: t.Callable) -> t.Callable:
    """
    Return a decorated function that caches the results.

    Uses both an in-memory cache and a persistent pickle-based cache
    in the system temp directory. Cache entries expire after 1 hour.

    :param function: The async function to wrap with caching.
    :return: An async wrapper that returns cached results when available.
    """

    def save_to_permacache():
        """
        Save the in-memory cache data to the permacache.

        There is a race condition here between two processes updating at the
        same time. It's perfectly acceptable to lose and/or corrupt the
        permacache information as each process's in-memory cache will remain
        in-tact.
        """

        update_from_permacache()
        try:
            with open(filename, "wb") as fp:
                pickle.dump(cache, fp, pickle.HIGHEST_PROTOCOL)
        except IOError:
            pass  # Ignore permacache saving exceptions

    def update_from_permacache():
        """
        Attempt to update newer items from the permacache.
        """

        try:
            with open(filename, "rb") as fp:
                permacache = pickle.load(fp)
        except (FileNotFoundError, FileExistsError):  # TODO: Handle specific exceptions
            return  # It's okay if it cannot load
        for key, value in permacache.items():
            if key not in cache or value[0] > cache[key][0]:
                cache[key] = value

    cache = {}
    cache_expire_time = 3600
    try:
        filename = os.path.join(gettempdir(), "update_checker_cache.pkl")
        update_from_permacache()
    except NotImplementedError:
        filename = None

    @wraps(function)
    async def wrapped(
        obj: UpdateChecker,
        package_name: str,
        package_version: str,
    ) -> t.Union[UpdateResult, None]:
        """
        Return cached results if available.

        :param obj: The instance the decorated method is bound to.
        :param package_name: Name of the package to check.
        :param package_version: Currently running version string.
        :return: The (possibly cached) result of the wrapped function.
        """

        now = time.time()
        key = (package_name, package_version)
        if not obj._bypass_cache and key in cache:  # Check the in-memory cache
            cache_time, retval = cache[key]
            if now - cache_time < cache_expire_time:
                return retval
        retval = await function(obj, package_name, package_version)
        cache[key] = now, retval
        if filename:
            save_to_permacache()
        return retval

    return wrapped


async def query_pypi(package: str, include_prereleases: bool) -> dict:
    """
    Query PyPI for the latest version of a package.

    :param package: The package name to look up on PyPI.
    :param include_prereleases: Whether to consider pre-release versions.
    :return: A dict with ``success`` key, and ``data`` containing
        ``version`` and ``upload_time`` on success.
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://pypi.org/pypi/{package}/json", timeout=1
            )
    except httpx.HTTPError:
        return {"success": False}
    if response.status_code != 200:
        return {"success": False}
    data = response.json()
    versions = list(data["releases"].keys())
    versions.sort(key=parse_version, reverse=True)

    version = versions[0]
    for tmp_version in versions:
        if include_prereleases or standard_release(tmp_version):
            version = tmp_version
            break

    upload_time = None
    for file_info in data["releases"][version]:
        if file_info["upload_time"]:
            upload_time = file_info["upload_time"]
            break

    return {"success": True, "data": {"upload_time": upload_time, "version": version}}


def standard_release(version: str) -> bool:
    """
    Check whether a version string represents a standard (non-pre-release) release.

    :param version: The version string to check.
    :return: ``True`` if the version contains only digits and dots.
    """

    return version.replace(".", "").isdigit()


# This class must be defined before UpdateChecker in order to unpickle objects
# of this type
class UpdateResult:
    """
    Contains the information for a package that has an update.
    """

    def __init__(
        self,
        package: str,
        running: str,
        available: str,
        release_date: t.Union[str, None],
    ):
        """
        Initialise an UpdateResult instance.

        :param package: The package name.
        :param running: The currently running version string.
        :param available: The latest available version string.
        :param release_date: ISO 8601 upload timestamp from PyPI, or ``None``.
        """

        self.available_version = available
        self.package_name = package
        self.running_version = running
        if release_date:
            self.release_date = datetime.strptime(
                release_date, "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=UTC)
        else:
            self.release_date = None

    def __str__(self) -> str:
        """
        Return a printable UpdateResult string.

        :return: A human-readable message about the available update.
        """

        retval = f"Version {self.running_version} of {self.package_name} is outdated. Version {self.available_version} "
        if self.release_date:
            retval += f"was released {pretty_date(self.release_date)}."
        else:
            retval += "is available."
        return retval


class UpdateChecker:
    """
    A class to check for package updates on PyPI.
    """

    def __init__(self, *, bypass_cache: bool = False):
        """
        Initialise an UpdateChecker instance.

        :param bypass_cache: If ``True``, skip the in-memory cache and
            always query PyPI.
        """

        self._bypass_cache = bypass_cache

    @cache_results
    async def check(
        self, package_name: str, package_version: str
    ) -> t.Union[UpdateResult, None]:
        """
        Check whether a newer version of the package is available.

        :param package_name: The package name to check.
        :param package_version: The currently running version string.
        :return: An :class:`UpdateResult` if a newer version exists,
            or ``None`` if already up to date.
        """

        data = await query_pypi(
            package=package_name,
            include_prereleases=not standard_release(package_version),
        )

        if not data.get("success") or (
            parse_version(package_version) >= parse_version(data["data"]["version"])
        ):
            return None

        return UpdateResult(
            package=package_name,
            running=package_version,
            available=data["data"]["version"],
            release_date=data["data"]["upload_time"],
        )


def pretty_date(the_datetime: datetime) -> str:
    """
    Attempt to return a human-readable time delta string.

    :param the_datetime: A timezone-aware :class:`~datetime.datetime` to
        compare against the current UTC time.
    :return: A relative time string such as ``"3 days ago"`` or
        ``"just now"``.
    """

    # Source modified from
    # http://stackoverflow.com/a/5164027/176978
    diff = datetime.now(UTC) - the_datetime
    if diff.days > 7 or diff.days < 0:
        return the_datetime.strftime("%A %B %d, %Y")
    elif diff.days == 1:
        return "1 day ago"
    elif diff.days > 1:
        return f"{diff.days} days ago"
    elif diff.seconds <= 1:
        return "just now"
    elif diff.seconds < 60:
        return f"{diff.seconds} seconds ago"
    elif diff.seconds < 120:
        return "1 minute ago"
    elif diff.seconds < 3600:
        return f"{int(round(diff.seconds / 60))} minutes ago"
    elif diff.seconds < 7200:
        return "1 hour ago"
    else:
        return f"{int(round(diff.seconds / 3600))} hours ago"


async def update_check(
    package_name: str, package_version: str, bypass_cache: bool = False
):
    """
    Convenience function that outputs to stderr if an update is available.

    :param package_name: The package name to check.
    :param package_version: The currently running version string.
    :param bypass_cache: If ``True``, skip the cache and query PyPI directly.
    """

    checker = UpdateChecker(bypass_cache=bypass_cache)
    result = await checker.check(package_name, package_version=package_version)
    if result:
        console.log(f"[bold blue]⬆[/bold blue] {result}")


# The following section of code is taken from setuptools pkg_resources.py (PSF
# license). Unfortunately importing pkg_resources to directly use the
# parse_version function results in some undesired side effects.

component_re = re.compile(r"(\d+ | [a-z]+ | \.| -)", re.VERBOSE)
replace = {"pre": "c", "preview": "c", "-": "final-", "rc": "c", "dev": "@"}.get


def _parse_version_parts(version_string: str) -> t.Generator[str]:
    """
    Yield normalized version parts from a version string.

    :param version_string: A version string to split into comparable parts.
    """

    for part in component_re.split(version_string):
        part = replace(part, part)
        if not part or part == ".":
            continue
        if part[:1] in "0123456789":
            yield part.zfill(8)  # pad for numeric comparison
        else:
            yield "*" + part

    yield "*final"  # ensure that alpha/beta/candidate are before final


def parse_version(string: str) -> tuple[str, ...]:
    """
    Convert a version string to a chronologically-sortable key.

    This is a rough cross between distutils' StrictVersion and LooseVersion;
    if you give it versions that would work with StrictVersion, then it behaves
    the same; otherwise it acts like a slightly-smarter LooseVersion. It is
    *possible* to create pathological version coding schemes that will fool
    this parser, but they should be very rare in practice.

    The returned value will be a tuple of strings.  Numeric portions of the
    version are padded to 8 digits so they will compare numerically, but
    without relying on how numbers compare relative to strings.  Dots are
    dropped, but dashes are retained.  Trailing zeros between alpha segments
    or dashes are suppressed, so that e.g. "2.4.0" is considered the same as
    "2.4". Alphanumeric parts are lower-cased.

    The algorithm assumes that strings like "-" and any alpha string that
    alphabetically follows "final"  represents a "patch level".  So, "2.4-1"
    is assumed to be a branch or patch of "2.4", and therefore "2.4.1" is
    considered newer than "2.4-1", which in turn is newer than "2.4".

    Strings like "a", "b", "c", "alpha", "beta", "candidate" and so on (that
    come before "final" alphabetically) are assumed to be pre-release versions,
    so that the version "2.4" is considered newer than "2.4a1".

    Finally, to handle miscellaneous cases, the strings "pre", "preview", and
    "rc" are treated as if they were "c", i.e. as though they were release
    candidates, and therefore are not as new as a version string that does not
    contain them, and "dev" is replaced with an '@' so that it sorts lower than
    any other pre-release tag.

    :param string: The version string to parse.
    :return: A tuple of strings suitable for comparison.
    """

    parts = []
    for part in _parse_version_parts(string.lower()):
        if part.startswith("*"):
            if part < "*final":  # remove '-' before a prerelease tag
                while parts and parts[-1] == "*final-":
                    parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == "00000000":
                parts.pop()
        parts.append(part)
    return tuple(parts)
