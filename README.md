<p align="center">
<img alt="logo" src="https://www.gstatic.com/buganizer/img/v0/logo.svg" width="150" height="150">
<br>
<br>
<strong>Python client for the Google Issue Tracking system (Buganizer)</strong>
</p>

## Quick Start

```python
from buganize import Buganize


async def main():
    async with Buganize() as client:
        result = await client.search(query="status:open priority:p1", page_size=25)
        for issue in result.issues:
            print(f"#{issue.id} [{issue.status.name}] {issue.title}")
```

```bash
buganize search "status:open priority:p1"
```

## Documentation

Refer to [the docs](https://buganize.readthedocs.io) for installation, usage and api reference.
