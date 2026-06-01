import os
import shlex
import sys
from pathlib import Path

from buganize.gui import APP_ICON_NAME, LAUNCHER_ENV_VARS, main


def _install_desktop() -> int:
    here = Path(__file__).resolve().parent
    icon_src = here / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ICON_NAME}.svg"
    template = here / f"{APP_ICON_NAME}.desktop"
    # here = src/buganize/gui  →  parents[2] = project root
    project_root = here.parents[2]

    home = Path.home()
    apps_dir = home / ".local" / "share" / "applications"
    icons_dir = home / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    # Generate a launcher that bakes in the current GTK/Nix env so the app can
    # start from a bare compositor environment (no nix-shell on the path).
    launcher = here / "buganize-launch.sh"
    exports = "\n".join(
        f"export {var}={shlex.quote(os.environ[var])}"
        for var in LAUNCHER_ENV_VARS
        if var in os.environ
    )
    launcher.write_text(
        "#!/bin/sh\n"
        f"cd {shlex.quote(str(project_root))}\n"
        f"{exports}\n"
        f'exec {shlex.quote(sys.executable)} -m buganize.gui "$@"\n'
    )
    launcher.chmod(0o755)

    desktop_dst = apps_dir / f"{APP_ICON_NAME}.desktop"
    icon_dst = icons_dir / f"{APP_ICON_NAME}.svg"

    rendered = (
        template.read_text()
        .replace("{EXEC}", str(launcher))
        .replace("{PATH}", str(project_root))
    )
    desktop_dst.write_text(rendered)

    if icon_dst.is_symlink() or icon_dst.exists():
        icon_dst.unlink()
    icon_dst.symlink_to(icon_src)

    print(
        "Installed:\n"
        f"  {desktop_dst}\n"
        f"  {icon_dst} -> {icon_src}\n"
        f"  {launcher} (launcher with baked-in env)"
    )
    return 0


if "--install-desktop" in sys.argv:
    sys.exit(_install_desktop())

sys.exit(main())
