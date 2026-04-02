from __future__ import annotations

from typing import Any

import httpx


class ScrapeDriveError(Exception):
    """Base exception for ScrapeDrive SDK failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        payload: Any = None,
        response: httpx.Response | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.payload = payload
        self.response = response


class MissingApiKeyError(ScrapeDriveError):
    """Raised when no API key is configured."""


class ApiError(ScrapeDriveError):
    """Raised for unexpected ScrapeDrive API errors."""


class AuthenticationError(ApiError):
    """Raised for authentication failures."""


class PaymentRequiredError(ApiError):
    """Raised when the account lacks credits or an active plan."""


class ValidationError(ApiError):
    """Raised when request parameters are rejected by the API."""


class RateLimitError(ApiError):
    """Raised when the API rate limits the caller."""


class TimeoutError(ApiError):
    """Raised when ScrapeDrive times out waiting for a page."""


def raise_for_scrapedrive_error(response: httpx.Response) -> None:
    """Raise a typed SDK exception for a failed ScrapeDrive response."""

    if response.is_success:
        return

    payload: Any = None
    error_code: str | None = None
    message = response.reason_phrase or (
        f"ScrapeDrive request failed with status {response.status_code}."
    )

    try:
        payload = response.json()
    except ValueError:
        payload = response.text

    if isinstance(payload, dict):
        error_value = payload.get("error")
        if isinstance(error_value, dict):
            code_value = error_value.get("code")
            message_value = error_value.get("message")
            if code_value is not None:
                error_code = str(code_value)
            if message_value:
                message = str(message_value)
        elif isinstance(error_value, str):
            message = error_value

    error_type = {
        401: AuthenticationError,
        402: PaymentRequiredError,
        422: ValidationError,
        429: RateLimitError,
        504: TimeoutError,
    }.get(response.status_code, ApiError)

    raise error_type(
        message,
        status_code=response.status_code,
        error_code=error_code,
        payload=payload,
        response=response,
    )
