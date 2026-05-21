#!/bin/sh
# Run the buganize CLI inside the project's nix-shell.
# Forwards any extra arguments to the CLI.
set -e
cd "$(dirname "$0")"
exec nix-shell --run "./.gui-venv/bin/buganize $*"
