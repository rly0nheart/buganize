{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python313
    python313Packages.pygobject3
    python313Packages.pygobject-stubs
    gobject-introspection
    gtk4
    libadwaita
    webkitgtk_6_0
    glib
    cairo
    pkg-config
    uv
  ];

  GI_TYPELIB_PATH = "${pkgs.gtk4}/lib/girepository-1.0:${pkgs.libadwaita}/lib/girepository-1.0";

  # Bootstrap the GUI virtualenv that gui.sh / cli.sh expect. It is built with
  # --system-site-packages so the GTK4 / PyGObject bindings supplied by Nix
  # remain importable, while project deps are installed on top with uv.
  shellHook = ''
    if [ ! -x ./.gui-venv/bin/python ]; then
      echo "Creating .gui-venv ..."
      uv venv --system-site-packages --python "${pkgs.python313}/bin/python3" ./.gui-venv
      VIRTUAL_ENV=./.gui-venv uv pip install -e '.[cli]'
    fi
  '';
}
