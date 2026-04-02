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

When the `scrapedrive` GitHub org repo is available:

1. Push the repository.
2. Tag the release version.
3. Publish the built artifacts using the target package registry workflow you choose.

Keep live API tests opt-in; they should not gate a normal release build unless dedicated release
credentials are available.
