from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Mapping, MutableMapping
from dataclasses import replace
from typing import Any, TypeVar, overload

import httpx

from .exceptions import MissingApiKeyError, TimeoutError, raise_for_scrapedrive_error
from .models import ScrapeJob, ScrapeOptions, ScrapeResponse

DEFAULT_SYNC_BASE_URL = "https://sync.scrapedrive.com"
DEFAULT_API_BASE_URL = "https://api.scrapedrive.com"
DEFAULT_HTTP_TIMEOUT = httpx.Timeout(150.0, connect=10.0)

_SyncClientT = TypeVar("_SyncClientT", bound="ScrapeDrive")
_AsyncClientT = TypeVar("_AsyncClientT", bound="AsyncScrapeDrive")


class ScrapeDrive:
    """Blocking ScrapeDrive SDK client."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = None,
        client: httpx.Client | None = None,
        sync_base_url: str = DEFAULT_SYNC_BASE_URL,
        api_base_url: str = DEFAULT_API_BASE_URL,
        default_country_code: str | None = "US",
    ) -> None:
        self.api_key = api_key or os.getenv("SCRAPEDRIVE_API_KEY")
        if not self.api_key:
            raise MissingApiKeyError(
                "ScrapeDrive API key is required. Pass api_key=... or set SCRAPEDRIVE_API_KEY."
            )

        self.sync_base_url = sync_base_url.rstrip("/")
        self.api_base_url = api_base_url.rstrip("/")
        self.default_country_code = _normalize_country_code(default_country_code)
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout or DEFAULT_HTTP_TIMEOUT,
            headers=dict(headers or {}),
        )

    def __enter__(self: _SyncClientT) -> _SyncClientT:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @overload
    def scrape(
        self,
        request: ScrapeOptions,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeResponse: ...

    @overload
    def scrape(
        self,
        url: str,
        /,
        *,
        scrape_tier: str = "standard",
        country_code: str | None = None,
        custom_proxy: str | None = None,
        session_number: int | None = None,
        render_js: bool = True,
        device_type: str = "desktop",
        wait_browser: str | None = None,
        wait_for: str | None = None,
        wait_ms: int | None = None,
        block_resources: bool = True,
        block_ads: bool = False,
        forward_sdrive_headers: bool = False,
        timeout_ms: int | None = None,
        result_type: str = "html",
        screenshot: bool = False,
        screenshot_fullpage: bool = False,
        screenshot_selector: str | None = None,
        extra_params: Mapping[str, Any] | None = None,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeResponse: ...

    def scrape(
        self,
        request: ScrapeOptions | str,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> ScrapeResponse:
        options = _apply_client_defaults(
            _coerce_options(request, kwargs),
            default_country_code=self.default_country_code,
        )
        headers = _target_headers(target_headers)
        payload = options.as_payload(
            api_key=self.api_key,
            mode="sync",
            force_forward_headers=bool(headers),
        )
        response = self._client.get(
            f"{self.sync_base_url}/api/v1/scrape",
            params=payload,
            headers=headers,
        )
        raise_for_scrapedrive_error(response)
        return _scrape_response_from_httpx(response)

    @overload
    def submit_scrape(
        self,
        request: ScrapeOptions,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeJob: ...

    @overload
    def submit_scrape(
        self,
        url: str,
        /,
        *,
        scrape_tier: str = "standard",
        country_code: str | None = None,
        custom_proxy: str | None = None,
        session_number: int | None = None,
        render_js: bool = True,
        device_type: str = "desktop",
        wait_browser: str | None = None,
        wait_for: str | None = None,
        wait_ms: int | None = None,
        block_resources: bool = True,
        block_ads: bool = False,
        forward_sdrive_headers: bool = False,
        timeout_ms: int | None = None,
        result_type: str = "html",
        screenshot: bool = False,
        screenshot_fullpage: bool = False,
        screenshot_selector: str | None = None,
        extra_params: Mapping[str, Any] | None = None,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeJob: ...

    def submit_scrape(
        self,
        request: ScrapeOptions | str,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> ScrapeJob:
        options = _apply_client_defaults(
            _coerce_options(request, kwargs),
            default_country_code=self.default_country_code,
        )
        headers = _target_headers(target_headers)
        payload = options.as_payload(
            api_key=self.api_key,
            mode="async",
            force_forward_headers=bool(headers),
        )
        response = self._client.post(
            f"{self.api_base_url}/api/v1/scrape/async",
            json=payload,
            headers=headers,
        )
        raise_for_scrapedrive_error(response)
        return ScrapeJob.from_payload(response.json())

    def get_job(self, job_id: str | None = None, *, status_url: str | None = None) -> ScrapeJob:
        url = _job_url(api_base_url=self.api_base_url, job_id=job_id, status_url=status_url)
        response = self._client.get(url)
        raise_for_scrapedrive_error(response)
        return ScrapeJob.from_payload(response.json())

    def wait_for_job(
        self,
        job_id: str | None = None,
        *,
        status_url: str | None = None,
        poll_interval: float = 2.0,
        timeout: float | None = None,
    ) -> ScrapeJob:
        if poll_interval < 0:
            raise ValueError("poll_interval must be greater than or equal to 0")

        deadline = None if timeout is None else time.monotonic() + timeout
        job = self.get_job(job_id, status_url=status_url)
        while job.is_pending:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for ScrapeDrive job {job.id} to finish.")
            if poll_interval:
                time.sleep(poll_interval)
            next_status_url = job.status_url or status_url
            if next_status_url:
                job = self.get_job(status_url=next_status_url)
            else:
                job = self.get_job(job.id)
        return job


class AsyncScrapeDrive:
    """Async ScrapeDrive SDK client."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = None,
        client: httpx.AsyncClient | None = None,
        sync_base_url: str = DEFAULT_SYNC_BASE_URL,
        api_base_url: str = DEFAULT_API_BASE_URL,
        default_country_code: str | None = "US",
    ) -> None:
        self.api_key = api_key or os.getenv("SCRAPEDRIVE_API_KEY")
        if not self.api_key:
            raise MissingApiKeyError(
                "ScrapeDrive API key is required. Pass api_key=... or set SCRAPEDRIVE_API_KEY."
            )

        self.sync_base_url = sync_base_url.rstrip("/")
        self.api_base_url = api_base_url.rstrip("/")
        self.default_country_code = _normalize_country_code(default_country_code)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout or DEFAULT_HTTP_TIMEOUT,
            headers=dict(headers or {}),
        )

    async def __aenter__(self: _AsyncClientT) -> _AsyncClientT:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @overload
    async def scrape(
        self,
        request: ScrapeOptions,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeResponse: ...

    @overload
    async def scrape(
        self,
        url: str,
        /,
        *,
        scrape_tier: str = "standard",
        country_code: str | None = None,
        custom_proxy: str | None = None,
        session_number: int | None = None,
        render_js: bool = True,
        device_type: str = "desktop",
        wait_browser: str | None = None,
        wait_for: str | None = None,
        wait_ms: int | None = None,
        block_resources: bool = True,
        block_ads: bool = False,
        forward_sdrive_headers: bool = False,
        timeout_ms: int | None = None,
        result_type: str = "html",
        screenshot: bool = False,
        screenshot_fullpage: bool = False,
        screenshot_selector: str | None = None,
        extra_params: Mapping[str, Any] | None = None,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeResponse: ...

    async def scrape(
        self,
        request: ScrapeOptions | str,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> ScrapeResponse:
        options = _apply_client_defaults(
            _coerce_options(request, kwargs),
            default_country_code=self.default_country_code,
        )
        headers = _target_headers(target_headers)
        payload = options.as_payload(
            api_key=self.api_key,
            mode="sync",
            force_forward_headers=bool(headers),
        )
        response = await self._client.get(
            f"{self.sync_base_url}/api/v1/scrape",
            params=payload,
            headers=headers,
        )
        raise_for_scrapedrive_error(response)
        return _scrape_response_from_httpx(response)

    @overload
    async def submit_scrape(
        self,
        request: ScrapeOptions,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeJob: ...

    @overload
    async def submit_scrape(
        self,
        url: str,
        /,
        *,
        scrape_tier: str = "standard",
        country_code: str | None = None,
        custom_proxy: str | None = None,
        session_number: int | None = None,
        render_js: bool = True,
        device_type: str = "desktop",
        wait_browser: str | None = None,
        wait_for: str | None = None,
        wait_ms: int | None = None,
        block_resources: bool = True,
        block_ads: bool = False,
        forward_sdrive_headers: bool = False,
        timeout_ms: int | None = None,
        result_type: str = "html",
        screenshot: bool = False,
        screenshot_fullpage: bool = False,
        screenshot_selector: str | None = None,
        extra_params: Mapping[str, Any] | None = None,
        target_headers: Mapping[str, str] | None = None,
    ) -> ScrapeJob: ...

    async def submit_scrape(
        self,
        request: ScrapeOptions | str,
        /,
        *,
        target_headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> ScrapeJob:
        options = _apply_client_defaults(
            _coerce_options(request, kwargs),
            default_country_code=self.default_country_code,
        )
        headers = _target_headers(target_headers)
        payload = options.as_payload(
            api_key=self.api_key,
            mode="async",
            force_forward_headers=bool(headers),
        )
        response = await self._client.post(
            f"{self.api_base_url}/api/v1/scrape/async",
            json=payload,
            headers=headers,
        )
        raise_for_scrapedrive_error(response)
        return ScrapeJob.from_payload(response.json())

    async def get_job(
        self, job_id: str | None = None, *, status_url: str | None = None
    ) -> ScrapeJob:
        url = _job_url(api_base_url=self.api_base_url, job_id=job_id, status_url=status_url)
        response = await self._client.get(url)
        raise_for_scrapedrive_error(response)
        return ScrapeJob.from_payload(response.json())

    async def wait_for_job(
        self,
        job_id: str | None = None,
        *,
        status_url: str | None = None,
        poll_interval: float = 2.0,
        timeout: float | None = None,
    ) -> ScrapeJob:
        if poll_interval < 0:
            raise ValueError("poll_interval must be greater than or equal to 0")

        deadline = None if timeout is None else time.monotonic() + timeout
        job = await self.get_job(job_id, status_url=status_url)
        while job.is_pending:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for ScrapeDrive job {job.id} to finish.")
            if poll_interval:
                await asyncio.sleep(poll_interval)
            next_status_url = job.status_url or status_url
            if next_status_url:
                job = await self.get_job(status_url=next_status_url)
            else:
                job = await self.get_job(job.id)
        return job


def _coerce_options(
    request: ScrapeOptions | str, kwargs: MutableMapping[str, Any]
) -> ScrapeOptions:
    if isinstance(request, ScrapeOptions):
        if kwargs:
            raise TypeError(
                "Cannot pass keyword scrape options when request is already a "
                "ScrapeOptions instance"
            )
        return request

    extra_params = kwargs.pop("extra_params", None) or {}
    return ScrapeOptions(url=request, extra_params=extra_params, **kwargs)


def _apply_client_defaults(
    options: ScrapeOptions, *, default_country_code: str | None
) -> ScrapeOptions:
    if (
        default_country_code is not None
        and options.country_code is None
        and options.scrape_tier in {"advanced", "hyperdrive"}
    ):
        return replace(options, country_code=default_country_code)
    return options


def _normalize_country_code(country_code: str | None) -> str | None:
    if country_code is None:
        return None
    code = country_code.strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise ValueError("default_country_code must be a two-letter ISO 3166-1 alpha-2 code")
    return code


def _target_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}

    forwarded = {}
    for key, value in headers.items():
        header_name = key if key.lower().startswith("sdrive-") else f"sdrive-{key}"
        forwarded[header_name] = value
    return forwarded


def _scrape_response_from_httpx(response: httpx.Response) -> ScrapeResponse:
    data: Mapping[str, Any] | None = None
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        parsed = response.json()
        if isinstance(parsed, dict):
            data = parsed

    return ScrapeResponse(
        status_code=response.status_code,
        headers=dict(response.headers),
        text=response.text,
        data=data,
    )


def _job_url(*, api_base_url: str, job_id: str | None, status_url: str | None) -> str:
    if bool(job_id) == bool(status_url):
        raise ValueError("Pass exactly one of job_id or status_url")

    if status_url is not None:
        return status_url
    return f"{api_base_url.rstrip('/')}/api/v1/job/{job_id}"
