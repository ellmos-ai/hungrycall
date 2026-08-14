# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-08-14

### Added
- Standard `llms.txt` context file for LLM & AI agent integration.
- Ecosystem & discoverability badges across `README.md` and `README_de.md` (`ellmos-ai`, `open-bricks`, MIT, Python 3.11+, Pytest 301 passed, llms.txt).
- Comprehensive Ruff configuration and `pytest` testpaths in `pyproject.toml`.

### Changed
- Modernized enumeration classes in `hungrycall/models.py` and `hungrycall/server_mode.py` to inherit from `enum.StrEnum` (Python 3.11+).
- Refactored type annotations to PEP 604 union syntax (`X | None`) across `translator.py`, `safety.py`, and test files.
- Optimized dictionary and collection instantiation in tests and web routes.

### Fixed
- Resolved ~400+ Ruff linting warnings (F401, UP042, UP035, SIM118, RUF013, RUF059) across all production and test modules.
- Added explicit unicode ignore overrides (`RUF001`, `RUF002`, `RUF003`) in `pyproject.toml` for intentional internationalization characters and UI symbols.

## [0.1.0] - 2026-08-05

### Added
- Multi-position order chains (`OrderChain`) with conditional fallback and item replacement rules.
- Multi-mode calling cascade (`CascadeRunner`) supporting delivery, table reservation, and pickup.
- Server deployment modes (`local`, `huckepack-gift`, `huckepack-only-host`, `pay-membership`).
- Dynamic dry-run fixture simulation and web UI with real-time SSE progress events.
- Privacy protections with E.164 phone normalization, log redaction, and strict anonymization.
