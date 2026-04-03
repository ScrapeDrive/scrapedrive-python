# ScrapeDrive Agent Guide

Use this file as the provider-agnostic source of truth for AI agents working with this repository.

## Scope

This repository contains the `scrapedrive` Python SDK. Use it for:

- one-shot sync scraping
- long-running async scrape jobs
- HTML, text, and markdown extraction
- screenshot workflows
- forwarded target headers

## Choose The Flow

- Use `ScrapeDrive.scrape()` for one-shot requests that should return immediately.
- Use `ScrapeDrive.submit_scrape()` plus `wait_for_job()` when the target may take longer or the caller wants explicit polling.
- Use `AsyncScrapeDrive` only when the caller is already async. Do not introduce async complexity unless the surrounding code already needs it.

## Choose The Tier

- Use `standard` by default for uncomplicated targets.
- Use `advanced` when the site is geo-sensitive or `standard` is not reliable enough.
- Use `hyperdrive` only for the hardest targets or when `advanced` still fails.
- Treat `country_code` as meaningful only on `advanced` and `hyperdrive`.

## Geography Rules

- Do not rely on random geography for `advanced` or `hyperdrive`.
- Prefer the country the site is actually from. If that is unclear, use `US`.
- The SDK defaults `country_code` to `US` for `advanced` and `hyperdrive` when the caller omits it. Preserve that behavior unless there is a concrete reason to change it.
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

## Validation

- Run `uv run pytest` for mocked coverage.
- Run `SCRAPEDRIVE_RUN_LIVE_TESTS=1 uv run pytest tests/test_live.py` for live coverage.
- Keep live tests small and deterministic: one sync scrape, one async scrape, and one screenshot path are enough for smoke coverage.

## Repo Pointers

- Use `README.md` for install and public examples.
- Use `tests/test_live.py` when you need the current live API expectations.
- Use `src/scrapedrive/client.py` and `src/scrapedrive/models.py` when changing request defaults or response normalization.

Do not keep provider-specific agent config in this repository unless there is a strong reason.
If you add adapters for specific ecosystems later, treat this file as canonical and generate those
adapters from it rather than making them the source of truth.
