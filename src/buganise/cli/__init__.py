from importlib.metadata import version

from rich.console import Console

__pkg__ = "buganise"
__version__ = version(__pkg__)

console = Console()
