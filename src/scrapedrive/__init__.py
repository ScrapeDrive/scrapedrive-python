from importlib.metadata import PackageNotFoundError, version

from .client import AsyncScrapeDrive, ScrapeDrive
from .exceptions import (
    ApiError,
    AuthenticationError,
    MissingApiKeyError,
    PaymentRequiredError,
    RateLimitError,
    ScrapeDriveError,
    TimeoutError,
    ValidationError,
)
from .models import ScrapeJob, ScrapeOptions, ScrapeResponse

try:
    __version__ = version("scrapedrive")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "ApiError",
    "AsyncScrapeDrive",
    "AuthenticationError",
    "MissingApiKeyError",
    "PaymentRequiredError",
    "RateLimitError",
    "ScrapeDrive",
    "ScrapeDriveError",
    "ScrapeJob",
    "ScrapeOptions",
    "ScrapeResponse",
    "TimeoutError",
    "ValidationError",
    "__version__",
]
