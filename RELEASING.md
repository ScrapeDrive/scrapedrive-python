# Releasing

## Pre-release checklist

1. Update the version in `pyproject.toml`.
2. Move the relevant notes from `Unreleased` into a dated release entry in `CHANGELOG.md`.
3. Run the local verification commands:

```bash
uv sync --group dev
uv run ruff check
uv run pytest
uv build
```

4. Smoke-install the built wheel into a clean environment.

## Wheel smoke install

Windows PowerShell example:

```powershell
uv venv .wheel-smoke --python 3.13
$wheel = Get-ChildItem dist\scrapedrive-*.whl | Select-Object -First 1
uv pip install --python .wheel-smoke\Scripts\python.exe $wheel.FullName
.wheel-smoke\Scripts\python.exe -c "import importlib.metadata, scrapedrive; print(importlib.metadata.version('scrapedrive')); print(hasattr(scrapedrive, 'ScrapeDrive'))"
```

## Publish later

PyPI publishing is configured for GitHub Actions Trusted Publishing via
`.github/workflows/publish.yml`.

One-time PyPI setup:

1. Create the `scrapedrive` project on PyPI if it does not exist yet.
2. In the PyPI project settings, add a Trusted Publisher for:
   - owner: `ScrapeDrive`
   - repository: `scrapedrive-python`
   - workflow: `publish.yml`
   - environment: `pypi`

Release flow:

1. Update the version in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Commit and push.
4. Create a GitHub release or run the `Publish` workflow manually.
5. GitHub Actions will build the artifacts and run `uv publish --trusted-publishing always`.

Keep live API tests opt-in; they should not gate a normal release build unless dedicated release
credentials are available.
