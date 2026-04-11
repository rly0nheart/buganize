<p align="center">
<img alt="logo" src="https://www.gstatic.com/buganizer/img/v0/logo.svg" width="150" height="150">
<br>
<br>
<strong>Python client for the Google Issue Tracking system (Buganizer)</strong>
</p>


## Quick start

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
See:
- [Installation](https://github.com/rly0nheart/buganize/blob/master/INSTALLATION.md) for installation guide.
- [Usage](https://github.com/rly0nheart/buganize/blob/master/USAGE.md) for full library and CLI documentation.
- [Buganizer API Reference](https://github.com/rly0nheart/buganize/blob/master/src/buganize/api/README.md) for details about
  limitations, and how the Buganizer API works.
