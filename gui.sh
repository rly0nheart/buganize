#!/bin/sh
# Run the buganize GTK4 GUI inside the project's nix-shell.
# Forwards any extra arguments (e.g. --install-desktop) to the entry point.
set -e
cd "$(dirname "$0")"
exec nix-shell --run "./.gui-venv/bin/python -m buganize.gui $*"
