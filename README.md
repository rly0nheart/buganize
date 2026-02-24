<p align="center">
<img alt="logo" src="https://www.gstatic.com/buganizer/img/v0/logo.svg" width="150" height="150">
<br>
<br>
<strong>Unofficial Python client for the Google Issue Tracker.</strong>
</p>

## Installation

```shell
pip install buganize
```

## Quick start

```python
from buganize import Buganize


async def main():
    async with Buganize() as client:
        result = await client.search("status:open priority:p1", page_size=25)
        for issue in result.issues:
            print(f"#{issue.id} [{issue.status.name}] {issue.title}")
```

```bash
buganize search "status:open"
```

## Documentation

- See [USAGE.md](https://github.com/rly0nheart/buganize/blob/master/USAGE.md) for full library and CLI documentation.
- See [API Reference](https://github.com/rly0nheart/buganize/tree/master/src/buganize/api#readme) for details about
  limitations, and how the API works.
