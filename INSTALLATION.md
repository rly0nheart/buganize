## Installation

### Table of Contents

1. [From PyPI](#from-pypi)
    - [Library](#library)
    - [With the CLI](#with-the-cli)
2. [Docker Image](#docker-image)
3. [Nix](#nix)

## From PyPI

`buganize` is available on PyPI as `buganize` or `buganise`. By default, the `pip install` command will only install the library without the cli util support. Below are instructions on how to install both the library and CLI utility:

### Library
```shell
pip install buganize
```

### With the CLI

```shell
pip install buganize[cli]
```

## Docker Image

If you prefer running the CLI utility inside a docker container, a `Dockerfile` is provided.

```shell
docker build -t buganize-cli .
```

> This assumes your current working directory is `buganize/`

## Nix

For Nix users, a `shell.nix` is provided. Once you enter the shell, you will be able to do stuff.

```shell
nix-shell
```
