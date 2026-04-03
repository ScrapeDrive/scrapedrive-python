# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [0.1.1] - 2026-04-03

### Changed
- Set the PyPI homepage metadata to `https://scrapedrive.com` while keeping repository and issue links on GitHub.

## [0.1.0] - 2026-04-03

### Added
- Initial SDK release candidate.
- Typed sync and async ScrapeDrive SDK clients built on `httpx`.
- Async job polling helpers with normalized completed-job body access.
- Deterministic geo defaults for `advanced` and `hyperdrive` requests.
- `uv`-based development workflow, CI, and wheel smoke-install verification steps.
