# buganize GTK4 GUI

A small GTK4 desktop frontend over the `buganize` Python client.

<table>
  <tr>
    <td><img width="1920" height="1200" alt="20260601-175818" src="https://github.com/user-attachments/assets/01d52886-1347-4ffc-9b74-a8f65ce27b48" /></td>
    <td><img width="1920" height="1200" alt="20260601-175846" src="https://github.com/user-attachments/assets/5c6f3919-3890-4dfe-a7a4-874ffde43160" /></td>
  </tr>
</table>

## Requirements

- Python ≥ 3.11
- GTK 4 (4.12+ recommended for row/column separators)
- PyGObject (`pygobject` / `python-gi` on most distros)
- The `buganize` package installed (or run from a `uv` env in the project root)

On Debian/Ubuntu:

```sh
sudo apt install python3-gi gir1.2-gtk-4.0
```

On Arch:

```sh
sudo pacman -S python-gobject gtk4
```

## Running

From the project root:

```sh
uv run python -m gui
```

Or with a plain venv that has `buganize` and `PyGObject` installed:

```sh
python -m gui
```
