---
name: scrapedrive-sdk
description: Use the ScrapeDrive Python SDK for web fetching, JS rendering, screenshots, text extraction, markdown extraction, and long-running async scrape jobs. Trigger when Codex needs to write or review code against this SDK, choose between sync and async ScrapeDrive flows, pick a scrape tier, set deterministic geography, forward target headers, or handle ScrapeDrive response quirks such as screenshot URLs and async job bodies.
---

# ScrapeDrive SDK

Use this skill when writing code that calls `scrapedrive` or when maintaining this repository.
Treat `AGENTS.md` in the repo root as the canonical provider-agnostic guide. This skill is the Codex-specific adapter for the same guidance.

## Choose The Flow

- Use `ScrapeDrive.scrape()` for one-shot requests where the response should be returned immediately.
- Use `ScrapeDrive.submit_scrape()` plus `wait_for_job()` when the target may take a while or when polling is easier to control than blocking on one request.
- Use `AsyncScrapeDrive` only when the caller is already async. Do not add async complexity to otherwise synchronous code just to use the async client.

## Choose The Tier

- Use `standard` by default for uncomplicated targets.
- Use `advanced` when the site is geo-sensitive or `standard` is not reliable enough.
- Use `hyperdrive` only for the hardest targets or when `advanced` still fails.
- Treat `country_code` as meaningful only on `advanced` and `hyperdrive`.

## Geography Rules

- Do not rely on random geography for `advanced` or `hyperdrive`.
- Prefer the country the site is actually from. If that is unclear, use `US`.
- The SDK defaults `country_code` to `US` for `advanced` and `hyperdrive` when the caller omits it. Keep that behavior unless there is a concrete reason to change it.
- `standard` requests do not accept `country_code`.

## Request Patterns

- Use `result_type="html"` when downstream code needs full markup.
- Use `result_type="page_text"` for extraction or summarization pipelines.
- Use `result_type="page_markdown"` for LLM-friendly page capture.
- Pass `target_headers={...}` when the destination site needs request headers such as `Authorization`. The SDK rewrites them to `sdrive-*` headers and enables `forward_sdrive_headers=true`.
- Use `session_number` when sticky behavior matters across multiple requests.

## Response Quirks

- For sync screenshot requests, read `response.screenshot_url`. Do not assume the response body itself is JSON.
- For async completed jobs, use `job.result` for the normalized body. The live API returns completed content under `response.body`, and the SDK already normalizes that shape.
- For async screenshot jobs, use `job.screenshot_url`.
- If code needs the raw payload, use `job.raw`.

## Code Shapes

Use patterns like these:

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    response = client.scrape(
        "https://example.com",
        result_type="page_markdown",
        scrape_tier="advanced",
        country_code="US",
        render_js=True,
    )
    print(response.text)
```

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    job = client.submit_scrape(
        "https://example.com",
        scrape_tier="advanced",
        country_code="DE",
        render_js=True,
    )
    completed = client.wait_for_job(job.id, poll_interval=2.0, timeout=60.0)
    print(completed.result)
```

```python
from scrapedrive import ScrapeDrive

with ScrapeDrive() as client:
    response = client.scrape(
        "https://example.com/private",
        target_headers={"Authorization": "Bearer token"},
    )
    print(response.text)
```

## Validation

- Run `uv run pytest` for mocked coverage.
- Run `SCRAPEDRIVE_RUN_LIVE_TESTS=1 uv run pytest tests/test_live.py` for live coverage.
- Keep live tests small and deterministic: one sync scrape, one async scrape, and one screenshot path are enough for smoke coverage.

## Repo Pointers

- Use `README.md` for install and public examples.
- Use `tests/test_live.py` when you need the current live API expectations.
- Use `src/scrapedrive/client.py` and `src/scrapedrive/models.py` when changing request defaults or response normalization.
