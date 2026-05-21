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
}
