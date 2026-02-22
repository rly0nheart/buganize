from importlib.metadata import version

from rich.console import Console

__pkg__ = "buganize"
__version__ = version(__pkg__)

console = Console(log_time=False)
