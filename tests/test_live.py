from __future__ import annotations

import os

import pytest

from scrapedrive import AsyncScrapeDrive, ScrapeDrive

pytestmark = pytest.mark.skipif(
    os.getenv("SCRAPEDRIVE_RUN_LIVE_TESTS") != "1",
    reason="Set SCRAPEDRIVE_RUN_LIVE_TESTS=1 to run live API checks.",
)


def test_live_sync_page_text() -> None:
    with ScrapeDrive() as client:
        response = client.scrape(
            "https://bytexd.com",
            render_js=True,
            scrape_tier="advanced",
            country_code="US",
            block_resources=True,
        )

    assert response.status_code == 200
    assert "<html" in response.text.lower()


def test_live_sync_markdown_result() -> None:
    with ScrapeDrive() as client:
        response = client.scrape(
            "https://bytexd.com",
            render_js=False,
            result_type="page_markdown",
        )

    assert response.status_code == 200
    assert len(response.text) > 0


def test_live_sync_screenshot_response() -> None:
    with ScrapeDrive() as client:
        response = client.scrape(
            "https://bytexd.com",
            render_js=True,
            scrape_tier="advanced",
            country_code="US",
            screenshot=True,
        )

    assert response.status_code == 200
    assert response.screenshot_url is not None


@pytest.mark.asyncio
async def test_live_async_completed_job_has_body() -> None:
    async with AsyncScrapeDrive() as client:
        job = await client.submit_scrape(
            "https://bytexd.com",
            render_js=True,
            scrape_tier="advanced",
            country_code="US",
            block_resources=True,
        )
        completed = await client.wait_for_job(job.id, poll_interval=1.0, timeout=90.0)

    assert completed.is_completed
    assert completed.result is not None
    assert "<html" in str(completed.result).lower()
