# scrapedrive-python

Typed Python SDK for the [ScrapeDrive API](https://scrapedrive.com/docs/), built around `httpx`
and managed with `uv`.

## Install

```bash
uv sync
```

For packaging consumers:

```bash
uv add scrapedrive
```

## Quick Start

Set your API key in the environment:

```bash
export SCRAPEDRIVE_API_KEY=your_key
```

### Sync client

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    response = client.scrape(
        "https://example.com",
        result_type="page_text",
        render_js=False,
    )
    print(response.text)
```

### Async job flow

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    job = client.submit_scrape(
        "https://example.com",
        render_js=True,
        wait_browser="networkidle",
        scrape_tier="advanced",
        country_code="US",
    )
    completed = client.wait_for_job(job.id, poll_interval=2.0, timeout=60.0)
    print(completed.result)
```

### Native async client

```python
import asyncio

from scrapedrive import AsyncScrapeDrive


async def main() -> None:
    async with AsyncScrapeDrive() as client:
        response = await client.scrape("https://example.com", result_type="page_markdown")
        print(response.text)


asyncio.run(main())
```

### Forward headers to the target site

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    response = client.scrape(
        "https://example.com/private",
        target_headers={"Authorization": "Bearer token"},
    )
    print(response.text)
```

The SDK automatically rewrites forwarded target headers to the `sdrive-` format required by
ScrapeDrive and enables `forward_sdrive_headers=true`.

## Geography Defaults

For `advanced` and `hyperdrive` requests, the SDK defaults `country_code` to `US` when you do not
pass one explicitly. This avoids ScrapeDrive's random geo selection. If you want a site-local
country instead, pass it per request:

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    response = client.scrape(
        "https://example.de",
        scrape_tier="advanced",
        country_code="DE",
    )
```

## AI Agents

Provider-agnostic agent guidance lives in `AGENTS.md`.

This repo also includes a repo-local Codex skill at `.codex/skills/scrapedrive-sdk`, but that is
just a Codex-specific adapter. Keep `AGENTS.md` as the canonical source of truth for agent behavior.

## Development

```bash
uv run ruff check
uv run ruff format
uv run pytest
```

Live integration tests are opt-in:

```bash
SCRAPEDRIVE_RUN_LIVE_TESTS=1 uv run pytest tests/test_live.py
```

## Build

```bash
uv build
```

See `RELEASING.md` for the wheel smoke-install workflow and release checklist.
