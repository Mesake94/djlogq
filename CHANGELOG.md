# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features that have been added

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Now removed features

### Fixed
- Any bug fixes

### Security
- Vulnerability fixes

## [1.0.7] - 2025-07-17

### Added
- Added custom log handlers

### Features
- Support for adding custom log handlers

## [1.0.8] - 2025-07-18

### Fixed
- Fixed bug for custom log handlers flush method not being called


## [1.0.9] - 2025-07-19
### Added
- Automatic periodic log cleanup service (`PeriodicCleanupService`) that runs in a background thread.
- Support for multiple cleanup policies, configurable via `ASYNC_LOGGING_CONFIG['CLEANUP_POLICIES']` in Django settings.
- Each cleanup policy can specify log level, age (in days), and enabled/disabled status.
- Management command `clean_logs` for manual or programmatic log cleanup, supporting `--days`, `--level`, and `--dry-run` options.
- Singleton pattern for cleanup service with `start_cleanup_service()` and `stop_cleanup_service()` helpers.
