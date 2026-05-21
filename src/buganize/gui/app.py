"""Adw.Application entry point for the Buganize GTK4 GUI."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gio  # noqa: E402

from .window import MainWindow


class BuganizeApp(Adw.Application):
    """
    Top-level libadwaita application for the Buganize GUI. Creates a single
    :class:`MainWindow` on activation.
    """

    def __init__(self) -> None:
        super().__init__(
            application_id="dev.rly0nheart.buganize",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = MainWindow(application=self)
        window.present()


def main() -> int:
    """
    Entry point: run the GUI application loop.

    :return: Application exit code suitable for ``sys.exit``.
    """

    return BuganizeApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
