from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse

ScrapeTier = Literal["standard", "advanced", "hyperdrive"]
DeviceType = Literal["desktop", "mobile"]
WaitBrowser = Literal["domcontentloaded", "load", "networkidle"]
ResultType = Literal["html", "page_text", "page_markdown"]

_KNOWN_OPTION_FIELDS = frozenset(
    {
        "url",
        "scrape_tier",
        "country_code",
        "custom_proxy",
        "session_number",
        "render_js",
        "device_type",
        "wait_browser",
        "wait_for",
        "wait_ms",
        "block_resources",
        "block_ads",
        "forward_sdrive_headers",
        "timeout_ms",
        "result_type",
        "screenshot",
        "screenshot_fullpage",
        "screenshot_selector",
        "extra_params",
    }
)

_ACTIVE_JOB_STATUSES = frozenset({"queued", "processing"})
_SCRAPE_TIERS = frozenset({"standard", "advanced", "hyperdrive"})
_DEVICE_TYPES = frozenset({"desktop", "mobile"})
_WAIT_EVENTS = frozenset({"domcontentloaded", "load", "networkidle"})
_RESULT_TYPES = frozenset({"html", "page_text", "page_markdown"})


@dataclass(frozen=True)
class ScrapeOptions:
    """Typed request options for ScrapeDrive scrape endpoints."""

    url: str
    scrape_tier: ScrapeTier = "standard"
    country_code: str | None = None
    custom_proxy: str | None = None
    session_number: int | None = None
    render_js: bool = True
    device_type: DeviceType = "desktop"
    wait_browser: WaitBrowser | None = None
    wait_for: str | None = None
    wait_ms: int | None = None
    block_resources: bool = True
    block_ads: bool = False
    forward_sdrive_headers: bool = False
    timeout_ms: int | None = None
    result_type: ResultType = "html"
    screenshot: bool = False
    screenshot_fullpage: bool = False
    screenshot_selector: str | None = None
    extra_params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")

        if self.scrape_tier not in _SCRAPE_TIERS:
            raise ValueError("scrape_tier must be one of: standard, advanced, hyperdrive")

        if self.country_code:
            if len(self.country_code) != 2 or not self.country_code.isalpha():
                raise ValueError("country_code must be a two-letter ISO 3166-1 alpha-2 code")
            if self.scrape_tier == "standard":
                raise ValueError("country_code requires scrape_tier='advanced' or 'hyperdrive'")

        if self.session_number is not None and self.session_number < 0:
            raise ValueError("session_number must be greater than or equal to 0")

        if self.device_type not in _DEVICE_TYPES:
            raise ValueError("device_type must be either 'desktop' or 'mobile'")

        if self.wait_browser is not None and self.wait_browser not in _WAIT_EVENTS:
            raise ValueError("wait_browser must be one of: domcontentloaded, load, networkidle")

        if self.wait_browser and not self.render_js:
            raise ValueError("wait_browser requires render_js=True")

        if self.wait_for and not self.render_js:
            raise ValueError("wait_for requires render_js=True")

        if self.wait_ms is not None:
            if not self.render_js:
                raise ValueError("wait_ms requires render_js=True")
            if not 0 <= self.wait_ms <= 30_000:
                raise ValueError("wait_ms must be between 0 and 30000")

        if self.result_type not in _RESULT_TYPES:
            raise ValueError("result_type must be one of: html, page_text, page_markdown")

        if self.timeout_ms is not None and self.timeout_ms < 10_000:
            raise ValueError("timeout_ms must be at least 10000")

        if self.extra_params:
            overlap = _KNOWN_OPTION_FIELDS.intersection(self.extra_params)
            if overlap:
                duplicate = ", ".join(sorted(overlap))
                raise ValueError(f"extra_params cannot redefine built-in options: {duplicate}")

    def validate_for_mode(self, mode: Literal["sync", "async"]) -> None:
        if self.timeout_ms is None:
            return

        max_timeout = 95_000 if mode == "sync" else 130_000
        if self.timeout_ms > max_timeout:
            raise ValueError(f"timeout_ms must be less than or equal to {max_timeout} for {mode}")

    @property
    def wants_screenshot(self) -> bool:
        return self.screenshot or self.screenshot_fullpage or self.screenshot_selector is not None

    def as_payload(
        self,
        *,
        api_key: str,
        mode: Literal["sync", "async"],
        force_forward_headers: bool,
    ) -> dict[str, Any]:
        self.validate_for_mode(mode)

        payload: dict[str, Any] = {
            "api_key": api_key,
            "url": self.url,
            "scrape_tier": self.scrape_tier,
            "render_js": self.render_js,
            "device_type": self.device_type,
            "block_resources": self.block_resources,
            "block_ads": self.block_ads,
            "forward_sdrive_headers": self.forward_sdrive_headers or force_forward_headers,
            "result_type": self.result_type,
            "screenshot": self.wants_screenshot,
        }

        optional_values = {
            "country_code": self.country_code.upper() if self.country_code else None,
            "custom_proxy": self.custom_proxy,
            "session_number": self.session_number,
            "wait_browser": self.wait_browser,
            "wait_for": self.wait_for,
            "wait_ms": self.wait_ms,
            "timeout_ms": self.timeout_ms,
            "screenshot_fullpage": self.screenshot_fullpage if self.screenshot_fullpage else None,
            "screenshot_selector": self.screenshot_selector,
        }

        payload.update({key: value for key, value in optional_values.items() if value is not None})
        payload.update(dict(self.extra_params))

        if mode == "sync":
            return {key: _query_value(value) for key, value in payload.items()}
        return payload


@dataclass(frozen=True)
class ScrapeResponse:
    """Normalized sync scrape response."""

    status_code: int
    headers: Mapping[str, str]
    text: str
    data: Mapping[str, Any] | None = None

    @property
    def is_json(self) -> bool:
        return self.data is not None

    @property
    def body(self) -> str | Mapping[str, Any]:
        return self.data if self.data is not None else self.text

    @property
    def screenshot_url(self) -> str | None:
        if self.data is not None:
            value = self.data.get("screenshot_url")
            if value is not None:
                return str(value)
        header_value = self.headers.get("x-sdrive-screenshot-url")
        return str(header_value) if header_value is not None else None

    def json(self) -> Mapping[str, Any]:
        if self.data is None:
            raise ValueError("Response body is not JSON")
        return self.data


@dataclass(frozen=True)
class ScrapeJob:
    """Typed async job state."""

    id: str | None
    status: str
    url: str | None = None
    status_url: str | None = None
    result: Any = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_pending(self) -> bool:
        return self.status in _ACTIVE_JOB_STATUSES

    @property
    def screenshot_url(self) -> str | None:
        response_payload = self.raw.get("response")
        if not isinstance(response_payload, Mapping):
            return None
        headers = response_payload.get("headers")
        if not isinstance(headers, Mapping):
            return None
        value = headers.get("x-sdrive-screenshot-url")
        return str(value) if value is not None else None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ScrapeJob:
        job_id = payload.get("id")
        status = payload.get("status")
        result = payload.get("result")
        response_payload = payload.get("response")
        if result is None and isinstance(response_payload, Mapping):
            if "body" in response_payload:
                result = response_payload.get("body")
            else:
                result = dict(response_payload)
        return cls(
            id=str(job_id) if job_id is not None else None,
            status=str(status) if status is not None else "unknown",
            url=_optional_string(payload.get("url")),
            status_url=_optional_string(payload.get("status_url")),
            result=result,
            raw=dict(payload),
        )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
