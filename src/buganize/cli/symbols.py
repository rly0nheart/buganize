"""
Shared Rich-markup status symbols for CLI output.

Centralises the decorative prefixes used across the CLI so they stay
visually consistent and are defined in exactly one place.
"""

__all__ = ["OK", "FAIL", "WARN", "INFO"]

#: Success marker (green ✔).
OK = "[bold green]✔[/bold green]"

#: Failure/error marker (red ✘).
FAIL = "[bold red]✘[/bold red]"

#: Warning/interrupted marker (yellow ✘).
WARN = "[bold yellow]✘[/bold yellow]"

#: Informational marker (blue *).
INFO = "[bold blue]*[/bold blue]"
