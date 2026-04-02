from __future__ import annotations

import json
from collections import deque

import httpx
import pytest

from scrapedrive import (
    ApiError,
    AsyncScrapeDrive,
    AuthenticationError,
    PaymentRequiredError,
    RateLimitError,
    ScrapeDrive,
    ScrapeJob,
    TimeoutError,
    ValidationError,
)


def test_sync_scrape_returns_text_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.params["api_key"] == "test-key"
        assert request.url.params["url"] == "https://example.com"
        assert request.url.params["render_js"] == "false"
        assert request.url.params["result_type"] == "page_text"
        return httpx.Response(200, text="Example Domain")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com", result_type="page_text", render_js=False)

    assert response.status_code == 200
    assert response.text == "Example Domain"
    assert response.data is None


def test_default_country_code_is_applied_for_advanced_tiers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["scrape_tier"] == "advanced"
        assert request.url.params["country_code"] == "US"
        return httpx.Response(200, text="Example Domain")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com", scrape_tier="advanced")

    assert response.status_code == 200


def test_explicit_country_code_overrides_client_default() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["scrape_tier"] == "hyperdrive"
        assert request.url.params["country_code"] == "DE"
        return httpx.Response(200, text="Example Domain")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape(
        "https://example.com",
        scrape_tier="hyperdrive",
        country_code="DE",
    )

    assert response.status_code == 200


def test_standard_tier_does_not_send_default_country_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "country_code" not in request.url.params
        return httpx.Response(200, text="Example Domain")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com", scrape_tier="standard")

    assert response.status_code == 200


def test_custom_proxy_and_session_number_are_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["custom_proxy"] == "http://user:pass@proxy.example.com:8080"
        assert request.url.params["session_number"] == "42"
        return httpx.Response(200, text="Example Domain")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape(
        "https://example.com",
        scrape_tier="advanced",
        custom_proxy="http://user:pass@proxy.example.com:8080",
        session_number=42,
    )

    assert response.status_code == 200


def test_sync_screenshot_response_exposes_screenshot_url() -> None:
    payload = {"screenshot_url": "https://cdn.scrapedrive.com/screenshots/1.png"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            text=json.dumps(payload),
        )

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com", screenshot=True)

    assert response.is_json
    assert response.screenshot_url == payload["screenshot_url"]
    assert response.json() == payload


def test_sync_screenshot_url_can_come_from_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html; charset=utf-8",
                "x-sdrive-screenshot-url": "https://cdn.scrapedrive.com/screenshots/2.png",
            },
            text="<html>ok</html>",
        )

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com", screenshot=True)

    assert response.screenshot_url == "https://cdn.scrapedrive.com/screenshots/2.png"


def test_submit_and_wait_for_job_until_completed() -> None:
    job_responses = deque(
        [
            {
                "id": "job-123",
                "status": "queued",
                "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
            },
            {
                "id": "job-123",
                "status": "completed",
                "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
                "result": "done",
            },
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                202,
                headers={"content-type": "application/json"},
                json=job_responses[0],
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=job_responses.popleft(),
        )

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    job = client.submit_scrape("https://example.com", render_js=True)
    completed = client.wait_for_job(job.id, poll_interval=0.0, timeout=1.0)

    assert isinstance(job, ScrapeJob)
    assert job.id == "job-123"
    assert completed.is_completed
    assert completed.result == "done"


@pytest.mark.asyncio
async def test_async_client_waits_for_completed_job() -> None:
    job_responses = deque(
        [
            {
                "id": "job-123",
                "status": "queued",
                "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
            },
            {
                "id": "job-123",
                "status": "completed",
                "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
                "result": {"page_text": "done"},
            },
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                202,
                headers={"content-type": "application/json"},
                json=job_responses[0],
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=job_responses.popleft(),
        )

    transport = httpx.MockTransport(handler)
    client = AsyncScrapeDrive(api_key="test-key", client=httpx.AsyncClient(transport=transport))

    job = await client.submit_scrape("https://example.com")
    completed = await client.wait_for_job(job.id, poll_interval=0.0, timeout=1.0)

    assert completed.is_completed
    assert completed.result == {"page_text": "done"}


@pytest.mark.asyncio
async def test_async_client_applies_default_country_code() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            seen["country_code"] = request.content.decode("utf-8")
            return httpx.Response(
                202,
                headers={"content-type": "application/json"},
                json={
                    "id": "job-123",
                    "status": "completed",
                    "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
                    "response": {"body": "<html>ok</html>"},
                },
            )
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "id": "job-123",
                "status": "completed",
                "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
                "response": {"body": "<html>ok</html>"},
            },
        )

    transport = httpx.MockTransport(handler)
    client = AsyncScrapeDrive(api_key="test-key", client=httpx.AsyncClient(transport=transport))

    job = await client.submit_scrape("https://example.com", scrape_tier="advanced")

    assert job.is_completed
    assert '"country_code":"US"' in seen["country_code"]


