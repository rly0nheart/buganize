"""Static data shared across the GUI modules — no GTK imports here."""

from __future__ import annotations

import os
from importlib.metadata import version

APP_PKG = "buganize"
APP_VERSION = version(APP_PKG)
APP_ICON_NAME = "dev.rly0nheart.buganize"

_HERE = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(_HERE, "icons")
EMPTY_STATE_IMAGE = os.path.join(ICONS_DIR, "space_empty_state.png")
TRACKER_ICONS_DIR = os.path.join(ICONS_DIR, "trackers")


# Filter dropdown choices: (display label, query token). A token of None means
# "no constraint" and is omitted from the search query.

STATUS_CHOICES: list[tuple[str, str | None]] = [
    ("any", None),
    ("Open", "open"),
    ("Closed", "closed"),
    ("New", "new"),
    ("Assigned", "assigned"),
    ("Accepted", "accepted"),
    ("Fixed", "fixed"),
    ("Verified", "verified"),
    ("Duplicate", "duplicate"),
    ("Obsolete", "obsolete"),
    ("Not reproducible", "notreproducible"),
    ("Intended behavior", "intendedbehavior"),
    ("Infeasible", "infeasible"),
]

PRIORITY_CHOICES: list[tuple[str, str | None]] = [
    ("any", None),
    ("P0", "p0"),
    ("P1", "p1"),
    ("P2", "p2"),
    ("P3", "p3"),
    ("P4", "p4"),
]

SEVERITY_CHOICES: list[tuple[str, str | None]] = [
    ("any", None),
    ("S0", "s0"),
    ("S1", "s1"),
    ("S2", "s2"),
    ("S3", "s3"),
    ("S4", "s4"),
]

TYPE_CHOICES: list[tuple[str, str | None]] = [
    ("any", None),
    ("Bug", "bug"),
    ("Feature request", "feature_request"),
    ("Customer issue", "customer_issue"),
    ("Internal cleanup", "internal_cleanup"),
    ("Process", "process"),
    ("Vulnerability", "vulnerability"),
]

# Filter keys that the dropdowns own in the search-entry text. Tokens with
# these keys get rewritten whenever the user changes a dropdown.
MANAGED_FILTER_KEYS: frozenset[str] = frozenset(
    {"status", "priority", "severity", "type"}
)


PAGE_SIZE_CHOICES: list[int] = [25, 50, 100, 250]
DEFAULT_PAGE_SIZE: int = 50


EMPTY_STATE_CSS = (
    ".empty-state-text {"
    " font-family: Roboto, Arial, sans-serif;"
    " font-weight: normal;"
    " color: white;"
    "}"
)


# Env vars carried into the launcher script written by --install-desktop.
LAUNCHER_ENV_VARS: tuple[str, ...] = (
    "LD_LIBRARY_PATH",
    "LIBRARY_PATH",
    "GI_TYPELIB_PATH",
    "GIO_MODULE_DIR",
    "GIO_EXTRA_MODULES",
    "GSETTINGS_SCHEMA_DIR",
    "XDG_DATA_DIRS",
    "XDG_CONFIG_DIRS",
    "PATH",
    "PYTHONPATH",
    "FONTCONFIG_FILE",
    "FONTCONFIG_PATH",
    "LOCALE_ARCHIVE",
    "LOCPATH",
    "TZDIR",
)