def test_async_job_maps_response_body_when_result_is_absent() -> None:
    job = ScrapeJob.from_payload(
        {
            "id": "job-123",
            "status": "completed",
            "url": "https://example.com",
            "status_url": "https://api.scrapedrive.com/api/v1/job/job-123",
            "response": {
                "status_code": 200,
                "final_url": "https://example.com/",
                "headers": {},
                "body": "<html>ok</html>",
                "credits": 10,
            },
        }
    )

    assert job.is_completed
    assert job.result == "<html>ok</html>"


def test_async_job_exposes_screenshot_url_from_response_headers() -> None:
    job = ScrapeJob.from_payload(
        {
            "id": "job-123",
            "status": "completed",
            "response": {
                "headers": {
                    "x-sdrive-screenshot-url": "https://cdn.scrapedrive.com/screenshots/3.png"
                },
                "body": "<html>ok</html>",
            },
        }
    )

    assert job.screenshot_url == "https://cdn.scrapedrive.com/screenshots/3.png"


def test_page_markdown_is_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["result_type"] == "page_markdown"
        return httpx.Response(200, text="# Example")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com", result_type="page_markdown", render_js=False)

    assert response.text == "# Example"


@pytest.mark.parametrize(
    ("status_code", "error_body", "expected_error"),
    [
        (401, {"error": "Invalid token"}, AuthenticationError),
        (
            402,
            {"error": {"code": "PAYMENT_REQUIRED", "message": "Need credits"}},
            PaymentRequiredError,
        ),
        (
            422,
            {"error": {"code": "VALIDATION_ERROR", "message": "url is required"}},
            ValidationError,
        ),
        (429, {"error": "Slow down"}, RateLimitError),
        (504, {"error": "Timed out"}, TimeoutError),
        (500, {"error": "Internal error"}, ApiError),
    ],
)
def test_status_codes_raise_typed_exceptions(
    status_code: int,
    error_body: dict[str, object],
    expected_error: type[ApiError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            headers={"content-type": "application/json"},
            json=error_body,
        )

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    with pytest.raises(expected_error):
        client.scrape("https://example.com")


def test_forwarded_headers_are_prefixed_and_flag_enabled() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["sdrive-authorization"] == "Bearer secret"
        assert request.headers["sdrive-x-trace"] == "abc123"
        assert request.url.params["forward_sdrive_headers"] == "true"
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(api_key="test-key", client=httpx.Client(transport=transport))

    response = client.scrape(
        "https://example.com/private",
        target_headers={"Authorization": "Bearer secret", "X-Trace": "abc123"},
    )

    assert response.text == "ok"


def test_api_key_can_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRAPEDRIVE_API_KEY", "env-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "env-key"
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    client = ScrapeDrive(client=httpx.Client(transport=transport))

    response = client.scrape("https://example.com")

    assert response.text == "ok"


def test_sync_timeout_validation_rejects_async_maximum() -> None:
    client = ScrapeDrive(
        api_key="test-key",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="ok"))
        ),
    )

    with pytest.raises(ValueError, match="95000"):
        client.scrape("https://example.com", timeout_ms=130000)
